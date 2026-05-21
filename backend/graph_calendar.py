"""
Intégration Microsoft Graph — calendrier de l'utilisateur connecté.

Modèle d'auth : **délégué / device code flow** (client PUBLIC, AUCUN secret).
Chaque salarié se connecte avec SON compte Microsoft ; l'app ne voit que
SON agenda (permission déléguée `Calendars.Read`). Le binaire distribué ne
contient donc aucun secret extractible.

Cache de jetons : chiffré via msal-extensions (DPAPI sur Windows = lié au
compte Windows de l'utilisateur), rangé dans ~/.meeting_assistant/ — JAMAIS
sous Documents/ (pas de synchro OneDrive d'un refresh token).

Le device code flow est *bloquant* : `acquire_token_by_device_flow()` poll
Microsoft tant que l'utilisateur n'a pas validé le code (jusqu'à ~15 min).
On le déporte donc dans un thread daemon ; l'UI poll `status()`.

Toutes les fonctions sont synchrones (msal/requests sont synchrones) — les
endpoints FastAPI les appellent via `asyncio.to_thread`.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

log = logging.getLogger("backend.graph_calendar")

# ── Config (overridable par env pour un futur passage multi-tenant) ───────────
CLIENT_ID = os.environ.get(
    "GRAPH_CLIENT_ID", "12351aae-0fce-4628-8124-3f0df9e6be50"
)
TENANT_ID = os.environ.get(
    "GRAPH_TENANT_ID", "0922c70a-4c47-4b76-bc88-0a46299375d0"
)
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Calendars.Read"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
# Fuseau renvoyé par Graph pour les heures de début/fin (Paris).
OUTLOOK_TIMEZONE = "Romance Standard Time"

# Rangé hors de Documents/ (comme settings.json) → pas de synchro OneDrive.
_SETTINGS_DIR = Path.home() / ".meeting_assistant"
_CACHE_PATH = _SETTINGS_DIR / "graph_token_cache.bin"

AuthState = Literal["signed_out", "pending", "signed_in", "error"]


# ── Token cache chiffré ───────────────────────────────────────────────────────
def _build_token_cache():
    """PersistedTokenCache chiffré (DPAPI Windows). Fallback fichier brut si
    le chiffrement n'est pas disponible (ex. environnement exotique) — on
    préfère un cache non chiffré qu'une redemande de login à chaque run."""
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    from msal_extensions import PersistedTokenCache  # type: ignore

    try:
        from msal_extensions import build_encrypted_persistence  # type: ignore

        persistence = build_encrypted_persistence(str(_CACHE_PATH))
    except Exception as exc:  # pragma: no cover - dépend de l'OS
        log.warning(
            "Chiffrement du cache indisponible (%s) — fallback fichier brut", exc
        )
        from msal_extensions import FilePersistence  # type: ignore

        persistence = FilePersistence(str(_CACHE_PATH))
    return PersistedTokenCache(persistence)


# ── État du device flow (partagé entre le thread d'auth et les requêtes) ──────
_lock = threading.RLock()
_state: AuthState = "signed_out"
_pending_flow: Optional[dict] = None  # infos device code à montrer à l'user
_auth_thread: Optional[threading.Thread] = None
_last_error: Optional[str] = None
_app = None  # msal.PublicClientApplication (lazy, singleton)


def _get_app():
    """Singleton PublicClientApplication. Recréé si le cache a été purgé."""
    global _app
    if _app is None:
        import msal  # type: ignore

        _app = msal.PublicClientApplication(
            CLIENT_ID, authority=AUTHORITY, token_cache=_build_token_cache()
        )
    return _app


def _account():
    app = _get_app()
    accounts = app.get_accounts()
    return accounts[0] if accounts else None


def _acquire_silent() -> Optional[dict]:
    """Tente un jeton via le refresh token en cache (sans interaction)."""
    app = _get_app()
    acc = _account()
    if not acc:
        return None
    return app.acquire_token_silent(SCOPES, account=acc)


# ── API publique du module ────────────────────────────────────────────────────
class StatusResult(TypedDict):
    state: AuthState
    account: Optional[str]
    error: Optional[str]


def status() -> StatusResult:
    """État courant. Si un refresh token valide existe en cache, bascule en
    `signed_in` (silencieux) — l'utilisateur reste connecté entre les runs."""
    with _lock:
        if _state == "pending":
            acc = _account()
            return {
                "state": "pending",
                "account": acc["username"] if acc else None,
                "error": None,
            }
        if _state == "error":
            return {"state": "error", "account": None, "error": _last_error}

    # Hors lock : appel réseau possible (acquire_silent peut rafraîchir).
    res = _acquire_silent()
    if res and "access_token" in res:
        acc = _account()
        with _lock:
            _set_state("signed_in")
        return {
            "state": "signed_in",
            "account": acc["username"] if acc else None,
            "error": None,
        }
    return {"state": "signed_out", "account": None, "error": None}


def _set_state(new: AuthState, error: Optional[str] = None) -> None:
    global _state, _last_error
    _state = new
    _last_error = error


class LoginResult(TypedDict):
    state: AuthState
    account: Optional[str]
    userCode: Optional[str]
    verificationUri: Optional[str]
    message: Optional[str]
    expiresIn: Optional[int]


def start_login() -> LoginResult:
    """Démarre (ou reprend) le device code flow.

    - Déjà connecté → renvoie `signed_in` direct.
    - Flow déjà en cours → renvoie le code en cours (idempotent).
    - Sinon → initie un nouveau device flow et lance l'acquisition en fond.
    """
    # Court-circuit : refresh token déjà valide.
    res = _acquire_silent()
    if res and "access_token" in res:
        acc = _account()
        with _lock:
            _set_state("signed_in")
        return {
            "state": "signed_in",
            "account": acc["username"] if acc else None,
            "userCode": None,
            "verificationUri": None,
            "message": None,
            "expiresIn": None,
        }

    with _lock:
        if _state == "pending" and _pending_flow:
            f = _pending_flow
            return {
                "state": "pending",
                "account": None,
                "userCode": f.get("user_code"),
                "verificationUri": f.get("verification_uri"),
                "message": f.get("message"),
                "expiresIn": f.get("expires_in"),
            }

        app = _get_app()
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            msg = flow.get("error_description") or "Échec d'initialisation du device flow"
            _set_state("error", msg)
            return {
                "state": "error",
                "account": None,
                "userCode": None,
                "verificationUri": None,
                "message": msg,
                "expiresIn": None,
            }

        globals()["_pending_flow"] = flow
        _set_state("pending")
        t = threading.Thread(
            target=_acquire_in_background,
            args=(flow,),
            daemon=True,
            name="graph-device-flow",
        )
        globals()["_auth_thread"] = t
        t.start()

        return {
            "state": "pending",
            "account": None,
            "userCode": flow.get("user_code"),
            "verificationUri": flow.get("verification_uri"),
            "message": flow.get("message"),
            "expiresIn": flow.get("expires_in"),
        }


def _acquire_in_background(flow: dict) -> None:
    """Bloque jusqu'à login utilisateur ou expiration du code (~15 min)."""
    app = _get_app()
    try:
        result = app.acquire_token_by_device_flow(flow)  # bloquant (poll)
    except Exception as exc:  # pragma: no cover - réseau/timeout
        log.warning("Device flow a levé : %s", exc)
        with _lock:
            globals()["_pending_flow"] = None
            _set_state("error", f"Connexion échouée : {exc}")
        return

    with _lock:
        globals()["_pending_flow"] = None
        if result and "access_token" in result:
            # Le PersistedTokenCache a déjà persisté le refresh token chiffré.
            _set_state("signed_in")
            log.info("Calendrier Microsoft connecté.")
        else:
            err = (result or {}).get("error_description") or "Connexion refusée ou expirée"
            _set_state("error", err)
            log.warning("Device flow non abouti : %s", err)


def logout() -> None:
    """Déconnexion : retire les comptes du cache et purge le fichier chiffré."""
    global _app
    with _lock:
        try:
            app = _get_app()
            for acc in app.get_accounts():
                app.remove_account(acc)
        except Exception as exc:
            log.warning("remove_account a levé : %s", exc)
        # Reset dur : on jette le cache + le singleton app.
        try:
            if _CACHE_PATH.exists():
                _CACHE_PATH.unlink()
        except OSError as exc:
            log.warning("Suppression du cache impossible : %s", exc)
        _app = None
        globals()["_pending_flow"] = None
        _set_state("signed_out")


class NotAuthenticated(RuntimeError):
    """Levée par list_upcoming() si aucun jeton valide n'est disponible."""


def list_upcoming(days: int = 7) -> list[dict[str, Any]]:
    """Réunions de l'utilisateur sur la fenêtre [début d'aujourd'hui, +days jours].

    La fenêtre démarre à **minuit aujourd'hui (heure locale)** — pas à
    « maintenant » — pour que les réunions déjà terminées ce matin restent
    visibles et que l'utilisateur puisse encore y rattacher un enregistrement.

    Utilise `calendarView` (et non `/events`) pour développer les
    occurrences récurrentes dans la fenêtre demandée.
    """
    import requests  # type: ignore

    res = _acquire_silent()
    if not res or "access_token" not in res:
        raise NotAuthenticated("Calendrier non connecté")
    with _lock:
        _set_state("signed_in")

    days = max(1, min(int(days), 31))
    # Heure locale de la machine (Paris) → minuit aujourd'hui, converti en UTC
    # pour la requête Graph (timestamps suffixés 'Z').
    now_local = datetime.now().astimezone()
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = now_local + timedelta(days=days)
    start_iso = start_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    end_iso = end_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    url = f"{GRAPH_BASE}/me/calendarView"
    params = {
        "startDateTime": start_iso,
        "endDateTime": end_iso,
        "$select": "subject,start,end,organizer,location,attendees,body,bodyPreview,isOnlineMeeting,onlineMeetingProvider",
        "$orderby": "start/dateTime",
        "$top": 100,
    }
    headers = {
        "Authorization": f"Bearer {res['access_token']}",
        "Prefer": f'outlook.timezone="{OUTLOOK_TIMEZONE}"',
    }

    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 401:
        raise NotAuthenticated("Jeton expiré ou révoqué")
    if r.status_code != 200:
        raise RuntimeError(f"Graph API {r.status_code} : {r.text[:300]}")

    events = r.json().get("value", [])
    out: list[dict[str, Any]] = []
    for e in events:
        organizer = (e.get("organizer") or {}).get("emailAddress", {}) or {}
        attendees_raw = e.get("attendees") or []
        attendees = []
        for a in attendees_raw:
            # Une salle / ressource (mailbox de réunion) est un participant
            # de type "resource" → on l'exclut des participants (elle reste
            # dans "Lieu / salle" via location).
            if (a.get("type") or "").lower() == "resource":
                continue
            ea = a.get("emailAddress", {}) or {}
            name = ea.get("name") or ea.get("address")
            if name:
                attendees.append({"name": name, "address": ea.get("address")})
        out.append({
            "id": e.get("id"),
            "subject": e.get("subject") or "(sans objet)",
            "start": (e.get("start") or {}).get("dateTime"),
            "end": (e.get("end") or {}).get("dateTime"),
            "timeZone": (e.get("start") or {}).get("timeZone"),
            "organizer": {
                "name": organizer.get("name"),
                "address": organizer.get("address"),
            },
            "location": (e.get("location") or {}).get("displayName") or None,
            "attendees": attendees,
            "isOnline": bool(e.get("isOnlineMeeting")),
            "onlineProvider": e.get("onlineMeetingProvider"),
            "preview": _extract_body_text(e),
        })
    return out


def _extract_body_text(event: dict[str, Any]) -> str:
    """Récupère la description COMPLÈTE de la réunion en clair.

    Graph renvoie `body` ({contentType, content}) où `content` est l'HTML
    complet de l'invitation. `bodyPreview` (255 caractères max) est gardé en
    fallback si `body` est absent ou que le strip HTML échoue.
    """
    body = event.get("body") or {}
    raw = (body.get("content") or "").strip()
    if not raw:
        return (event.get("bodyPreview") or "").strip()
    if (body.get("contentType") or "").lower() == "html":
        import html as _html
        import re as _re
        # Style/script supprimés EN PREMIER (leur contenu ne doit pas fuiter
        # dans le texte). Puis toutes les balises, puis décodage des entités.
        cleaned = _re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", raw)
        cleaned = _re.sub(r"(?s)<[^>]+>", " ", cleaned)
        cleaned = _html.unescape(cleaned)
        # Normalisation des blancs : Outlook insère beaucoup de &nbsp; / \r\n.
        cleaned = _re.sub(r"[ \t\xa0]+", " ", cleaned)
        cleaned = _re.sub(r"\s*\n\s*", "\n", cleaned)
        cleaned = _re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
    return raw
