"""Compte rendu de réunion via l'API Mistral Large (cloud, single-shot).

Alternative à `meeting_minutes_pipeline.py` : au lieu de chunker le transcript
et d'orchestrer plusieurs appels à un llama-server local, on envoie le
transcript complet en un seul appel à `mistral-large-latest`. Rapide, simple,
pratique pour tester la qualité de Mistral Large sur les comptes rendus.

Usage :
    MISTRAL_API_KEY=sk-xxx python mistral_minutes.py \
        --transcript chemin/vers/audio.normalized.txt \
        --output chemin/vers/compte_rendu.md \
        [--participants "Alice, Bob"] [--entreprises "Yele, RTE"]

Variables d'environnement supportées (équivalentes aux flags) :
    MISTRAL_API_KEY      obligatoire
    MEETING_CONTEXT      contexte libre injecté dans le system prompt
    MEETING_PARTICIPANTS liste des participants (même format que --participants)
    MEETING_ENTREPRISES  liste des entreprises
    MISTRAL_MODEL        défaut "mistral-large-latest"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-large-latest"
REQUEST_TIMEOUT_S = 300


def _build_system_prompt(participants: str, entreprises: str, contexte: str) -> str:
    base = (
        "Tu es un assistant expert en rédaction de comptes rendus professionnels. "
        "Réponds uniquement en français.\n\n"
        "RÈGLES STRICTES DE NON-INVENTION :\n"
        "- Ne mentionne QUE ce qui est EXPLICITEMENT dit dans le texte fourni.\n"
        "- N'invente JAMAIS d'informations, de décisions, d'actions, de chiffres, de dates ou d'échéances.\n"
        "- N'invente JAMAIS le développement d'un sigle ou acronyme — laisse le sigle tel quel si tu n'es pas certain.\n"
        "- Si aucune décision n'a été prise, écris 'Aucune décision prise'.\n"
        "- Si aucune action n'a été définie, écris 'Aucune action définie'.\n"
        "- Ne reformule pas au point de changer le sens — reste fidèle au propos tenu."
    )

    if participants or entreprises:
        base += (
            "\n\n========================================\n"
            "=== ENTITÉS FIGÉES — VÉRITÉ ABSOLUE ===\n"
            "========================================\n"
            "Les listes ci-dessous sont fournies par l'utilisateur et ont PRIORITÉ ABSOLUE "
            "sur tout ce que tu lis dans le transcript. Le transcript est issu d'une ASR "
            "qui produit inévitablement des erreurs phonétiques sur les noms propres — "
            "les listes utilisateur corrigent ces erreurs.\n"
            "\nRÈGLES IMPÉRATIVES :\n"
            "1. Orthographe EXACTE : reproduire chaque nom caractère pour caractère.\n"
            "2. Corriger silencieusement toute variante phonétique vers la forme de la liste.\n"
            "3. Si un nom mentionné dans le transcript ne matche AUCUN élément de la liste,\n"
            "   ne le cite pas — c'est probablement une erreur ASR.\n"
            "4. Ne pas déduire qu'une personne appartient à une entreprise sans mention explicite.\n"
        )
        if participants:
            base += f"\nPARTICIPANTS (forme EXACTE) :\n{participants}\n"
        if entreprises:
            base += f"\nENTREPRISES (forme EXACTE) :\n{entreprises}\n"

    if contexte:
        base += (
            "\n\n=== CONTEXTE DE LA RÉUNION (fourni par l'utilisateur) ===\n"
            "À utiliser pour lever les ambiguïtés sur les sigles et acronymes. "
            "N'invente JAMAIS de contenu absent du transcript.\n"
            + contexte
        )
    return base


USER_PROMPT_TEMPLATE = """\
Voici le transcript intégral d'une réunion (une ligne par phrase, format
"Locuteur: phrase"). Rédige un compte rendu professionnel en Markdown, en
suivant EXACTEMENT la structure ci-dessous :

# Compte rendu de réunion

## 1. Résumé
Un paragraphe de 5 à 6 phrases maximum résumant l'objectif global, les grands
thèmes et la conclusion générale. Pas de liste, pas de titre imbriqué.

## 2. Sujets abordés
Identifie entre 3 et 8 sujets distincts. Pour chaque sujet :
### <Titre du sujet>
Courte mise en contexte (1-2 phrases), suivie de 2 à 6 points-clés sous forme
de puces `-`.
Puis, si applicable, une sous-section :
**Décisions :** (liste de puces) — à OMETTRE si aucune décision.
(Pas de sous-section "Actions" — les actions vont dans le Plan d'attaque global.)

## 3. Décisions
Tableau Markdown récapitulatif de TOUTES les décisions actées. Colonnes : `# | Sujet | Décision`.
Si aucune, écrire : _Aucune décision formellement prise._

## 4. Plan d'attaque
Liste unifiée combinant DEUX types d'items :
1. **Engagements explicites** tirés du transcript ("je vais faire X", "on organise Y",
   échéance mentionnée) — priorité haute. Responsable et échéance repris tels
   que mentionnés, sans invention.
2. **Recommandations consultant** (2 à 4 items) — actions de bon sens pour donner
   suite aux sujets. Pour celles-ci, mettre `—` en responsable et en échéance.

4 à 10 items au total. Tableau Markdown. Colonnes :
`# | Sujet | Action | Responsable | Échéance`.
Utiliser `—` quand l'info n'est pas explicite. Si aucun item : _Aucune action à planifier._

CONTRAINTES :
- Ne réponds RIEN d'autre que le Markdown final (pas d'introduction, pas de conclusion hors-cadre).
- Respecte strictement les règles de non-invention du system prompt.
- Utilise `\\|` pour échapper les pipes à l'intérieur des cellules de tableau.

--- TRANSCRIPT ---
{transcript}
"""


def _call_mistral(system_prompt: str, user_prompt: str, api_key: str,
                  model: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MISTRAL_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mistral API HTTP {e.code} : {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Mistral API inaccessible : {e.reason}") from e

    try:
        result = json.loads(body)
        content = result["choices"][0]["message"]["content"].strip()
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Réponse Mistral inattendue : {body[:500]}") from e
    return _strip_outer_code_fence(content)


def _strip_outer_code_fence(text: str) -> str:
    """Retire un éventuel ```markdown … ``` (ou ```…```) entourant TOUTE la
    réponse. Mistral encadre fréquemment le markdown dans un fence pour
    « l'isoler », ce qui transforme tout le compte rendu en un bloc <pre><code>
    dans l'éditeur (monospace, aucune mise en forme)."""
    s = text.strip()
    if not s.startswith("```"):
        return s
    first_nl = s.find("\n")
    if first_nl == -1:
        return s
    end = s.rstrip().rfind("```")
    # `end` doit être le fence FERMANT — pas le même que l'ouvrant.
    if end <= 0 or end == s.find("```"):
        return s
    return s[first_nl + 1 : end].strip()


def generate(transcript_path: Path, output_path: Path,
             participants: str, entreprises: str, contexte: str,
             api_key: str, model: str) -> None:
    transcript = transcript_path.read_text(encoding="utf-8").strip()
    if not transcript:
        raise ValueError(f"Transcript vide : {transcript_path}")

    system_prompt = _build_system_prompt(participants, entreprises, contexte)
    user_prompt = USER_PROMPT_TEMPLATE.format(transcript=transcript)

    print(f"[mistral-minutes] modèle={model} | transcript={len(transcript)} chars "
          f"(~{len(transcript) // 4} tokens)")
    markdown = _call_mistral(system_prompt, user_prompt, api_key, model)
    if not markdown:
        raise RuntimeError("Mistral a renvoyé une réponse vide")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"[mistral-minutes] écrit -> {output_path} ({len(markdown)} chars)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compte rendu via Mistral Large (single-shot).")
    ap.add_argument("--transcript", required=True, help="Chemin du transcript normalisé (.txt)")
    ap.add_argument("--output", required=True, help="Chemin du compte rendu .md à écrire")
    ap.add_argument("--participants", default=None)
    ap.add_argument("--entreprises", default=None)
    args = ap.parse_args()

    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        print("ERROR: MISTRAL_API_KEY manquante (variable d'environnement)", file=sys.stderr)
        sys.exit(2)

    participants = (args.participants if args.participants is not None
                    else os.environ.get("MEETING_PARTICIPANTS", "")).strip()
    entreprises = (args.entreprises if args.entreprises is not None
                   else os.environ.get("MEETING_ENTREPRISES", "")).strip()
    contexte = (os.environ.get("MEETING_CONTEXT", "") or "").strip()
    model = (os.environ.get("MISTRAL_MODEL", "") or DEFAULT_MODEL).strip()

    transcript_path = Path(args.transcript)
    output_path = Path(args.output)
    if not transcript_path.exists():
        print(f"ERROR: transcript introuvable : {transcript_path}", file=sys.stderr)
        sys.exit(1)

    try:
        generate(transcript_path, output_path, participants, entreprises,
                 contexte, api_key, model)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
