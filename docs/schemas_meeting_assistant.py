"""Definition de tous les schemas de la documentation technique Meeting Assistant.

Chaque fonction produit un PNG dans `docs/schemas/` et renvoie son chemin.
Les schemas sont numerotes dans l'ordre d'apparition du document.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Windows : stdout en cp1252 par defaut -> plante sur le moindre caractere
# non-ASCII. Meme correctif que le reste du projet.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from yele_schemas import Diagram

OUT = Path(__file__).parent / "schemas"
OUT.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 1 — Vue globale en couches
# ─────────────────────────────────────────────────────────────────────────────
def schema_1_vue_globale() -> str:
    d = Diagram(width=100, height=62)

    # Couche 1 — presentation
    d.group(2, 47, 96, 13, "Couche présentation — Electron + Next.js (export statique)", "grenat")
    d.box(6, 49.5, 20, 6.5, "Fenêtre principale", ["5 vues, état local"], "grenat")
    d.box(29, 49.5, 18, 6.5, "Popup barre tâches", ["/tray-popup"], "grenat")
    d.box(50, 49.5, 20, 6.5, "Superviseur", ["backend, MAJ, notifs"], "grenat")
    d.box(73, 49.5, 21, 6.5, "Notifications natives", ["agenda, CR prêt"], "grenat")

    d.arrow((50, 47), (50, 41.5), lw=1.2)
    d.label(51.5, 44.3, "HTTP  127.0.0.1:8000   (sondage 2–5 s)", ha="left", size=6.2)

    # Couche 2 — orchestration
    d.group(2, 27, 96, 14.5, "Couche orchestration — backend FastAPI (backend.exe)", "violet")
    d.box(6, 29.5, 19, 8.5, "API REST", ["28 endpoints", "jobs · dossiers", "calendrier"], "violet")
    d.box(28, 29.5, 19, 8.5, "État en mémoire", ["dict de Jobs", "rechargé au boot", "verrou pipeline"], "violet")
    d.box(50, 29.5, 20, 8.5, "Captation live", ["AudioRecorder", "LiveProcessor", "7 threads"], "violet")
    d.box(73, 29.5, 21, 8.5, "Lanceur", ["sous-commandes", "diar · normalize", "minutes"], "violet")

    d.arrow((80, 27), (80, 21.5), lw=1.2)
    d.label(81.5, 24.3, "sous-processus", ha="left", size=6.2)

    # Couche 3 — traitement
    d.group(2, 8, 96, 13.5, "Couche traitement — briques 1 à 3 (100 % local, CPU)", "vert")
    d.box(6, 10.5, 20, 8, "diar_pipeline", ["VAD · embeddings", "NMESC · alignement"], "vert")
    d.box(29, 10.5, 17, 8, "normalize", ["1 phrase / ligne"], "vert")
    d.box(49, 10.5, 21, 8, "meeting_minutes", ["découpage MiniLM", "extraction LLM"], "vert")
    d.box(73, 10.5, 21, 8, "llama-server", ["Ministral 3B Q4", "port 8765"], "vert_f")

    # Stockage
    d.group(2, 0.5, 96, 6, None, "gris")
    d.label(5, 3.5, "Stockage :", size=6.8, weight="bold", color="#5F5F5F", ha="left")
    d.label(17, 3.5, "Documents/Réunions/  (1 dossier par réunion — la base de données)",
            size=6.4, ha="left")
    d.label(17, 1.8, "~/.meeting_assistant/  (réglages, jetons)        userData/assets/  (modèles ~2,3 Go)",
            size=6.4, ha="left")

    return d.save(OUT / "s1_vue_globale.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 2 — Les trois chemins de traitement
# ─────────────────────────────────────────────────────────────────────────────
def schema_2_trois_chemins() -> str:
    d = Diagram(width=100, height=59)

    # (A) Upload audio
    d.group(2, 43, 96, 15, "(A)  Fichier audio uploadé", "grenat")
    d.box(5, 45, 16, 8, "Upload", ["POST /process/upload", "→ audio.<ext>"], "gris")
    d.box(25, 45, 20, 8, "BRIQUE 1 — batch", ["diarisation + ASR", "NMESC sur tout"], "grenat")
    d.box(49, 45, 15, 8, "normalize", ["1 phrase/ligne"], "vert")
    d.box(68, 45, 27, 8, "BRIQUE 3 — compte rendu", ["local (défaut) ou Mistral"], "violet")
    for x0, x1 in ((21, 25), (45, 49), (64, 68)):
        d.arrow((x0, 49), (x1, 49))

    # (B) Enregistrement
    d.group(2, 15, 96, 25, "(B)  Enregistrement dans l'application", "vert")
    d.box(5, 28.5, 16, 7.5, "Captation", ["micro + système", "ducking"], "gris")
    d.box(25, 28.5, 20, 7.5, "BRIQUE 2 — live", ["ASR + diarisation", "EN PARALLÈLE"], "vert")
    d.box(49, 28.5, 20, 7.5, "BRIQUE 3 — live", ["extraction au fil de l'eau"], "violet")
    d.box(73, 28.5, 22, 7.5, "Au clic sur Stop", ["compte_rendu.md", "déjà prêt"], "vert_f")
    for x0, x1 in ((21, 25), (45, 49), (69, 73)):
        d.arrow((x0, 32.25), (x1, 32.25))

    d.box(25, 17, 20, 7, "BRIQUE 1 — repli", ["--bootstrap-online"], "grenat")
    d.box(49, 17, 15, 7, "normalize", None, "vert")
    d.box(68, 17, 27, 7, "BRIQUE 3 — après réunion", None, "violet")
    d.arrow((35, 28.5), (35, 24.4), dashed=True)
    d.label(39, 26.4, "si le pipeline live échoue → aucun fichier écrit → repli",
            size=6.4, color="#8E403C", style="italic", ha="left")
    for x0, x1 in ((45, 49), (64, 68)):
        d.arrow((x0, 20.5), (x1, 20.5))

    # (C) Transcript
    d.group(2, 1, 96, 12, "(C)  Transcript texte importé (.txt ou .docx Teams)", "bleu")
    d.box(5, 3, 20, 6, "Import", ["transcript.raw.txt"], "gris")
    d.box(29, 3, 20, 6, "normalize", ["ni audio, ni diarisation"], "vert")
    d.box(53, 3, 27, 6, "BRIQUE 3", ["compte rendu"], "violet")
    for x0, x1 in ((25, 29), (49, 53)):
        d.arrow((x0, 6), (x1, 6))

    return d.save(OUT / "s2_trois_chemins.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 3 — Brique 1 : le pipeline de diarisation
# ─────────────────────────────────────────────────────────────────────────────
def schema_3_pipeline_diarisation() -> str:
    d = Diagram(width=100, height=60)

    d.box(30, 52, 40, 6.5, "[1]  CONVERSION AUDIO", ["ffmpeg → WAV 16 kHz mono"], "gris")

    # Branche ASR (gauche)
    d.box(4, 30, 38, 15, "[2]  TRANSCRIPTION", [
        "sherpa-onnx  ·  Zipformer FR streaming",
        "tranches de 0,5 s, contexte conservé",
        "→ mots + horodatages",
    ], "grenat")
    d.label(23, 27.5, "⚠ tourne sur l'audio ENTIER, sans découpage", size=6.2,
            color="#8E403C", style="italic")

    # Branche diarisation (droite)
    d.box(58, 43.5, 38, 6.5, "[3]  VAD  —  Silero", ["zones de parole (sans locuteur)"], "vert")
    d.box(58, 34.5, 38, 7.5, "[4]  EMBEDDINGS", ["fenêtre 1,2 s / pas 0,6 s",
                                                  "WeSpeaker ResNet34 → (N, 256)"], "vert")
    d.box(58, 25.5, 38, 7.5, "[5]  CLUSTERING", ["NMESC estime k",
                                                  "Spectral Clustering assigne"], "vert")
    d.box(58, 17.5, 38, 6.5, "[6]  SEGMENTS", ["fusion des voisins < 0,7 s"], "vert")

    # Distribution depuis [1] vers les deux branches
    d.path([(50, 52), (23, 52), (23, 45.4)], lw=1.2)
    d.path([(50, 52), (77, 52), (77, 50.4)], lw=1.2)
    # Chaine de la branche diarisation
    for y0, y1 in ((43.5, 42.4), (34.5, 33.4), (25.5, 24.4)):
        d.path([(77, y0), (77, y1)], lw=1.2)

    # Convergence des deux branches vers l'alignement
    d.box(20, 6, 60, 8, "[7]  ALIGNEMENT  MOTS ↔ LOCUTEURS", [
        "instant médian de chaque mot → segment qui le contient",
        "puis regroupement en tours de parole",
    ], "violet")
    d.path([(23, 30), (23, 18), (50, 18), (50, 14.4)], lw=1.2)
    d.path([(77, 17.5), (77, 18), (50, 18)], lw=1.2, arrow=False)

    d.arrow((50, 6), (50, 3.9), lw=1.2)
    d.label(50, 2.2, "transcript.txt   +   turns.json", size=7.6, weight="bold",
            color="#8E403C")

    return d.save(OUT / "s3_pipeline_diarisation.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 4 — Brique 1 : les deux modes de clustering
# ─────────────────────────────────────────────────────────────────────────────
def schema_4_modes_clustering() -> str:
    d = Diagram(width=100, height=40)

    d.group(2, 21, 96, 17, "Mode BATCH — fichier audio uploadé", "grenat")
    d.box(5, 23.5, 21, 10, "Tous les embeddings", ["N ≈ 4 800 pour 1 h"], "gris")
    d.box(30, 23.5, 30, 10, "NMESC sur la totalité", [
        "balayage de 30 valeurs de p",
        "décomposition dense N × N",
        "coût en O(N³)"], "grenat")
    d.box(64, 23.5, 31, 10, "Spectral Clustering", ["k locuteurs assignés"], "grenat")
    d.arrow((26, 28.5), (30, 28.5))
    d.arrow((60, 28.5), (64, 28.5))

    d.group(2, 1.5, 96, 17, "Mode BOOTSTRAP + ONLINE — enregistrement (--bootstrap-online)", "vert")
    d.box(5, 4, 21, 10, "1 000 premiers", ["≈ 10 min de parole"], "gris")
    d.box(30, 4, 30, 10, "NMESC sur ce lot seul", [
        "centroïdes + seuil auto",
        "borné à [0,3 ; 0,85]"], "vert")
    d.box(64, 4, 31, 10, "Assignation séquentielle", [
        "centroïde le plus proche",
        "AUCUN nouveau locuteur"], "vert_f")
    d.arrow((26, 9), (30, 9))
    d.arrow((60, 9), (64, 9))

    return d.save(OUT / "s4_modes_clustering.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 5 — Brique 2 : les threads de la captation
# ─────────────────────────────────────────────────────────────────────────────
def schema_5_threads_captation() -> str:
    d = Diagram(width=100, height=68)

    d.label(50, 66, "POST  /api/record/start", size=7.6, weight="bold", color="#8E403C")

    d.group(2, 42, 46, 21, "AudioRecorder", "grenat")
    d.box(5, 53.5, 40, 5.5, "[T1]  flux micro",
          ["WASAPI shared — coexiste avec Teams"], "grenat")
    d.box(5, 47.5, 40, 5.5, "[T2]  worker loopback",
          ["son système, 3 niveaux de repli"], "grenat")
    d.box(5, 43, 40, 4, "[T3]  mixage live  +  ducking", None, "grenat_f")
    d.arrow((25, 53.5), (25, 53.2), lw=1.0)
    d.arrow((25, 47.5), (25, 47.2), lw=1.0)

    d.group(52, 42, 46, 21, "LiveProcessor", "violet")
    d.box(55, 52.5, 40, 6.5, "start()  —  thread de fond",
          ["chargement + warmup des modèles (15–20 s)",
           "les chunks s'empilent pendant ce temps"], "violet")
    d.box(55, 44.5, 40, 6, "push(chunk)",
          ["non bloquant, appelé par [T3]"], "violet")
    d.arrow((48, 45), (55, 47.2), lw=1.1)

    d.box(20, 34, 26, 5, "_asr_q", ["file bornée à 15 000"], "gris")
    d.box(54, 34, 26, 5, "_embed_q", ["file bornée à 15 000"], "gris")
    d.path([(75, 44.5), (75, 41.5), (33, 41.5), (33, 39.3)], lw=1.1)
    d.path([(75, 44.5), (75, 41.5), (67, 41.5), (67, 39.3)], lw=1.1)

    d.box(4, 20, 42, 11, "[T4]  worker ASR",
          ["sherpa-onnx, num_threads = 2",
           "interroge le décodeur toutes les 2 s",
           "→ mots au fil de l'eau"], "vert")
    d.box(54, 20, 42, 11, "[T5]  worker empreintes",
          ["grille fixe 1,2 s / 0,6 s",
           "VAD par blocs de 512 → resnet34",
           "→ BootstrapOnlineClusterer.add()"], "vert")
    d.arrow((33, 34), (25, 31.3), lw=1.1)
    d.arrow((67, 34), (75, 31.3), lw=1.1)

    d.box(20, 12.5, 60, 5.5, "[T6]  dispatch des tours de parole",
          ["TurnBuilder → chunker sémantique → LLM  (brique 3)"], "violet")
    d.arrow((25, 20), (35, 18.3), lw=1.1)
    d.arrow((75, 20), (65, 18.3), lw=1.1)

    d.box(12, 1.5, 76, 6,
          "join des workers  ·  clustering final  ·  alignement mots ↔ locuteurs",
          ["écrit transcript.txt  —  ou N'ÉCRIT RIEN, et le repli batch prend la main"],
          "gris")
    d.arrow((30, 12.5), (30, 7.8), lw=1.1)
    d.label(36, 10.0, "POST  /api/record/stop   →   finalize()", size=7.2,
            weight="bold", color="#8E403C", ha="left")

    return d.save(OUT / "s5_threads_captation.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 6 — Brique 2 : le ducking
# ─────────────────────────────────────────────────────────────────────────────
def schema_6_ducking() -> str:
    d = Diagram(width=100, height=46)

    d.box(3, 34, 27, 9, "Micro",
          ["voix présentes dans la pièce",
           "+ FUITE acoustique du distant"], "grenat")
    d.box(3, 21, 27, 9, "Son système (loopback)",
          ["voix des participants distants",
           "propre, numérique"], "vert")

    d.label(37, 42.5, "sans traitement, la voix du distant arrive DEUX fois :",
            size=6.6, weight="bold", color="#8E403C", ha="left")
    d.label(37, 40.2, "voix dédoublée, effet d'écho, et la diarisation invente un locuteur",
            size=6.4, color="#8E403C", style="italic", ha="left")

    d.box(37, 22, 28, 12, "DUCKING",
          ["décision par fenêtre",
           "120 ms hors ligne",
           "≈ 50 ms en direct"], "violet")
    d.arrow((30, 38), (37, 31), lw=1.1)
    d.arrow((30, 25), (37, 26.5), lw=1.1)

    d.box(70, 22, 27, 12, "Mixage",
          ["micro × gain variable", "+ système × 0,9", "clipping [-1, 1]"], "gris")
    d.arrow((65, 28), (70, 28), lw=1.1)

    d.group(2, 1.5, 96, 17, "Règle de décision, appliquée fenêtre par fenêtre", "gris")
    d.box(5, 9, 29, 5, "Système silencieux", ["gain micro 0,8"], "vert")
    d.label(19.5, 6.9, "l'utilisateur parle", size=6.2, style="italic")
    d.box(36, 9, 29, 5, "Système actif, micro plus faible", ["gain micro 0,08"], "grenat")
    d.label(50.5, 6.9, "le micro ne capte que la fuite", size=6.2, style="italic")
    d.box(67, 9, 29, 5, "Système actif, micro plus fort", ["gain micro 0,8"], "vert")
    d.label(81.5, 6.9, "l'utilisateur parle par-dessus", size=6.2, style="italic")
    d.label(50, 3.6, "seuil de bascule : micro < 1,6 × système        lissage 0,25 par "
                     "fenêtre — environ 12 fenêtres pour converger",
            size=6.4, color="#8E403C")

    return d.save(OUT / "s6_ducking.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 7 — Brique 2 : fenetrage batch contre fenetrage live
# ─────────────────────────────────────────────────────────────────────────────
def schema_7_fenetrage() -> str:
    import matplotlib.pyplot as plt

    d = Diagram(width=100, height=42)
    X0 = 15                                              # marge pour les libelles
    speech = [(18, 18), (39, 10), (55, 22), (82, 13)]    # (debut, duree)

    def piste(y):
        d.ax.add_patch(plt.Rectangle((X0, y), 96 - X0, 3.2, facecolor="#EFEFEF",
                                     edgecolor="#CFCFCF", lw=0.6, zorder=1))
        for x, w in speech:
            d.ax.add_patch(plt.Rectangle((x, y), w, 3.2, facecolor="#C7C7C7",
                                         edgecolor="none", zorder=2))

    # ── Mode batch
    d.label(2, 38.4, "MODE BATCH  —  le VAD segmente d'abord ; les fenêtres sont posées "
                     "À L'INTÉRIEUR des zones de parole",
            size=7.0, weight="bold", color="#333333", ha="left")
    piste(33.5)
    for x, w in speech:
        d.ax.add_patch(plt.Rectangle((x, 30.0), w, 2.2, facecolor="#1F6F5C",
                                     edgecolor="none", zorder=3))
        xi = x
        while xi + 2.2 <= x + w:
            d.ax.add_patch(plt.Rectangle((xi + 0.15, 26.8), 1.9, 2.0,
                                         facecolor="#B2544F", edgecolor="none", zorder=3))
            xi += 2.4
    d.label(13, 35.1, "signal", size=6.0, color="#777777", ha="right")
    d.label(13, 31.1, "zones VAD", size=6.0, color="#1F6F5C", ha="right", weight="bold")
    d.label(13, 27.8, "fenêtres", size=6.0, color="#B2544F", ha="right", weight="bold")
    d.label(52, 24.2, "toute fenêtre tient entièrement dans une zone de parole  →  "
                      "empreintes propres",
            size=6.4, color="#1F6F5C", style="italic")

    # ── Mode live
    d.label(2, 19.4, "MODE LIVE  —  grille fixe 1,2 s / 0,6 s, conservée dès qu'UN bloc "
                     "de 512 échantillons dépasse le seuil VAD",
            size=7.0, weight="bold", color="#333333", ha="left")
    piste(14.5)
    xi = X0
    while xi + 2.2 <= 96:
        mid = xi + 1.1
        inside = any(x + 1.2 <= mid <= x + w - 1.2 for x, w in speech)
        touch = any(x - 1.2 <= mid <= x + w + 1.2 for x, w in speech)
        col = "#B2544F" if inside else ("#DBA5A2" if touch else "#E9E9E9")
        d.ax.add_patch(plt.Rectangle((xi + 0.15, 11.3), 1.9, 2.0, facecolor=col,
                                     edgecolor="none", zorder=3))
        xi += 2.4
    d.label(13, 16.1, "signal", size=6.0, color="#777777", ha="right")
    d.label(13, 12.3, "grille", size=6.0, color="#B2544F", ha="right", weight="bold")

    d.ax.add_patch(plt.Rectangle((26, 7.4), 1.9, 1.8, facecolor="#B2544F", zorder=3))
    d.label(29, 8.3, "conservée — parole pleine", size=6.2, ha="left")
    d.ax.add_patch(plt.Rectangle((58, 7.4), 1.9, 1.8, facecolor="#DBA5A2", zorder=3))
    d.label(61, 8.3, "conservée mais BRUITÉE — bord de zone", size=6.2,
            color="#8E403C", ha="left")

    d.label(50, 3.4, "C'est la source des empreintes bruitées qui a rendu nécessaire "
                     "le gel du clusterer après amorçage",
            size=6.8, color="#8E403C", style="italic", weight="bold")

    return d.save(OUT / "s7_fenetrage.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 8 — Brique 3 : les trois moteurs de compte rendu
# ─────────────────────────────────────────────────────────────────────────────
def schema_8_trois_moteurs() -> str:
    d = Diagram(width=100, height=62)

    d.box(30, 55.5, 40, 5, "transcript.txt", ["produit par la brique 1 ou 2"], "gris")
    d.box(30, 48, 40, 5.5, "normalize", ["1 phrase par ligne — horodatages RETIRÉS"], "vert")
    d.arrow((50, 55.5), (50, 53.8), lw=1.2)

    # Colonne 1 — live local
    d.group(1, 8, 31, 35, "LIVE LOCAL", "vert")
    d.label(16.5, 37.6, "pendant la réunion", size=6.2, style="italic", color="#1F6F5C")
    d.box(3, 32, 27, 5, "TurnBuilder", None, "vert")
    d.box(3, 25, 27, 5.5, "StreamingTopicChunker", ["seuil GLISSANT + confirmation"], "vert")
    d.box(3, 18, 27, 5.5, "LiveLLMWorker", ["Ministral 3B local"], "vert")
    d.box(3, 10.5, 27, 6, "finalize()", ["résumé + plan + assemblage"], "vert_f")
    for y0, y1 in ((32, 31.3), (25, 24.3), (18, 17.3)):
        d.path([(16.5, y0), (16.5, y1)], lw=1.0)

    # Colonne 2 — batch local
    d.group(34.5, 8, 31, 35, "BATCH LOCAL", "grenat")
    d.label(50, 37.6, "après la réunion — moteur par défaut", size=6.2,
            style="italic", color="#B2544F")
    d.box(36.5, 32, 27, 5, "découpage sémantique", None, "grenat")
    d.box(36.5, 25, 27, 5.5, "generate_section_json", ["3 appels LLM par chunk"], "grenat")
    d.box(36.5, 18, 27, 5.5, "résumé + plan d'attaque", ["1 appel LLM"], "grenat")
    d.box(36.5, 10.5, 27, 6, "assemble_report()", ["100 % déterministe"], "grenat_f")
    for y0, y1 in ((32, 31.3), (25, 24.3), (18, 17.3)):
        d.path([(50, y0), (50, y1)], lw=1.0)

    # Colonne 3 — mistral
    d.group(68, 8, 31, 35, "BATCH MISTRAL", "violet")
    d.label(83.5, 37.6, "sur demande — clé API requise", size=6.2,
            style="italic", color="#6B4E9B")
    d.box(70, 25, 27, 12, "UN SEUL appel API", [
        "transcript INTÉGRAL",
        "mistral-large-latest",
        "temporisation 300 s"], "violet")
    d.box(70, 10.5, 27, 11, "markdown renvoyé tel quel", [
        "le plan du document est",
        "DICTÉ dans le prompt",
        "aucun garde-fou de code"], "violet")
    d.path([(83.5, 25), (83.5, 21.8)], lw=1.0)

    d.path([(50, 48), (50, 45), (16.5, 45), (16.5, 43.3)], lw=1.1)
    d.path([(50, 48), (50, 45), (50, 43.3)], lw=1.1)
    d.path([(50, 48), (50, 45), (83.5, 45), (83.5, 43.3)], lw=1.1)

    d.box(30, 1.5, 40, 5, "compte_rendu.md", None, "gris")
    d.path([(16.5, 10.5), (16.5, 7), (47.5, 7)], lw=1.1)
    d.path([(83.5, 10.5), (83.5, 7), (52.5, 7)], lw=1.1)
    d.arrow((50, 10.5), (50, 6.7), lw=1.1)

    return d.save(OUT / "s8_trois_moteurs.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 9 — Brique 3 : le decoupage semantique
# ─────────────────────────────────────────────────────────────────────────────
def schema_9_decoupage_semantique() -> str:
    import numpy as np
    import matplotlib.pyplot as plt

    d = Diagram(width=100, height=50)

    d.box(4, 43.5, 21, 5.5, "1 phrase / ligne", ["transcript normalisé"], "gris")
    d.box(28, 43.5, 21, 5.5, "fenêtres de 3", ["glissantes, pas de 1"], "gris")
    d.box(52, 43.5, 21, 5.5, "embeddings MiniLM", ["vecteurs normalisés"], "vert")
    d.box(76, 43.5, 21, 5.5, "similarité cosinus", ["entre fenêtres voisines"], "vert")
    for x0, x1 in ((25, 28), (49, 52), (73, 76)):
        d.arrow((x0, 46.25), (x1, 46.25))

    # Courbe de similarite
    rng = np.random.default_rng(3)
    n = 120
    base = 0.86 + 0.05 * np.sin(np.linspace(0, 7, n))
    for c, w, dep in ((22, 5, 0.30), (52, 5, 0.26), (86, 4, 0.24)):
        base -= dep * np.exp(-0.5 * ((np.arange(n) - c) / w) ** 2)
    raw = base + rng.normal(0, 0.022, n)
    sm = np.convolve(raw, np.ones(7) / 7, mode="same")
    sm[:3], sm[-3:] = raw[:3], raw[-3:]

    X0, X1, Y0, YH = 10.0, 96.0, 17.0, 18.0
    xs = X0 + (X1 - X0) * np.arange(n) / (n - 1)

    def ry(v):
        return Y0 + (v - 0.50) / 0.45 * YH

    d.ax.add_patch(plt.Rectangle((X0, Y0), X1 - X0, YH, facecolor="#FAFAFA",
                                 edgecolor="#DDDDDD", lw=0.6, zorder=1))
    d.ax.plot(xs, [ry(v) for v in raw], color="#C9C9C9", lw=0.7, zorder=2)
    d.ax.plot(xs, [ry(v) for v in sm], color="#1F6F5C", lw=1.5, zorder=3)

    seuil = float(np.percentile(sm, 5))
    d.ax.plot([X0, X1], [ry(seuil)] * 2, color="#B2544F", lw=1.0,
              linestyle=(0, (4, 2)), zorder=4)
    d.label(X0 + 1.0, ry(seuil) - 1.6, "seuil = 5ᵉ percentile des similarités lissées",
            size=6.2, color="#B2544F", ha="left")

    for c in (22, 52, 86):
        x = X0 + (X1 - X0) * c / (n - 1)
        d.ax.plot([x, x], [Y0, Y0 + YH], color="#B2544F", lw=1.0, zorder=5)
        d.ax.add_patch(plt.Circle((x, ry(sm[c])), 0.7, facecolor="#B2544F", zorder=6))

    d.label(X0 - 0.8, Y0 + YH - 1.2, "similarité", size=6.2, ha="right", color="#1F6F5C",
            weight="bold")
    d.label(X0 - 0.8, Y0 + 1.2, "brute / lissée", size=6.0, ha="right", color="#999999")
    d.label(50, Y0 + YH + 2.4, "Une CHUTE de similarité signale un changement de sujet",
            size=7.0, weight="bold", color="#333333")

    # Chunks
    bnds = [0, 22, 52, 86, n - 1]
    cols = ["grenat", "violet", "vert", "grenat_f"]
    for i in range(4):
        xa = X0 + (X1 - X0) * bnds[i] / (n - 1)
        xb = X0 + (X1 - X0) * bnds[i + 1] / (n - 1)
        d.box(xa + 0.4, 8.5, xb - xa - 0.8, 5.5, f"Chunk {i + 1}",
              ["→ 1 sujet du CR"], cols[i], title_size=7.0, line_size=6.0)
        d.path([((xa + xb) / 2, Y0), ((xa + xb) / 2, 14.3)], lw=1.0, arrow=True)

    d.label(50, 5.0, "garde-fou : un chunk de plus de 15 000 caractères est re-coupé "
                     "récursivement à sa vallée la plus profonde",
            size=6.4, color="#8E403C", style="italic")
    d.label(50, 2.0, "distance minimale de 10 fenêtres entre deux frontières — "
                     "empêche de hacher la réunion en micro-sections",
            size=6.4, color="#5A5A5A", style="italic")

    return d.save(OUT / "s9_decoupage_semantique.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 10 — Brique 3 : du chunk au compte rendu
# ─────────────────────────────────────────────────────────────────────────────
def schema_10_chunk_vers_cr() -> str:
    d = Diagram(width=100, height=54)

    d.box(3, 44, 24, 7, "Chunk thématique", ["texte brut du passage"], "gris")

    d.group(31, 40.5, 67, 12.5, "generate_section_json  —  3 appels LLM par chunk", "grenat")
    d.box(33, 42.5, 20, 6.5, "1 · RÉSUMÉ", ["titre, contexte", "points-clés"], "grenat")
    d.box(55, 42.5, 20, 6.5, "2 · EXTRACTION", ["décisions actées"], "grenat")
    d.box(77, 42.5, 19, 6.5, "3 · PLAN", ["0 à 2 items"], "grenat")
    d.arrow((27, 47.5), (33, 45.7), lw=1.1)
    d.label(64.5, 36.8, "les trois partagent le préfixe [system][chunk] → le cache "
                        "de préfixe du serveur évite de le recalculer",
            size=6.2, style="italic", color="#8E403C")

    d.box(20, 29, 60, 6, "Sortie JSON CONTRAINTE au niveau des tokens", [
        "schéma strict — le modèle ne PEUT PAS produire du JSON invalide"], "violet")
    for x in (43, 65, 86):
        d.path([(x, 42.5), (x, 39.3), (50, 39.3), (50, 35.3)], lw=1.0)

    d.box(6, 19, 40, 6.5, "build_exec_summary", ["1 appel LLM sur les titres et résumés"], "grenat")
    d.box(54, 19, 40, 6.5, "build_plan_attack", ["assemblage DÉTERMINISTE", "aucun appel LLM"], "vert")
    d.path([(50, 29), (50, 27), (26, 27), (26, 25.8)], lw=1.0)
    d.path([(50, 29), (50, 27), (74, 27), (74, 25.8)], lw=1.0)

    d.box(12, 8, 76, 8.5, "assemble_report()  —  100 % déterministe, aucun appel LLM", [
        "Participants · Résumé · Sujets abordés · Décisions · Plan d'attaque",
        "titres, tableaux, numérotation et échappement produits par du CODE"], "vert_f")
    d.arrow((26, 19), (35, 16.8), lw=1.1)
    d.arrow((74, 19), (65, 16.8), lw=1.1)

    d.label(50, 4.6, "La structure du document ne dépend JAMAIS du LLM.", size=7.6,
            weight="bold", color="#8E403C")
    d.label(50, 1.8, "Le modèle remplit des cases ; le squelette est du code. "
                     "C'est ce qui rend un modèle de 3 milliards de paramètres utilisable.",
            size=6.6, style="italic", color="#5A5A5A")

    return d.save(OUT / "s10_chunk_vers_cr.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 11 — Brique 4 : le systeme de fichiers comme base de donnees
# ─────────────────────────────────────────────────────────────────────────────
def schema_11_stockage() -> str:
    d = Diagram(width=100, height=52)

    # Colonne gauche — Documents/Reunions
    d.group(1, 12, 61, 38, "Documents / Réunions /", "grenat")
    d.label(4, 46.4, "résolu par l'API Windows — suit OneDrive si actif", size=6.2,
            style="italic", color="#8E403C", ha="left")

    d.box(4, 27.5, 55, 16, "", None, "grenat")
    d.label(31.5, 42.2, "2026-05-19_14h00m00s_Revue produit", size=7.4,
            weight="bold", color="#FFFFFF")
    inner = [
        ("audio.wav", "l'enregistrement ou le fichier importé"),
        ("compte_rendu.md  /  .docx", "le livrable"),
        ("transcript.txt  ·  turns.json", "transcript + tours de parole"),
        ("speakers.json", "renommage des locuteurs"),
        (".origin.recording", "marqueur : vient d'un enregistrement"),
        (".calendar_event.json", "marqueur : réunion d'agenda liée"),
    ]
    y = 39.4
    for nom, desc in inner:
        d.label(7, y, nom, size=6.1, color="#FFFFFF", ha="left", weight="bold")
        d.label(33, y, desc, size=5.8, color="#F2DEDD", ha="left", style="italic")
        y -= 2.2

    d.box(4, 21.5, 55, 4.5, "2026-05-20_09h30m00s", ["une autre réunion, hors agenda"],
          "grenat", title_size=7.0, line_size=6.0)

    d.box(4, 13.5, 55, 6.5, "", None, "gris")
    d.label(31.5, 18.4, "Clients /", size=7.2, weight="bold", color="#FFFFFF")
    d.label(31.5, 16.4, "un dossier-CATÉGORIE — sous-dossier réel", size=6.0,
            color="#DDDDDD")
    d.label(31.5, 14.6, "└─  2026-05-21_10h00m00s_Comité AO /", size=6.0,
            color="#DDDDDD")

    # Colonne droite — reglages
    d.group(64, 24, 35, 26, "~ / .meeting_assistant /", "violet")
    d.label(66.5, 46.4, "hors de Documents — pas de synchro", size=6.2,
            style="italic", color="#6B4E9B", ha="left")
    d.box(66, 38, 31, 5.5, "settings.json", ["clé API Mistral — EN CLAIR"], "violet")
    d.box(66, 31.5, 31, 5.5, "graph_token_cache.bin", ["jetons Microsoft — CHIFFRÉS"], "violet")
    d.box(66, 25.5, 31, 5, "logs /", ["désactivés dans le build livré"], "gris")

    # Regle
    d.group(64, 12, 35, 10, "Réunion ou catégorie ?", "vert")
    d.label(81.5, 17.4, "un dossier contenant un fichier audio.*", size=6.3)
    d.label(81.5, 15.3, "ou transcript.raw.txt est une RÉUNION.", size=6.3)
    d.label(81.5, 13.3, "sinon, c'est une CATÉGORIE.", size=6.3, weight="bold",
            color="#1F6F5C")

    d.label(50, 8.4, "Il n'y a AUCUNE base de données.", size=8.4, weight="bold",
            color="#8E403C")
    d.label(50, 5.4, "L'état en mémoire est intégralement reconstruit au démarrage "
                     "par un balayage de l'arborescence.", size=6.8, color="#5A5A5A")
    d.label(50, 2.6, "Corollaire : les identifiants de traitement sont régénérés à "
                     "chaque lancement — ils ne survivent pas à un redémarrage.",
            size=6.6, style="italic", color="#8E403C")

    return d.save(OUT / "s11_stockage.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 12 — Brique 4 : cycle de vie d'un traitement
# ─────────────────────────────────────────────────────────────────────────────
def schema_12_cycle_job() -> str:
    d = Diagram(width=100, height=46)

    d.label(50, 44, "Cycle de vie d'un traitement", size=8.0, weight="bold",
            color="#333333")

    etats = [("draft", "gris"), ("pending", "gris"), ("queued", "violet"),
             ("running", "violet"), ("done", "vert")]
    x = 3
    for i, (nom, col) in enumerate(etats):
        d.box(x, 33.5, 15.5, 6, nom, None, col, title_size=7.6)
        if i:
            d.arrow((x - 2.6, 36.5), (x - 0.3, 36.5))
        x += 18.1
    d.box(84, 24, 13, 6, "error", None, "grenat", title_size=7.6)
    d.path([(76.5, 33.5), (76.5, 27), (83.7, 27)], lw=1.0)

    d.label(11, 31.4, "créé au boot\nou à l'import", size=6.0, color="#5A5A5A")
    d.label(47, 31.4, "verrou global —\nun seul à la fois", size=6.0, color="#6B4E9B")
    d.label(65, 31.4, "veille bloquée\npendant le calcul", size=6.0, color="#6B4E9B")

    # Rechargement au demarrage
    d.group(1, 2, 60, 25, "Au démarrage du backend", "grenat")
    d.box(3, 18, 56, 5, "thread daemon — ne bloque PAS l'ouverture de l'application",
          None, "grenat_f", title_size=7.0)
    d.box(3, 12, 56, 5, "balayage de Documents/Réunions/  (un seul niveau)", None, "grenat")
    d.box(3, 6, 56, 5, "reconstruction d'un Job par dossier de réunion", None, "grenat")
    d.arrow((31, 18), (31, 17.3), lw=1.0)
    d.arrow((31, 12), (31, 11.3), lw=1.0)
    d.label(31, 3.6, "lecture INTÉGRALE de chaque compte rendu et transcript",
            size=6.2, style="italic", color="#8E403C")

    # Idempotence
    d.group(64, 2, 35, 25, "Idempotence du lancement", "vert")
    d.box(66, 15, 31, 7, "compte rendu déjà présent ?",
          ["écrit par le LLM temps réel"], "vert")
    d.box(66, 7.5, 31, 5.5, "réponse « déjà terminé »",
          ["aucun retraitement"], "vert_f")
    d.arrow((81.5, 15), (81.5, 13.3), lw=1.0)
    d.label(81.5, 4.6, "c'est ce qui rend le compte rendu\ntemps réel simplement constaté",
            size=6.2, style="italic", color="#1F6F5C")

    return d.save(OUT / "s12_cycle_job.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 13 — Brique 4 : orchestration du pipeline
# ─────────────────────────────────────────────────────────────────────────────
def schema_13_orchestration() -> str:
    d = Diagram(width=100, height=50)

    d.box(28, 43, 44, 5.5, "POST /api/jobs/{id}/process", ["tâche de fond"], "violet")

    d.box(20, 34.5, 60, 6, "verrou global  —  un seul traitement à la fois", [
        "la mise en veille est bloquée pendant toute la durée"], "grenat_f")
    d.arrow((50, 43), (50, 40.7), lw=1.2)

    d.label(50, 32.4, "source = audio  et  pas de transcript temps réel ?", size=6.6,
            style="italic", color="#5A5A5A")

    d.box(4, 24, 44, 6.5, "backend.exe  diar", [
        "[--bootstrap-online si enregistrement]"], "grenat")
    d.box(52, 24, 44, 6.5, "sinon : on part du transcript existant", None, "gris")
    d.path([(50, 34.5), (50, 31.5), (26, 31.5), (26, 30.8)], lw=1.0)
    d.path([(50, 34.5), (50, 31.5), (74, 31.5), (74, 30.8)], lw=1.0)

    d.box(20, 16, 60, 5.5, "backend.exe  normalize", None, "vert")
    d.path([(26, 24), (26, 22.5), (50, 22.5), (50, 21.8)], lw=1.0)
    d.path([(74, 24), (74, 22.5), (50, 22.5)], lw=1.0, arrow=False)

    d.box(20, 8, 60, 5.5, "backend.exe  minutes  |  mistral-minutes", None, "violet")
    d.arrow((50, 16), (50, 13.8), lw=1.1)

    d.box(4, 1, 44, 5, "conversion en .docx", None, "gris")
    d.box(52, 1, 44, 5, "purge des fichiers intermédiaires", None, "gris")
    d.path([(50, 8), (50, 6.8), (26, 6.8), (26, 6.3)], lw=1.0)
    d.path([(50, 8), (50, 6.8), (74, 6.8), (74, 6.3)], lw=1.0)

    d.label(97, 40, "Chaque étape est un SOUS-PROCESSUS :", size=6.4, ha="right",
            weight="bold", color="#8E403C")
    d.label(97, 38, "le même exécutable se rappelle lui-même", size=6.2, ha="right",
            style="italic", color="#8E403C")

    return d.save(OUT / "s13_orchestration.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 14 — Brique 5 : sequence de demarrage et cycle du backend
# ─────────────────────────────────────────────────────────────────────────────
def schema_14_demarrage() -> str:
    d = Diagram(width=100, height=66)

    d.box(20, 60, 60, 4.5, "verrou d'instance unique  —  la 2ᵉ réveille la 1ʳᵉ",
          None, "gris", title_size=7.2)

    etapes = [
        ("1", "vérifier / télécharger les modèles", "bloquant — fenêtre de progression", "grenat"),
        ("2", "afficher le splash", "visible en moins d'une seconde", "grenat"),
        ("3", "démarrer le backend Python", "environnement injecté : chemins des modèles", "violet"),
        ("4", "attendre la sonde de santé", "90 s maximum", "violet"),
        ("5", "créer la fenêtre principale", "remplace le splash quand elle est prête", "vert"),
        ("6", "vérifier les mises à jour", "production uniquement, en fond", "gris"),
        ("7-10", "préférences · barre des tâches · notifications", "", "gris"),
    ]
    y = 53.5
    for num, titre, sub, col in etapes:
        d.box(10, y, 80, 5, f"{num}.   {titre}", [sub] if sub else None, col,
              title_size=7.2, line_size=6.0)
        if y > 17:
            d.arrow((50, y), (50, y - 1.3), lw=1.0)
        y -= 6.3

    d.label(50, 13.0, "toute exception dans cette chaîne ferme le splash, "
                      "affiche une boîte d'erreur et quitte",
            size=6.4, color="#8E403C", style="italic")

    # Cycle du backend
    d.group(1, 1, 47, 10, "Arrêt du backend", "grenat")
    d.label(24.5, 6.4, "tuer l'ARBRE de processus, pas la racine seule :", size=6.3)
    d.label(24.5, 4.2, "le serveur et le modèle de langue engendrent des fils,",
            size=6.2, color="#8E403C", style="italic")
    d.label(24.5, 2.4, "un signal sur la racine laisse des orphelins.", size=6.2,
            color="#8E403C", style="italic")

    d.group(52, 1, 47, 10, "Avant une mise à jour", "violet")
    d.label(75.5, 6.4, "ATTENDRE la mort effective des processus", size=6.3,
            weight="bold")
    d.label(75.5, 4.2, "tant qu'ils tiennent les fichiers, l'installeur", size=6.2,
            color="#6B4E9B", style="italic")
    d.label(75.5, 2.4, "reste bloqué sur « accès refusé ».", size=6.2,
            color="#6B4E9B", style="italic")

    return d.save(OUT / "s14_demarrage.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 15 — Brique 5 : le mode arriere-plan
# ─────────────────────────────────────────────────────────────────────────────
def schema_15_mode_tray() -> str:
    d = Diagram(width=100, height=52)

    d.box(30, 45, 40, 5.5, "L'utilisateur ferme la fenêtre", None, "gris")

    d.box(6, 34, 40, 8, "par défaut  →  la fenêtre est CACHÉE", [
        "le processus et le backend continuent",
        "notifications et enregistrement restent actifs"], "vert")
    d.box(54, 34, 40, 8, "réglage « quitter à la fermeture »", [
        "comportement classique",
        "ou clic sur « Quitter » dans le menu"], "grenat")
    d.path([(50, 45), (50, 43.5), (26, 43.5), (26, 42.3)], lw=1.1)
    d.path([(50, 45), (50, 43.5), (74, 43.5), (74, 42.3)], lw=1.1)

    d.label(26, 31.6, "à la 1ʳᵉ fermeture, une notification explique que l'application",
            size=6.2, color="#1F6F5C", style="italic")
    d.label(26, 29.8, "tourne encore — sinon : « j'ai fermé, mais c'est toujours là ? »",
            size=6.2, color="#1F6F5C", style="italic")

    # Icone
    d.group(1, 2, 47, 24, "L'icône de la barre des tâches", "grenat")
    d.box(4, 16, 20, 5.5, "au repos", ["icône normale"], "gris")
    d.box(26, 16, 20, 5.5, "en captation", ["pastille rouge"], "grenat")
    d.label(24.5, 13.6, "superposée à l'exécution", size=6.0, style="italic",
            color="#8E403C")
    d.label(4, 10.6, "Menu contextuel, reconstruit selon l'état :", size=6.3,
            ha="left", weight="bold")
    d.label(6, 8.2, "en captation   →   durée écoulée  ·  arrêter et générer le CR",
            size=6.2, ha="left")
    d.label(6, 6.0, "au repos         →   démarrer un enregistrement", size=6.2, ha="left")
    d.label(6, 3.8, "réunion dans moins de 15 min   →   raccourci pré-rempli",
            size=6.2, ha="left", color="#8E403C")

    # Notifications
    d.group(52, 2, 47, 24, "Trois mécanismes de notification", "violet")
    d.box(55, 16, 41, 5.5, "« Compte rendu prêt »", ["détection de la transition"], "violet")
    d.box(55, 9.5, 41, 5.5, "Rappel 5 min avant une réunion", ["agenda Microsoft"], "violet")
    d.box(55, 4.5, 41, 4, "Rappel de fin de réunion", None, "violet")
    d.label(75.5, 2.4, "tous par sondage du backend depuis le processus principal",
            size=6.0, style="italic", color="#6B4E9B")

    return d.save(OUT / "s15_mode_tray.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 16 — Brique 6 : navigation a etat
# ─────────────────────────────────────────────────────────────────────────────
def schema_16_navigation() -> str:
    d = Diagram(width=100, height=54)

    d.group(1, 32, 46, 18, "Trois variables d'état — aucun routage", "grenat")
    d.box(4, 43.5, 40, 3.6, "nav            agenda | reports | folders | capture",
          None, "grenat", title_size=6.8)
    d.box(4, 38.8, 40, 3.6, "selected       une réunion ouverte, ou rien",
          None, "grenat", title_size=6.8)
    d.box(4, 34.1, 40, 3.6, "folderFilter   tous | sans dossier | un dossier",
          None, "grenat", title_size=6.8)

    d.group(52, 32, 47, 18, "Canaux d'événements Electron", "violet")
    d.box(54, 43.5, 43, 3.6, "ouvrir une réunion depuis une notification",
          None, "violet", title_size=6.8)
    d.box(54, 38.8, 43, 3.6, "ouvrir un traitement depuis la barre des tâches",
          None, "violet", title_size=6.8)
    d.box(54, 34.1, 43, 3.6, "message de première réduction en arrière-plan",
          None, "violet", title_size=6.8)

    d.label(50, 29.6, "l'état seul détermine ce qui s'affiche", size=7.0,
            weight="bold", color="#333333")
    d.path([(24, 32), (24, 27.5), (50, 27.5), (50, 26.2)], lw=1.1)
    d.path([(75, 32), (75, 27.5), (50, 27.5)], lw=1.1, arrow=False)

    vues = [
        ("MeetingDetail", "une réunion est ouverte", "vert"),
        ("OnboardingView", "page capture", "gris"),
        ("ReportsPage", "liste des comptes rendus", "gris"),
        ("FoldersPage", "les catégories", "gris"),
        ("MeetingsHome", "agenda + timeline — vue par défaut", "grenat"),
    ]
    y = 20.5
    for nom, sub, col in vues:
        d.box(14, y, 72, 4.4, nom, [sub], col, title_size=7.0, line_size=6.0)
        y -= 5.2

    d.label(50, 1.4, "Conséquence : la navigation n'est pas adressable — "
                     "ni lien profond, ni bouton « précédent ».",
            size=6.6, style="italic", color="#8E403C")

    return d.save(OUT / "s16_navigation.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 17 — Brique 6 : la charge de sondage cumulee
# ─────────────────────────────────────────────────────────────────────────────
def schema_17_sondages() -> str:
    import matplotlib.pyplot as plt

    d = Diagram(width=100, height=58)

    d.box(14, 51, 72, 6, "GET  /api/jobs", [
        "renvoie les comptes rendus ET transcripts INTÉGRAUX de tout l'historique"],
        "grenat_f")

    conso = [
        ("Sidebar", "toujours montée", "2,5 s", 2.5, "grenat"),
        ("SearchOverlay", "monté même FERMÉ", "2,5 s", 2.5, "grenat_f"),
        ("MeetingsHome", "sur la vue d'accueil", "4 s", 4.0, "grenat"),
        ("ReportsPage / FoldersPage", "si affichée", "2,5 s", 2.5, "gris"),
        ("Electron — processus principal", "notification « CR prêt »", "5 s", 5.0, "violet"),
    ]
    y = 41
    ys = []
    for nom, note, txt, freq, col in conso:
        d.box(4, y, 44, 5.5, nom, [note], col, title_size=7.0, line_size=6.0)
        ys.append(y + 2.75)
        d.label(57, y + 2.4, "toutes les " + txt, size=6.6, ha="left",
                weight="bold", color="#8E403C")
        w = 26.0 / freq
        d.ax.add_patch(plt.Rectangle((72, y + 1.4), w, 2.4, facecolor="#B2544F",
                                     edgecolor="none", zorder=3))
        d.path([(48, y + 2.75), (52.5, y + 2.75)], lw=0.9, arrow=False)
        y -= 6.6

    # Bus vertical vers l'endpoint
    d.ax.plot([52.5, 52.5], [ys[-1], 48.5], color="#8A8A8A", lw=1.1, zorder=4)
    d.path([(52.5, 48.5), (52.5, 50.7)], lw=1.1)
    d.label(87, 47.5, "fréquence relative", size=6.0, style="italic", color="#999999")

    d.group(2, 1, 96, 10.5, None, "grenat")
    d.label(50, 8.4, "Au repos sur la vue d'accueil : environ deux requêtes par seconde,",
            size=7.4, weight="bold", color="#8E403C")
    d.label(50, 5.6, "chacune rapatriant l'intégralité des comptes rendus et "
                     "transcripts archivés.", size=7.0, color="#333333")
    d.label(50, 2.8, "Le hook de récupération n'est PAS mutualisé : chaque composant "
                     "a son propre intervalle.", size=6.5, style="italic", color="#5A5A5A")

    return d.save(OUT / "s17_sondages.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 18 — Brique 6 : l'aller-retour de l'editeur
# ─────────────────────────────────────────────────────────────────────────────
def schema_18_editeur() -> str:
    d = Diagram(width=100, height=44)

    d.box(3, 36, 22, 6, "compte_rendu.md", ["produit par la brique 3"], "gris")
    d.box(30, 36, 20, 6, "HTML", ["conversion markdown"], "vert")
    d.box(55, 36, 20, 6, "éditeur WYSIWYG", ["édition directe"], "violet")
    d.arrow((25, 39), (30, 39))
    d.arrow((50, 39), (55, 39))

    d.label(85, 39, "frappe utilisateur", size=6.4, style="italic", color="#5A5A5A")
    d.path([(75, 39), (88, 39), (88, 30), (65, 30)], lw=1.1)

    d.box(45, 25.5, 20, 5.5, "temporisation 1 s", None, "gris", title_size=7.0)
    d.box(18, 25.5, 22, 5.5, "retour au markdown", None, "vert")
    d.arrow((45, 28.25), (40, 28.25))

    d.box(3, 16, 37, 6, "PATCH  /api/jobs/{id}/report", ["le backend réécrit le .md"],
          "violet")
    d.box(45, 16, 37, 6, "régénère compte_rendu.docx", ["convertisseur maison"], "violet")
    d.arrow((21.5, 25.5), (21.5, 22.3), lw=1.1)
    d.arrow((40, 19), (45, 19))

    # Regles maison
    d.group(2, 1, 96, 13, "Trois règles de conversion maison pour les tableaux", "grenat")
    d.box(4, 3.5, 30, 5.5, "déballage des cellules", ["retire les paragraphes",
                                                       "insérés par l'éditeur"], "grenat")
    d.box(36, 3.5, 30, 5.5, "reconstruction GFM", ["colonnes normalisées",
                                                    "barres échappées"], "grenat_f")
    d.box(68, 3.5, 30, 5.5, "filet de sécurité", ["aucune balise de tableau",
                                                   "ne doit survivre"], "grenat")
    d.label(50, 10.4, "sans elles, le tableau reste en HTML brut — et le convertisseur "
                      "Word du backend ne lit QUE le markdown : document cassé",
            size=6.4, style="italic", color="#8E403C")

    return d.save(OUT / "s18_editeur.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 19 — Brique 7 : composition de l'installeur et telechargement
# ─────────────────────────────────────────────────────────────────────────────
def schema_19_installeur() -> str:
    d = Diagram(width=100, height=52)

    # Installeur
    d.group(1, 26, 47, 24, "L'installeur  (~200 Mo)", "grenat")
    d.box(4, 40, 41, 5, "code de l'application Electron", None, "grenat")
    d.box(4, 33.5, 41, 5.5, "backend figé par PyInstaller",
          ["+ le modèle de détection de parole"], "grenat")
    d.box(4, 27.5, 41, 5, "interface statique  ·  serveur de modèle", None, "grenat")
    d.label(24.5, 24.0, "AUCUN modèle de langue ni de transcription", size=6.6,
            weight="bold", color="#8E403C")

    # Telechargement
    d.group(52, 26, 47, 24, "Au premier lancement  (~2,3 Go)", "vert")
    d.box(55, 40, 41, 5, "modèle de langue Ministral 3B", ["2,0 Go"], "vert",
          line_size=5.8)
    d.box(55, 33.5, 41, 5.5, "modèles de transcription et d'empreinte",
          ["93 Mo"], "vert", line_size=5.8)
    d.box(55, 27.5, 41, 5, "modèle de découpage sémantique", ["90 Mo"], "vert",
          line_size=5.8)
    d.label(75.5, 24.0, "vers un dossier utilisateur — sans droits administrateur",
            size=6.6, color="#1F6F5C")

    d.arrow((48, 36), (52, 36), lw=1.2)

    # Sources
    d.group(1, 12, 98, 10, "Deux sources, dans cet ordre", "violet")
    d.box(4, 14, 44, 5.5, "1 · dépôt GitHub privé", [
        "URLs autorisées par défaut dans la plupart des SI"], "violet")
    d.box(52, 14, 45, 5.5, "2 · repli automatique", [
        "si la première source échoue ou l'asset manque"], "gris")
    d.arrow((48, 16.75), (52, 16.75))

    d.group(1, 1, 98, 9.5, None, "grenat")
    d.label(50, 8.0, "Découplage volontaire : publier une nouvelle version de "
                     "l'application ne réexpédie pas 2,3 Go à chaque poste.",
            size=7.0, weight="bold", color="#8E403C")
    d.label(50, 5.2, "Reprise sur incident par plage d'octets · 3 tentatives · "
                     "vérification de la taille exacte", size=6.4, color="#333333")
    d.label(50, 2.6, "Le téléchargement est BLOQUANT et précède le démarrage du "
                     "backend — en cas d'échec, l'application se ferme.",
            size=6.4, style="italic", color="#5A5A5A")

    return d.save(OUT / "s19_installeur.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 20 — Brique 7 : les deux jetons et la publication
# ─────────────────────────────────────────────────────────────────────────────
def schema_20_jetons() -> str:
    d = Diagram(width=100, height=50)

    d.group(1, 26, 47, 22, "Machine de build  —  fichier gitignoré", "grenat")
    d.box(4, 38, 41, 6.5, "jeton LECTURE SEULE", [
        "gravé dans le fichier de mise à jour"], "vert")
    d.box(4, 29.5, 41, 6.5, "jeton ÉCRITURE", [
        "ne quitte JAMAIS cette machine"], "grenat_f")

    d.box(55, 38, 42, 6.5, "l'outil d'empaquetage", [
        "lancé en mode « ne jamais publier »"], "violet")
    d.box(55, 29.5, 42, 6.5, "publication par appels API", [
        "création de la version, envoi des fichiers"], "violet")
    d.arrow((45, 41.2), (55, 41.2), lw=1.2)
    d.arrow((45, 32.7), (55, 32.7), lw=1.2)

    d.label(50, 27.6, "l'outil d'empaquetage ne contacte JAMAIS le dépôt : "
                      "sa configuration ne sert qu'à graver le jeton de lecture",
            size=6.4, style="italic", color="#6B4E9B")

    d.box(20, 18.5, 60, 5.5, "installeur publié  +  fichier de version  +  "
                             "carte de blocs", None, "gris")
    d.path([(76, 29.5), (76, 26), (50, 26), (50, 24.3)], lw=1.1)

    d.group(1, 1, 98, 15, "Sur le poste de l'utilisateur", "vert")
    d.box(4, 3, 44, 9, "le jeton de LECTURE embarqué sert à :", [
        "télécharger les mises à jour",
        "télécharger les modèles (schéma 19)"], "vert")
    d.box(52, 3, 45, 9, "risque borné", [
        "lecture seule, sur un seul dépôt",
        "mais EXTRACTIBLE de l'application"], "grenat")
    d.arrow((50, 18.5), (50, 16.3), lw=1.1)

    return d.save(OUT / "s20_jetons.png")


# ─────────────────────────────────────────────────────────────────────────────
#   Schema 21 — Reprise : comptes externes et emplacement des secrets
# ─────────────────────────────────────────────────────────────────────────────
def schema_21_comptes() -> str:
    d = Diagram(width=100, height=52)

    # GitHub
    d.group(1, 16, 31, 34, "GitHub", "grenat")
    d.label(16.5, 45.6, "1 dépôt PRIVÉ, deux usages", size=6.4, style="italic",
            color="#8E403C")
    d.box(3, 37, 27, 6, "versions de l'app", ["étiquettes v X.Y.Z"], "grenat")
    d.box(3, 29.5, 27, 6, "modèles ML", ["étiquette assets-v1"], "grenat")
    d.box(3, 22, 27, 6, "jeton LECTURE seule", ["→ electron/.env"], "vert")
    d.box(3, 17, 27, 4.5, "jeton ÉCRITURE", None, "grenat_f")

    # Microsoft
    d.group(34.5, 16, 31, 34, "Microsoft Entra", "violet")
    d.label(50, 45.6, "1 inscription d'application", size=6.4, style="italic",
            color="#6B4E9B")
    d.box(36.5, 37, 27, 6, "client PUBLIC", ["aucun secret à créer"], "violet")
    d.box(36.5, 29.5, 27, 6, "permission déléguée", ["lecture du calendrier"], "violet")
    d.box(36.5, 22, 27, 6, "flux par code d'appareil", ["à autoriser"], "violet")
    d.box(36.5, 17, 27, 4.5, "identifiants → en dur", None, "gris")

    # Mistral
    d.group(68, 16, 31, 34, "Mistral", "vert")
    d.label(83.5, 45.6, "optionnel — moteur alternatif", size=6.4, style="italic",
            color="#1F6F5C")
    d.box(70, 37, 27, 6, "clé API", ["compte Mistral"], "vert")
    d.box(70, 29.5, 27, 6, "saisie par l'utilisateur", ["dans les paramètres"], "vert")
    d.box(70, 22, 27, 6, "stockée côté poste", ["dossier de réglages"], "vert")
    d.box(70, 17, 27, 4.5, "jamais dans le dépôt", None, "gris")

    # Recap secrets
    d.group(1, 1, 98, 13, "Où vivent les secrets — tous gitignorés", "gris")
    d.box(4, 3, 45, 8, "electron/.env", [
        "les deux jetons GitHub",
        "présent uniquement sur la machine de build"], "grenat")
    d.box(52, 3, 45, 8, "dossier de réglages du poste", [
        "clé Mistral en clair  ·  jetons Microsoft chiffrés",
        "créé à l'usage, jamais versionné"], "violet")

    return d.save(OUT / "s21_comptes.png")


# ─────────────────────────────────────────────────────────────────────────────
ALL = {
    "s1": schema_1_vue_globale,
    "s2": schema_2_trois_chemins,
    "s3": schema_3_pipeline_diarisation,
    "s4": schema_4_modes_clustering,
    "s5": schema_5_threads_captation,
    "s6": schema_6_ducking,
    "s7": schema_7_fenetrage,
    "s8": schema_8_trois_moteurs,
    "s9": schema_9_decoupage_semantique,
    "s10": schema_10_chunk_vers_cr,
    "s11": schema_11_stockage,
    "s12": schema_12_cycle_job,
    "s13": schema_13_orchestration,
    "s14": schema_14_demarrage,
    "s15": schema_15_mode_tray,
    "s16": schema_16_navigation,
    "s17": schema_17_sondages,
    "s18": schema_18_editeur,
    "s19": schema_19_installeur,
    "s20": schema_20_jetons,
    "s21": schema_21_comptes,
}


if __name__ == "__main__":
    for name, fn in ALL.items():
        print(f"[schemas] {name:8} → {fn()}")
