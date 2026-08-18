"""Documentation technique Meeting Assistant — generation du .docx.

Une fonction par section. Les briques sont ajoutees au fur et a mesure ;
`SECTIONS` fixe l'ordre d'assemblage.

    python docs/generate_doc_technique.py

Sortie : docs/Documentation_Technique_Meeting_Assistant.docx
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))

import schemas_meeting_assistant as S
from yele_style import YeleDoc

HERE = Path(__file__).parent
SCH = HERE / "schemas"


# ═════════════════════════════════════════════════════════════════════════════
#   1. Vue d'ensemble
# ═════════════════════════════════════════════════════════════════════════════
def section_1_vue_ensemble(d: YeleDoc) -> None:
    d.h1("1. Vue d'ensemble de la solution")

    d.para(
        "Meeting Assistant est une application de bureau Windows développée pour "
        "Yele Consulting. Elle enregistre une réunion, en produit la transcription "
        "attribuée par locuteur, puis en rédige le compte rendu — le tout "
        "**intégralement en local**, sans qu'aucune donnée audio ni aucun contenu "
        "de réunion ne quitte le poste de l'utilisateur."
    )
    d.para(
        "L'application se présente comme un exécutable unique installé sans droits "
        "administrateur. Elle embarque son propre serveur, ses modèles de "
        "reconnaissance vocale et son modèle de langue."
    )

    d.h3("Composants principaux")
    d.kv_table([
        ("Interface", "Next.js 15 / React 19 en export statique, chargée par Electron"),
        ("Shell", "Electron 33 — supervision du backend, barre des tâches, notifications"),
        ("Backend", "FastAPI (Python) figé par PyInstaller — 28 endpoints, 127.0.0.1 uniquement"),
        ("Transcription", "sherpa-onnx — Zipformer français streaming (kroko)"),
        ("Diarisation", "Silero VAD + WeSpeaker ResNet34 + NME-SC (Park et al. 2020)"),
        ("Compte rendu", "Ministral 3B Q4 sur llama-server local, ou API Mistral au choix"),
        ("Découpage sémantique", "all-MiniLM-L6-v2 — détection des ruptures de sujet"),
        ("Agenda", "Microsoft Graph — device code flow, permission déléguée"),
        ("Stockage", "système de fichiers — Documents/Réunions/, aucune base de données"),
    ], label_w=4.6)

    d.h3("Fonctionnalités clés")
    d.bullets([
        "Captation simultanée du **microphone et du son système** — les participants "
        "distants d'une visioconférence sont donc enregistrés",
        "**Transcription et diarisation en temps réel**, pendant la réunion",
        "**Compte rendu disponible dès l'arrêt de l'enregistrement**, sans attente",
        "Traitement de fichiers audio importés, et import de transcripts Teams",
        "Rattachement automatique aux réunions de l'agenda Microsoft",
        "Édition du compte rendu dans l'application, export Word",
        "Renommage des locuteurs, transcript synchronisé à la lecture audio",
        "Notifications natives — rappel avant réunion, compte rendu prêt",
    ])

    d.warning(
        "Aucune donnée ne sort du poste, à une exception près : si l'utilisateur "
        "choisit explicitement le moteur de compte rendu Mistral, le transcript "
        "est envoyé à l'API de Mistral. Le moteur par défaut est local."
    )

    d.schema(SCH / "s1_vue_globale.png",
             "Schéma 1 — Architecture en couches : présentation, orchestration, traitement")


# ═════════════════════════════════════════════════════════════════════════════
#   2. Architecture technique globale
# ═════════════════════════════════════════════════════════════════════════════
def section_2_architecture(d: YeleDoc) -> None:
    d.h1("2. Architecture technique globale")

    d.para(
        "La solution s'articule en trois couches : la **présentation** (Electron + "
        "Next.js), l'**orchestration** (backend FastAPI), et le **traitement** "
        "(diarisation, transcription, LLM). Une quatrième dimension, le stockage, "
        "repose entièrement sur le système de fichiers."
    )
    d.para(
        "Le point à retenir est que le backend ne calcule presque rien lui-même : "
        "il **lance des sous-processus**. Chaque étape lourde — diarisation, "
        "normalisation, génération du compte rendu — tourne dans un processus "
        "séparé qui meurt à la fin et rend toute sa mémoire. C'est le même "
        "exécutable qui se rappelle lui-même avec une sous-commande."
    )

    d.h2("2.1 Les trois chemins de traitement")
    d.para(
        "Une réunion peut entrer dans l'application de trois façons, qui ne "
        "mobilisent pas les mêmes briques. Comprendre ces trois chemins est le "
        "préalable à la lecture du reste du document."
    )
    d.schema(SCH / "s2_trois_chemins.png",
             "Schéma 2 — Les trois chemins de traitement et leurs branchements")

    d.table(
        ["Cas", "Diarisation", "Compte rendu", "Latence perçue"],
        [
            ["(A) Fichier audio importé", "Brique 1, mode batch",
             "après le traitement", "plusieurs minutes"],
            ["(B) Enregistrement, pipeline live réussi", "Brique 2, en temps réel",
             "produit **pendant** la réunion", "quasi nulle"],
            ["(B') Enregistrement, pipeline live en échec", "Brique 1, mode repli",
             "après le traitement", "plusieurs minutes"],
            ["(C) Transcript texte importé", "aucune",
             "après le traitement", "quelques minutes"],
        ],
        widths=[2.6, 2.2, 2.4, 1.8],
    )

    d.note(
        "Le repli est volontairement binaire : en cas de problème, le pipeline "
        "temps réel n'écrit strictement rien. Le backend décide donc par simple "
        "test d'existence de fichier s'il doit relancer la chaîne complète."
    )

    d.h2("2.2 Flux de données principal")
    d.numbered([
        "L'utilisateur démarre un enregistrement, importe un fichier audio, ou "
        "importe un transcript.",
        "Le backend crée un **dossier de réunion** horodaté dans "
        "`Documents/Réunions/` — ce dossier est la seule donnée persistante.",
        "Selon le cas, la diarisation tourne en temps réel ou en différé, et "
        "produit `transcript.txt` et `turns.json`.",
        "Le transcript est **normalisé** : une phrase par ligne, horodatages retirés.",
        "Le moteur de compte rendu découpe le transcript par sujet, extrait les "
        "décisions et actions, puis assemble `compte_rendu.md`.",
        "Le backend convertit le markdown en `compte_rendu.docx` et purge les "
        "fichiers intermédiaires.",
    ])

    d.h2("2.3 Conventions de communication")
    d.kv_table([
        ("Interface ↔ backend", "HTTP sur 127.0.0.1:8000 — jamais exposé sur le réseau"),
        ("Synchronisation", "sondage périodique (2 à 5 s) — ni WebSocket, ni SSE"),
        ("Electron ↔ interface", "pont de préchargement — événements uniquement, pas de données"),
        ("Backend ↔ traitements", "sous-processus, environnement hérité, sortie relayée ligne à ligne"),
    ], label_w=4.6)


# ═════════════════════════════════════════════════════════════════════════════
#   3. Brique 1 — Diarisation et transcription
# ═════════════════════════════════════════════════════════════════════════════
def section_3_diarisation(d: YeleDoc) -> None:
    d.h1("3. Brique 1 — Diarisation et transcription")

    d.kv_table([
        ("Package", "`diar_pipeline/` — 11 modules, environ 2 400 lignes"),
        ("Point d'entrée", "`backend.exe diar -i AUDIO -o DOSSIER`"),
        ("Rôle", "transformer un fichier audio en transcript attribué par locuteur"),
    ], label_w=3.4)

    d.h2("3.1 Rôle de la brique")
    d.para(
        "**Entrée** — un fichier audio quelconque : m4a, mp3, wav, webm, tout ce "
        "que ffmpeg sait décoder.  **Sortie** — un transcript texte horodaté, "
        "chaque tour de parole préfixé par un identifiant de locuteur."
    )
    d.code("""audio.m4a  ──►  [diar_pipeline]  ──►  transcript.txt

  [00:03.20 - 00:11.45]  SPEAKER_00 : bonjour à tous, on commence par...
  [00:11.45 - 00:19.02]  SPEAKER_01 : oui, sur le point deux justement...""")
    d.para(
        "C'est la seule brique du projet qui ne dépend d'aucune autre : ni du "
        "backend HTTP, ni d'Electron, ni du LLM. Elle est testable seule en ligne "
        "de commande. Tout ce qu'elle consomme, ce sont trois modèles et ffmpeg."
    )
    d.h3("Deux propriétés structurantes")
    d.numbered([
        "**Tout est local.** Aucun appel réseau pendant le traitement. Trois "
        "modèles, tous exécutés sur processeur.",
        "**Transcrire d'abord.** La transcription tourne sur l'audio *entier* "
        "avant la diarisation, et l'attribution des locuteurs se fait *a "
        "posteriori* en recollant les mots aux segments. Ce n'est pas l'ordre "
        "habituel — voir §3.3.",
    ])

    # ── 3.2 ──────────────────────────────────────────────────────────────────
    d.h2("3.2 Quand la brique est appelée")
    d.para("L'application ne diarise pas systématiquement. Quatre situations :")
    d.table(
        ["Situation", "Brique exécutée ?", "Mode de clustering"],
        [
            ["Fichier audio importé", "oui", "**batch**"],
            ["Enregistrement, pipeline live réussi", "non — court-circuitée", "—"],
            ["Enregistrement, pipeline live en échec", "oui, en repli", "**bootstrap + online**"],
            ["Transcript texte importé", "non", "—"],
        ],
        widths=[3.2, 2.0, 2.2],
    )
    d.para(
        "Le court-circuit tient à une seule condition, dans `backend/main.py:607` : "
        "si un `transcript.txt` non vide existe déjà dans le dossier de la réunion, "
        "toute la brique est sautée. Le pipeline temps réel n'écrit ce fichier "
        "**que** s'il a réussi, précisément pour rendre ce repli possible."
    )
    d.note(
        "En pratique, la brique sert donc surtout aux fichiers importés et aux "
        "replis d'enregistrement raté."
    )
    d.para("L'application l'invoque avec exactement trois arguments :")
    d.code("diar  -i <dossier>/audio.<ext>  -o <dossier>  [--bootstrap-online]")
    d.para(
        "Le dernier n'est ajouté que si le job provient d'un enregistrement "
        "(`backend/main.py:615`). Ni `--num-speakers` ni `--no-diarize` ne sont "
        "jamais passés : le nombre de locuteurs est toujours estimé, et la "
        "diarisation toujours active."
    )

    d.h3("Second consommateur : le pipeline temps réel")
    d.para(
        "Le module `audio_capture/live_processor.py` (brique 2) importe "
        "**directement trois morceaux internes** du package :"
    )
    d.table(
        ["Élément importé", "Provenance"],
        [
            ["`BootstrapOnlineClusterer`", "`clustering.py`"],
            ["`_EmbeddingExtractor`", "`embeddings.py`"],
            ["`align_words_to_speakers`, `words_to_turns`, `format_transcript_txt`, `Segment`",
             "`transcription.py`, `models.py`"],
        ],
        widths=[4.6, 2.4],
    )
    d.para(
        "Il réimplémente en revanche sa propre boucle de reconnaissance vocale et "
        "sa propre construction de segments."
    )
    d.warning(
        "Le module d'orchestration `run.py` n'est donc **pas le seul consommateur** "
        "de ces fonctions. Modifier `_EmbeddingExtractor` ou "
        "`BootstrapOnlineClusterer` casse le mode temps réel sans qu'aucun test ni "
        "aucun import visible dans `diar_pipeline` ne le signale."
    )

    d.h3("Pourquoi un sous-processus et pas un import")
    d.bullets([
        "**Isolation mémoire** — la diarisation charge torch, onnxruntime et "
        "sherpa, et monte à plusieurs gigaoctets. Le processus meurt à la fin et "
        "rend tout au système.",
        "**Contrainte de l'exécutable figé** — une fois empaqueté par PyInstaller, "
        "l'exécutable ne peut pas lancer `python -m module`. D'où le répartiteur "
        "multi-mode `backend/run_app.py`, qui réexpose chaque module comme "
        "sous-commande du même exécutable.",
    ])

    # ── 3.3 ──────────────────────────────────────────────────────────────────
    d.h2("3.3 Le pipeline")
    d.para(
        "Sept étapes, orchestrées par `diar_pipeline/run.py:57`, en exécution "
        "**strictement séquentielle** — il n'y a aucun parallélisme entre elles."
    )
    d.schema(SCH / "s3_pipeline_diarisation.png",
             "Schéma 3 — Le pipeline de diarisation en sept étapes")

    d.h3("Pourquoi « transcrire d'abord »")
    d.para(
        "L'approche classique découpe l'audio selon la diarisation, puis transcrit "
        "chaque segment séparément. Ici c'est l'inverse : **un seul passage de "
        "reconnaissance vocale sur tout l'audio**, puis recollage."
    )
    d.para(
        "**Avantage** — le modèle est de type *streaming* et conserve son contexte "
        "sur toute la réunion : pas de mots coupés ni perdus aux frontières de "
        "segments, et un seul chargement de modèle."
    )
    d.para(
        "**Coût** — l'attribution du locuteur devient un problème de recollage "
        "temporel, résolu approximativement (§3.4, étape 7). Aux moments où deux "
        "personnes parlent en même temps, le transcript ne conserve qu'une voix, "
        "attribuée à un seul locuteur."
    )

    # ── 3.4 ──────────────────────────────────────────────────────────────────
    d.h2("3.4 Traitement de l'audio, étape par étape")

    d.h3("Étape 1 — Conversion  (`audio.py`)")
    d.para(
        "L'entrée est normalisée en **16 kHz, mono, WAV** via le ffmpeg embarqué "
        "dans le paquet `imageio-ffmpeg` — il n'y a pas de dépendance à un ffmpeg "
        "système."
    )
    d.code("ffmpeg -y -v error -i <source> -ac 1 -ar 16000 <temp>/{stem}_16k.wav")
    d.para(
        "Le 16 kHz mono n'est pas un choix de confort : c'est le format "
        "d'entraînement des trois modèles. Tout écart dégrade la qualité."
    )
    d.warning(
        "**L'audio source est décodé deux fois.** `convert_to_wav(source)` produit "
        "le WAV utilisé par le VAD et les empreintes ; puis `load_audio_pcm(source)` "
        "relance ffmpeg **sur le fichier d'origine** pour produire le flux destiné "
        "à la reconnaissance vocale (`run.py:89` et `run.py:103`). Deux passes "
        "ffmpeg complètes sur le même fichier, là où le WAV converti aurait pu "
        "servir aux deux."
    )
    d.warning(
        "Le WAV converti est écrit dans le dossier temporaire du système et "
        "**jamais supprimé**. Or le backend nomme toujours le fichier source "
        "`audio.<ext>` — `audio.wav` pour un enregistrement (`main.py:1349`), "
        "`audio{ext}` pour un import (`main.py:1452`). **Tous les traitements "
        "écrivent donc au même chemin temporaire.** Sans conséquence tant qu'ils "
        "sont sérialisés — ce qu'assure le verrou global du backend "
        "(`main.py:546`) — mais c'est une hypothèse implicite à connaître avant "
        "d'envisager le moindre parallélisme."
    )

    d.h3("Étape 2 — Transcription  (`transcription.py`)")
    d.para(
        "La fonction `transcribe()` instancie un reconnaisseur **transducteur** "
        "sherpa-onnx (encodeur, décodeur, joiner, plus le vocabulaire) :"
    )
    d.table(
        ["Réglage", "Valeur"],
        [["`num_threads`", "4"],
         ["`sample_rate`", "16 000"],
         ["`feature_dim`", "80"],
         ["`decoding_method`", "`greedy_search`"],
         ["`enable_endpoint_detection`", "`False`"]],
        widths=[3.0, 4.0],
    )
    d.para(
        "L'audio est poussé dans le flux **par tranches de 0,5 s**, chaque tranche "
        "décodée jusqu'à épuisement. En fin de fichier, **0,5 s de silence** est "
        "ajouté pour vider le tampon du décodeur — sans quoi les derniers mots "
        "seraient perdus."
    )
    d.para(
        "La détection de fin de phrase est **désactivée** : on veut un flux continu "
        "sur toute la réunion, pas une segmentation par le modèle de reconnaissance."
    )
    d.h4("Reconstruction des mots")
    d.para("La fonction `_tokens_to_words()` réassemble les sous-mots :")
    d.bullets([
        "le marqueur SentencePiece (ou une espace) signale un **début de mot** — on "
        "clôture le mot en cours et on en ouvre un nouveau ;",
        "un token sans marqueur est **collé** au mot en cours ;",
        "la ponctuation est recollée au mot précédent, et la fin de ce mot est "
        "repoussée de **+0,08 s**.",
    ])
    d.para("Sortie : une liste de `{word, start, end}`.")

    d.h3("Étape 3 — Détection de parole  (`vad.py`)")
    d.para(
        "Silero VAD découpe le WAV en zones de parole. Paramètres effectifs, fixés "
        "dans `run.py` et différents des valeurs par défaut du module :"
    )
    d.table(
        ["Paramètre", "Valeur", "Effet"],
        [
            ["`threshold`", "0,4", "probabilité de parole minimale (défaut du module : 0,45)"],
            ["`min_speech_duration_ms`", "200", "ignore les salves de parole de moins de 200 ms"],
            ["`min_silence_duration_ms`", "50", "ne coupe pas sur un silence plus court"],
            ["`speech_pad_ms`", "20", "marge ajoutée de part et d'autre de chaque zone"],
        ],
        widths=[2.6, 0.9, 3.9],
    )
    d.para(
        "Sortie : une liste de zones `(début, fin)` — **sans locuteur**. Le VAD "
        "répond « quelqu'un parle », pas « qui parle »."
    )
    d.warning(
        "**La fonction de lecture audio officielle de Silero est délibérément "
        "contournée** (`vad.py:57`). Elle tire `torchaudio` en version récente et "
        "`torchcodec`, deux dépendances lourdes et pénibles à figer sous "
        "PyInstaller. Le WAV est lu avec `soundfile` et le tenseur construit à la "
        "main — possible parce que l'étape 1 garantit déjà du 16 kHz mono. Un "
        "rééchantillonnage de secours subsiste dans la fonction, au cas où elle "
        "serait appelée sur un WAV non converti."
    )

    d.h3("Étape 4 — Empreintes vocales  (`embeddings.py`)")
    d.para(
        "Chaque zone de parole est découpée en fenêtres, et chaque fenêtre passée "
        "au modèle d'empreinte qui en extrait un vecteur de **256 dimensions** "
        "caractérisant la voix."
    )
    d.h4("Règle de fenêtrage")
    d.table(
        ["Durée de la zone", "Traitement"],
        [
            ["moins de 0,4 s", "**ignorée** — aucune empreinte produite"],
            ["moins de 1,8 s  (= 1,2 s × 1,5)", "**une seule fenêtre** couvrant toute la zone"],
            ["1,8 s ou plus",
             "fenêtre glissante de **1,2 s**, pas de **0,6 s** (50 % de "
             "recouvrement) ; la dernière fenêtre est tronquée à la fin de la zone"],
        ],
        widths=[2.4, 4.6],
    )
    d.para(
        "Le compromis derrière la fenêtre de 1,2 s : trop courte, l'empreinte "
        "vocale est instable ; trop longue, on risque d'englober deux locuteurs "
        "dans la même fenêtre. Le recouvrement de 50 % limite le second effet sans "
        "multiplier le coût."
    )
    d.note(
        "Ordre de grandeur — une réunion d'une heure avec 80 % de parole produit "
        "**environ 4 800 empreintes**. Cette valeur pilote tout le coût du "
        "clustering (§3.8)."
    )
    d.h4("Deux chemins d'extraction")
    d.table(
        ["Méthode", "Usage", "Fonctionnement"],
        [
            ["`extract(chemin)`", "mode batch",
             "écrit **un fichier WAV temporaire par fenêtre**, le passe au modèle, "
             "puis le supprime — soit environ 4 800 cycles création / écriture / "
             "lecture / suppression"],
            ["`extract_from_array(pcm)`", "mode temps réel",
             "la bibliothèque exigeant un chemin de fichier, **un seul** "
             "temporaire est créé puis réécrit à chaque appel ; le commentaire du "
             "code annonce un facteur ~5 sur le coût disque sous Windows"],
        ],
        widths=[2.4, 1.4, 3.2],
    )
    d.para(
        "Le mode batch pourrait utiliser la seconde méthode, mais ne le fait pas "
        "(§3.8)."
    )
    d.warning(
        "**Le modèle d'empreinte est chargé depuis un chemin explicite, jamais via "
        "l'API automatique de la bibliothèque** (`embeddings.py:66`). Celle-ci "
        "déclencherait un téléchargement au premier appel — impossible dans une "
        "application qui tourne hors ligne, d'autant que l'environnement d'exécution "
        "interdit explicitement tout accès distant aux dépôts de modèles."
    )

    d.h3("Étape 5 — Regroupement des voix  (`clustering.py`)")
    d.para(
        "Deux questions : **combien de locuteurs**, puis **quel locuteur pour "
        "chaque empreinte**. Le nombre n'est jamais demandé à l'utilisateur."
    )
    d.code("""cluster_speakers(emb, method="sc", enhance=True, estimate_method="nmesc")
    │
    ├─ normalisation L2 des empreintes
    ├─ k = estimate_speakers_nmesc(emb)           ← combien de locuteurs
    └─ labels = cluster_sc(emb, k, enhance=True)   ← qui est qui""")

    d.h4("Estimation du nombre de locuteurs — NME-SC")
    d.para(
        "`clustering.py:191` — réimplémentation fidèle de l'algorithme 1 de **Park "
        "et al. 2020**, *Auto-Tuning Spectral Clustering*."
    )
    d.para(
        "Le problème : pour regrouper les voix, on construit un graphe de "
        "similarité entre empreintes, et il faut décider combien de voisins garder "
        "par nœud. Ce paramètre change le résultat, et il n'existe pas de bonne "
        "valeur universelle. L'idée de NME-SC est de **balayer ce paramètre et de "
        "retenir celui qui produit la structure la plus nette**."
    )
    d.para("Pour chaque valeur de p (nombre de voisins conservés par ligne) :")
    d.numbered([
        "binarisation — on ne garde que les p plus fortes similarités par ligne ;",
        "symétrisation de la matrice obtenue ;",
        "construction du laplacien non normalisé ;",
        "décomposition en valeurs propres ;",
        "calcul des écarts entre valeurs propres consécutives, plafonnés ;",
        "calcul de la valeur NME — plus grand écart rapporté à la plus grande "
        "valeur propre ;",
        "calcul du rapport p / valeur NME.",
    ])
    d.para(
        "On retient ensuite le p qui **minimise ce rapport**, et le nombre de "
        "locuteurs se lit dans la position du **plus grand écart entre valeurs "
        "propres consécutives**."
    )
    d.kv_table([
        ("Balayage", "de 1 à 25 % du nombre d'empreintes, échantillonné en 30 valeurs au plus"),
        ("Contrôle de connexité", "si le graphe retenu n'est pas connexe, on remonte "
                                  "le balayage jusqu'au premier qui l'est"),
        ("Bornes", "le nombre de locuteurs est ramené dans l'intervalle [1, 20]"),
    ], label_w=4.6)
    d.warning(
        "**Décomposition dense obligatoire** (`clustering.py:250`). Le code utilise "
        "une décomposition dense, pas une méthode creuse, alors que celle-ci serait "
        "bien plus rapide puisqu'on ne veut que les plus petites valeurs propres. "
        "Raison documentée dans le code : la méthode creuse **n'est pas "
        "déterministe** sous calcul multi-thread et faisait basculer le nombre de "
        "locuteurs d'un lancement à l'autre sur un audio identique — cas cité : un "
        "enregistrement oscillant entre 3 et 5 locuteurs, avec un taux d'erreur "
        "passant de 0,13 à 0,27. La version dense est plus lente mais stable "
        "bit à bit. Ne pas « optimiser » ce point sans reproduire d'abord ce test."
    )
    d.warning(
        "**Le calcul matriciel doit être forcé en mono-thread avant tout import de "
        "numpy.** Même cause : en multi-thread, la décomposition donne des "
        "résultats variables d'un lancement à l'autre. Ce bloc est présent **trois "
        "fois** — dans `diar_pipeline/__init__.py`, `diar_pipeline/run.py` et "
        "`backend/run_app.py` — parce que chacun de ces fichiers peut être le "
        "premier point d'entrée selon le chemin d'appel. Une fois les "
        "bibliothèques de calcul chargées, les variables n'ont plus aucun effet.\n"
        "C'est aussi pour cette raison que le balayage est **séquentiel** et non "
        "parallélisé — et donc que la diarisation n'exploite qu'un seul cœur sur "
        "ses étapes les plus lourdes."
    )

    d.h4("Raffinement de la matrice d'affinité")
    d.para(
        "`clustering.py:62` — appliqué avant le clustering. Objectif : réduire le "
        "bruit entre locuteurs dans la matrice de similarité. Sept étapes, dans "
        "cet ordre :"
    )
    d.code("""remplissage diagonal  →  flou gaussien (σ=1)  →  seuillage par ligne
   →  symétrisation  →  diffusion (A·Aᵀ)  →  normalisation par ligne
   →  symétrisation""")
    d.warning(
        "La **symétrisation finale** n'est pas décorative : la normalisation par "
        "ligne casse la symétrie, et le laplacien exige une matrice symétrique. Le "
        "commentaire du code marque explicitement ce point."
    )

    d.h4("Assignation — Spectral Clustering")
    d.para(
        "`clustering.py:301` — Spectral Clustering sur affinité précalculée, "
        "assignation par k-moyennes, graine fixée. La similarité cosinus, "
        "naturellement dans [-1, 1], est ramenée dans [0, 1]."
    )

    d.h4("Les deux modes de clustering")
    d.schema(SCH / "s4_modes_clustering.png",
             "Schéma 4 — Clustering batch et clustering bootstrap + online")
    d.para(
        "Le mode **bootstrap + online** (`clustering.py:648`) est activé par "
        "`--bootstrap-online`, donc pour les enregistrements faits dans "
        "l'application. Il procède en trois temps :"
    )
    d.numbered([
        "NME-SC et Spectral Clustering classiques sur les **1 000 premières "
        "empreintes** — environ 10 minutes de parole ;",
        "calcul des centroïdes par locuteur et d'un **seuil cosinus auto-calibré** : "
        "point milieu entre le premier décile des similarités internes et le "
        "neuvième décile des similarités externes, borné à [0,3 ; 0,85] ;",
        "le reste des empreintes est assigné séquentiellement au centroïde le plus "
        "proche, avec mise à jour incrémentale de ce centroïde.",
    ])
    d.para(
        "En dessous de 1 000 empreintes, la fonction retombe silencieusement sur le "
        "clustering batch."
    )
    d.para(
        "**Pourquoi ce mode existe :** il évite de faire tourner NME-SC, dont le "
        "coût est cubique, sur l'intégralité d'une longue réunion ; et il fournit "
        "une logique compatible avec le temps réel, où l'on ne dispose jamais de la "
        "vue globale de l'audio."
    )
    d.para(
        "Une variante à état, `BootstrapOnlineClusterer` (`clustering.py:731`), "
        "applique la même idée mais alimentée empreinte par empreinte. Elle est "
        "utilisée **uniquement par le pipeline temps réel**, et documentée ici "
        "parce qu'elle partage le code ci-dessus."
    )
    d.warning(
        "**Le gel après amorçage est un correctif, pas une simplification.** Passée "
        "la phase d'amorçage, la classe **n'ajoute plus jamais de locuteur** : toute "
        "empreinte est attribuée au centroïde le plus proche. Sans cette contrainte, "
        "les empreintes bruitées — fenêtres de 1,2 s mal filtrées par le VAD — ne "
        "ressemblaient à aucun centroïde et créaient des locuteurs fantômes en "
        "série : **dérive observée de 5 à plus de 25 locuteurs sur une réunion "
        "d'une heure**. Le seuil ne sert plus qu'à décider si l'on met à jour le "
        "centroïde (correspondance nette) ou non (correspondance faible : on "
        "assigne sans polluer).\n"
        "**Hypothèse assumée** — tous les locuteurs parlent dans les dix premières "
        "minutes. Vrai en pratique sur des réunions professionnelles, où l'on "
        "commence par un tour de table. Un participant arrivant en retard est "
        "rattaché au locuteur acoustiquement le plus proche : compromis accepté."
    )

    d.h3("Étape 6 — Construction des segments  (`segments.py`)")
    d.para("Les étiquettes par fenêtre deviennent des segments de parole continus :")
    d.numbered([
        "chaque fenêtre devient un triplet (début, fin, locuteur) ;",
        "les zones de parole **sans empreinte** — celles de moins de 0,4 s, écartées "
        "à l'étape 4 — récupèrent le locuteur du sous-segment le plus proche dans le "
        "temps, par recherche exhaustive ;",
        "tri chronologique, puis **fusion** des segments consécutifs d'un même "
        "locuteur séparés de moins de **0,7 s**.",
    ])
    d.para(
        "Ce dernier point évite un transcript haché : sans lui, une micro-pause au "
        "milieu d'une phrase produirait deux tours de parole distincts pour le même "
        "locuteur."
    )

    d.h3("Étape 7 — Alignement mots ↔ locuteurs  (`transcription.py`)")
    d.para(
        "C'est ici que les deux branches du pipeline se rejoignent : d'un côté les "
        "mots horodatés, de l'autre les segments avec locuteur."
    )
    d.para(
        "La fonction `align_words_to_speakers()`, dite **midpoint**, procède mot par "
        "mot : on prend l'**instant médian** du mot et on cherche le segment de "
        "diarisation qui le contient. Si le mot tombe dans un trou entre deux "
        "segments, on prend le plus proche des deux. Le balayage utilise un curseur "
        "conservé d'un mot au suivant, donc le coût reste linéaire."
    )
    d.para(
        "Les mots consécutifs d'un même locuteur sont ensuite regroupés en tours de "
        "parole, et le fichier texte horodaté est produit."
    )
    d.note(
        "Le module calcule **aussi** une seconde stratégie, `align_words_by_"
        "boundaries` : au lieu de décider mot par mot, elle relève les instants de "
        "changement de locuteur et cale chacun sur le point, le point "
        "d'exclamation ou le point d'interrogation le plus proche dans une fenêtre "
        "de ±5 s. L'intention est bonne — un changement de locuteur tombe rarement "
        "au milieu d'une phrase — mais sa sortie est écrite sur disque et "
        "**jamais lue**. C'est du temps de calcul et trois fichiers pour rien à "
        "chaque traitement."
    )

    # ── 3.5 ──────────────────────────────────────────────────────────────────
    d.h2("3.5 Modèles utilisés")
    d.para(
        "Trois modèles, tous au format ONNX, tous exécutés sur processeur, tous "
        "attendant du 16 kHz mono."
    )
    d.table(
        ["Modèle", "Étape", "Rôle", "Sortie", "Taille"],
        [
            ["Silero VAD", "3", "détecter les zones de parole",
             "intervalles (début, fin)", "0,6 Mo"],
            ["Zipformer FR streaming (kroko)", "2", "transcription française",
             "sous-mots + horodatages", "67,7 Mo"],
            ["WeSpeaker ResNet34-LM (VoxCeleb)", "4", "empreinte vocale",
             "vecteur 256 dim.", "25,3 Mo"],
        ],
        widths=[2.5, 0.7, 1.9, 1.5, 0.9],
    )
    d.h3("Points à connaître")
    d.bullets([
        "**Le Zipformer est *streaming*, pas *offline*.** C'est ce qui permet de "
        "l'alimenter par tranches de 0,5 s tout en gardant le contexte, et c'est le "
        "même modèle qui sert au pipeline temps réel. Un modèle *offline* donnerait "
        "sans doute une meilleure qualité en différé, au prix de perdre cette "
        "mutualisation.",
        "**Le ResNet34 est entraîné sur VoxCeleb**, corpus majoritairement "
        "anglophone. Les empreintes restent discriminantes quelle que soit la "
        "langue — c'est la voix qui est modélisée, pas le contenu — mais ce n'est "
        "pas un modèle spécialisé français, contrairement à la reconnaissance vocale.",
        "**Aucun des trois n'est ré-entraîné** sur les données du projet.",
    ])
    d.h3("Résolution des chemins")
    d.para(
        "Le code cherche le modèle de reconnaissance vocale dans la variable "
        "d'environnement `SHERPA_DIR` (`transcription.py:22`) et le modèle "
        "d'empreinte dans `PRETRAINED_DIR` (`embeddings.py:23`), avec repli sur les "
        "dossiers du dépôt source. Ces variables sont renseignées par "
        "l'application — voir la brique « Build & distribution »."
    )
    d.note(
        "Silero est embarqué dans l'exécutable du backend ; les deux autres sont "
        "téléchargés au premier lancement de l'application."
    )

    # ── 3.6 ──────────────────────────────────────────────────────────────────
    d.h2("3.6 Configuration effective")
    d.para(
        "Toute la configuration réelle est **codée en dur** en tête de "
        "`diar_pipeline/run.py`. Il n'y a ni fichier de configuration, ni réglage "
        "exposé dans l'interface."
    )
    d.code("""EMBED_MODEL          = "resnet34"    # empreintes 256 dimensions
ESTIMATE_METHOD      = "nmesc"       # estimation du nombre de locuteurs
CLUSTER_METHOD       = "sc"          # spectral clustering
ENHANCE              = True          # raffinement de la matrice d'affinité
WIN_LEN              = 1.2           # fenêtre d'empreinte (s)
HOP_LEN              = 0.6           # pas d'empreinte (s)
VAD_MODEL            = "silero"
VAD_THRESHOLD        = 0.4
VAD_MIN_SPEECH_MS    = 200
VAD_MIN_SILENCE_MS   = 50
VAD_PAD_MS           = 20""")
    d.h3("Ce que l'application passe réellement")
    d.table(
        ["Argument", "Passé par le backend"],
        [
            ["`-i, --input`", "**oui**, toujours — `<dossier>/audio.<ext>`"],
            ["`-o, --output-dir`", "**oui**, toujours — le dossier de la réunion"],
            ["`--bootstrap-online`", "**oui**, si le job provient d'un enregistrement"],
            ["`--num-speakers N`", "**non** — le nombre de locuteurs est toujours estimé"],
            ["`--no-diarize`", "**non** — la diarisation est toujours active, et une "
                               "demande contraire venant d'un client obsolète est "
                               "explicitement ignorée (`main.py:601`)"],
        ],
        widths=[2.2, 4.8],
    )
    d.para(
        "Pour ajuster le VAD ou le fenêtrage, il faut **modifier le code**. C'est "
        "un choix assumé — un seul jeu de réglages a été validé — mais c'est le "
        "premier point de friction pour qui veut faire varier le comportement."
    )

    # ── 3.7 ──────────────────────────────────────────────────────────────────
    d.h2("3.7 Fichiers produits")
    d.para(
        "Avec un fichier source `audio.m4a` dans le dossier de la réunion :"
    )
    d.table(
        ["Fichier", "Consommé par"],
        [
            ["`audio.transcript.midpoint.txt`",
             "**le backend** — renommé `transcript.txt`, puis normalisé et envoyé au LLM"],
            ["`audio.turns.json`",
             "**le backend** — renommé `turns.json`, alimente le transcript "
             "synchronisé à la lecture audio"],
            ["`audio.words.json`, `audio.words_midpoint.json`, "
             "`audio.turns_midpoint.json`, `audio.words_per_speaker.json`",
             "débogage"],
            ["`audio.words_boundary.json`, `audio.turns_boundary.json`, "
             "`audio.transcript.boundary.txt`",
             "stratégie d'alignement non retenue (§3.4, étape 7)"],
            ["`audio.rttm`, `audio.diarization.txt`",
             "évaluation hors application, inspection manuelle"],
        ],
        widths=[3.4, 3.6],
    )
    d.note(
        "**Deux fichiers sur dix sont réellement utilisés.** Les huit autres "
        "restent dans le dossier de réunion, que l'utilisateur voit dans "
        "l'Explorateur via « Ouvrir le dossier ». Le format RTTM est le standard "
        "NIST de la diarisation : c'est lui qui permet de calculer un taux "
        "d'erreur contre une référence annotée, si l'on veut mesurer la qualité."
    )

    # ── 3.8 ──────────────────────────────────────────────────────────────────
    d.h2("3.8 Limites connues")

    d.h3("Coût cubique du clustering en mode batch")
    d.para(
        "L'estimation du nombre de locuteurs effectue une décomposition dense sur "
        "une matrice N × N, **pour chacune des 30 valeurs balayées**. Le coût croît "
        "donc comme le cube du nombre d'empreintes. L'assignation par Spectral "
        "Clustering ajoute une seconde décomposition du même ordre."
    )
    d.table(
        ["Durée de réunion", "Empreintes (≈ 80 % de parole)", "Coût relatif"],
        [["10 min", "≈ 800", "1×"],
         ["30 min", "≈ 2 400", "≈ 27×"],
         ["60 min", "≈ 4 800", "≈ 216×"]],
        widths=[2.2, 3.0, 1.8],
    )
    d.note(
        "Extrapolation à partir de la complexité algorithmique — ce n'est pas une "
        "mesure. Aucun chiffre de performance de ce document ne provient d'un banc "
        "d'essai réel."
    )
    d.para(
        "Le mode bootstrap résout exactement ce problème en plafonnant l'estimation "
        "à 1 000 empreintes. **Mais il n'est appliqué qu'aux enregistrements**, pas "
        "aux fichiers importés — qui sont pourtant les plus susceptibles d'être "
        "longs, et les seuls pour lesquels la brique tourne systématiquement (§3.2). "
        "C'est le principal risque de performance de la brique."
    )
    d.para("Trois pistes, par coût d'implémentation croissant :")
    d.numbered([
        "activer `--bootstrap-online` aussi pour les imports au-delà d'un seuil de "
        "durée — une ligne dans `backend/main.py:615` ;",
        "sous-échantillonner les empreintes fournies à l'estimation, qui n'a pas "
        "besoin de la résolution complète, puis clusteriser sur l'ensemble ;",
        "réduire le nombre de valeurs balayées — gain seulement linéaire.",
    ])

    d.h3("Parole simultanée")
    d.para(
        "Perdue par construction. Le VAD ne détecte pas la parole superposée, une "
        "empreinte calculée sur une fenêtre à deux voix est un mélange, et la "
        "reconnaissance vocale ne transcrit qu'un flux. Quand deux personnes se "
        "coupent, le transcript n'en garde qu'une."
    )

    d.h3("Travail calculé pour rien")
    d.bullets([
        "**Second alignement** — calculé à chaque traitement, trois fichiers "
        "écrits, aucun consommateur. Soit le brancher, soit le retirer.",
        "**Double décodage ffmpeg** — deux passes complètes sur le fichier source.",
        "**Fichiers temporaires d'empreinte** — environ 4 800 cycles disque en mode "
        "batch, alors qu'une variante en mémoire existe déjà.",
    ])

    d.h3("Points mineurs")
    d.bullets([
        "La construction des segments cherche le plus proche voisin par recherche "
        "exhaustive — sans impact tant que les zones de moins de 0,4 s restent rares.",
        "Collision de fichiers temporaires sur le WAV converti (§3.4, étape 1).",
        "**Aucun test automatisé** ne couvre cette brique. La vérification est "
        "manuelle.",
    ])

    # ── 3.9 ──────────────────────────────────────────────────────────────────
    d.h2("3.9 Vérifier le fonctionnement")
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"

# ce que fait l'application sur un fichier importé
python -m diar_pipeline.run -i "reunion.m4a" -o ".\\_test_diar"

# ce que fait l'application sur un enregistrement (repli)
python -m diar_pipeline.run -i "reunion.m4a" -o ".\\_test_diar" --bootstrap-online

# débogage : force le nombre de locuteurs et court-circuite l'estimation
python -m diar_pipeline.run -i "reunion.m4a" --num-speakers 4""")
    d.para(
        "Forme de la sortie console — les valeurs sont illustratives, la brique n'a "
        "pas de chiffres de référence mesurés et versionnés :"
    )
    d.code("""============================================================
  DIARISATION + TRANSCRIPTION — reunion.m4a
============================================================
  [1] audio -> reunion_16k.wav (….…s)  ….…s
  [2] Transcription (sherpa-onnx)...
        10.0% | …s/…s | RTF ….…x        <- progression tous les 10 %
      -> N words  ….…s
  [3] VAD: N segments  ….…s
  [4] Embeddings: N x 256  ….…s          <- la dimension DOIT etre 256
  [5] Clustering (batch): K speakers  ….…s
  [6] Aligning N words to K speakers...
      midpoint: N turns | boundary: N turns | speakers: {...}
============================================================
  DONE  —  Duration / Speakers / Words / Time (RTF global) / Output
============================================================""")
    d.h3("Points de contrôle")
    d.table(
        ["Trace", "Interprétation"],
        [
            ["`[4] Embeddings: N x 256`",
             "la dimension **doit** être 256 — sinon mauvais modèle d'empreinte, ou "
             "fichier ONNX introuvable"],
            ["`[5] Clustering: 1 speaker`",
             "sur une réunion à plusieurs voix, signale presque toujours un problème "
             "de qualité audio en amont — capture d'un seul micro, son système non "
             "capté — et non un défaut du clustering"],
            ["`RTF` de l'étape [2]",
             "concerne la reconnaissance vocale seule. Le RTF global, en fin de "
             "traitement, inclut le clustering : c'est lui qui explose sur les longs "
             "fichiers (§3.8)"],
            ["Fichiers de sortie",
             "`transcript.midpoint.txt` **et** `turns.json` doivent être présents. "
             "Sans le premier, le backend lève une erreur de fichier manquant et le "
             "traitement échoue (`main.py:624`)"],
        ],
        widths=[2.4, 4.6],
    )

    # ── 3.10 ─────────────────────────────────────────────────────────────────
    d.h2("3.10 Ce qui n'est pas utilisé dans l'application")
    d.para(
        "Le package contient du code hérité de la phase de recherche. Il n'est "
        "appelé par aucun chemin de l'application et ne doit pas être pris pour de "
        "la logique de production."
    )
    d.table(
        ["Élément", "Statut"],
        [
            ["`refinement.py` — raffinement VBx",
             "exporté par le module, **jamais appelé** ; l'orchestrateur ne "
             "l'importe même pas"],
            ["`tracking.py` — MLflow, taux d'erreur, silhouette, projection UMAP",
             "**jamais appelé**. Vestige de la phase d'évaluation"],
            ["`estimate_speakers_gmm_bic`",
             "seconde méthode d'estimation, atteignable seulement par un paramètre "
             "que personne ne passe"],
            ["`cluster_ahc`, `cluster_ahc_threshold`, `cluster_meanshift`, "
             "`cluster_cosine_greedy`",
             "quatre méthodes de clustering alternatives, jamais sélectionnées"],
            ["Second moteur de détection de parole",
             "exigerait un jeton externe et l'acceptation d'une licence. Jamais activé"],
            ["Modèles d'empreinte `campplus` (512 dim.) et `ecapa` (192 dim.)",
             "**leurs fichiers ne sont ni livrés ni téléchargés** — les "
             "sélectionner échouerait à l'instanciation"],
            ["Alignement `boundary`",
             "seule exception : il **est** exécuté à chaque traitement, mais sa "
             "sortie n'est consommée par personne"],
        ],
        widths=[3.0, 4.0],
    )
    d.note(
        "**Recommandation de reprise** — ne pas supprimer en bloc. Le module de "
        "suivi et les méthodes de clustering alternatives constituent "
        "l'infrastructure qui a servi à choisir la configuration actuelle ; elles "
        "resservent dès qu'il faut rejustifier un choix ou comparer une nouvelle "
        "approche. En revanche, l'alignement non consommé mérite soit d'être "
        "branché, soit d'être retiré."
    )

    # ── 3.11 ─────────────────────────────────────────────────────────────────
    d.h2("3.11 Résumé pour une reprise")
    d.numbered([
        "Le pipeline **transcrit d'abord** : reconnaissance vocale sur tout "
        "l'audio, puis recollage des locuteurs par instant médian de chaque mot. "
        "Les chevauchements de parole sont perdus par construction.",
        "La brique **ne tourne pas systématiquement** : elle est court-circuitée dès "
        "que le pipeline temps réel a produit un transcript. En pratique elle sert "
        "surtout aux **fichiers importés**.",
        "**Trois modèles ONNX sur processeur**, aucun ré-entraîné : Silero pour la "
        "détection de parole, Zipformer français *streaming* pour la transcription, "
        "WeSpeaker ResNet34 pour les empreintes vocales.",
        "Le cœur algorithmique est **NME-SC** pour estimer le nombre de locuteurs, "
        "puis **Spectral Clustering** pour les assigner.",
        "Le pipeline temps réel **importe directement des morceaux internes** du "
        "package. Aucun test ne protège ce contrat.",
        "La configuration est **codée en dur** ; l'application ne passe que trois "
        "arguments.",
        "Les contraintes signalées par un avertissement sont des **correctifs de "
        "défauts reproduits** — le code les justifie en commentaire, les défaire "
        "fait revenir le problème.",
    ])
    d.note(
        "**Premier chantier si l'on doit améliorer quelque chose** — le coût "
        "cubique du clustering en mode batch sur les fichiers importés longs "
        "(§3.8). La correction la moins risquée tient en une ligne côté backend."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   4. Brique 2 — Captation audio et pipeline temps réel
# ═════════════════════════════════════════════════════════════════════════════
def section_4_captation(d: YeleDoc) -> None:
    d.h1("4. Brique 2 — Captation audio et pipeline temps réel")

    d.kv_table([
        ("Modules", "`audio_capture/recorder.py` (720 l.) et "
                    "`audio_capture/live_processor.py` (620 l.)"),
        ("Déclenchement", "`POST /api/record/start`"),
        ("Rôle", "capter le son de la réunion et produire le transcript "
                 "**pendant** qu'elle se déroule"),
    ], label_w=3.4)

    d.h2("4.1 Rôle de la brique")
    d.para(
        "C'est le chemin normal quand l'utilisateur clique sur « Enregistrer » "
        "dans l'application. Deux choses se passent **simultanément** : l'audio "
        "est accumulé pour produire le fichier final, et il est traité au fil de "
        "l'eau pour produire le transcript."
    )
    d.para(
        "Au moment où l'utilisateur clique sur Stop, **le transcript est déjà "
        "quasiment terminé**. C'est toute la raison d'être de cette brique : un "
        "compte rendu disponible quelques secondes après la fin d'une réunion "
        "d'une heure, au lieu des minutes de diarisation qu'exigerait le même "
        "fichier importé (§3.8)."
    )

    d.h2("4.2 Les trois issues possibles")
    d.para("L'arrêt de l'enregistrement peut se terminer de trois façons :")
    d.table(
        ["Issue", "Condition", "Conséquence"],
        [
            ["**Succès**", "le transcript a été écrit",
             "brique 1 **court-circuitée** ; on enchaîne sur la normalisation et "
             "le compte rendu"],
            ["**Succès + LLM**", "le LLM temps réel a aussi produit le compte rendu",
             "le traitement est marqué terminé immédiatement — l'utilisateur n'a "
             "rien à lancer"],
            ["**Échec**", "la finalisation échoue, rien n'est écrit",
             "**repli sur la brique 1**, en mode bootstrap + online"],
        ],
        widths=[1.6, 2.4, 3.0],
    )
    d.para(
        "Le mécanisme de repli est délibérément binaire : le pipeline temps réel "
        "**n'écrit rien du tout** en cas de problème, plutôt que d'écrire un "
        "transcript partiel. C'est ce qui permet au backend de décider par simple "
        "test d'existence de fichier (`backend/main.py:607`)."
    )
    d.note(
        "Un fichier marqueur `.origin.recording` est déposé dans le dossier de la "
        "réunion (`main.py:1352`). Il sert à se souvenir, même après un "
        "redémarrage de l'application, que ce dossier vient d'un enregistrement — "
        "et donc qu'en cas de repli il faut lancer la brique 1 en mode "
        "bootstrap + online."
    )

    d.h2("4.3 Architecture — qui tourne en parallèle de quoi")
    d.para("Sept threads coexistent pendant une captation.")
    d.schema(SCH / "s5_threads_captation.png",
             "Schéma 5 — Les sept threads d'une captation, de la carte son au transcript")

    d.h3("Le démarrage différé — un point de conception important")
    d.para(
        "L'endpoint de démarrage lance le magnétophone **immédiatement**, mais le "
        "chargement des modèles part dans un thread de fond (`main.py:1294`). La "
        "réponse HTTP revient tout de suite."
    )
    d.para(
        "**Pourquoi :** charger les trois modèles prend **15 à 20 secondes**. Si "
        "l'on attendait, on perdrait les vingt premières secondes de la réunion — "
        "souvent le moment où l'on annonce l'ordre du jour."
    )
    d.para(
        "**La solution :** le processeur temps réel se déclare actif dès sa "
        "construction, donc il accepte les chunks avant même que ses workers "
        "existent. Ceux-ci s'empilent dans les files et les workers les rattrapent "
        "au démarrage. La trace le dit explicitement : « la file contient N chunks "
        "audio en attente »."
    )
    d.warning(
        "**Les files sont bornées à 15 000 éléments** "
        "(`live_processor.py:56`). Au-delà, la mise en file échoue et le chunk est "
        "**silencieusement perdu** — l'exception est capturée sans rien "
        "journaliser. Le commentaire juste au-dessus (« ne devrait pas arriver avec "
        "une queue non bornée ») est **périmé** : la file *est* bornée. Tant que "
        "les workers tiennent le temps réel, le cas ne se produit pas ; s'ils "
        "décrochent durablement, l'audio est perdu sans aucun signal."
    )

    # ── 4.4 ──────────────────────────────────────────────────────────────────
    d.h2("4.4 La captation")

    d.h3("Deux sources simultanées")
    d.table(
        ["Source", "Bibliothèque", "Ce qu'elle capte"],
        [
            ["Microphone", "`sounddevice`, WASAPI **shared**",
             "la voix des personnes présentes dans la pièce"],
            ["Sortie système (loopback)", "`pyaudiowpatch`",
             "la voix des participants distants — Teams, Zoom…"],
        ],
        widths=[1.9, 2.1, 3.0],
    )
    d.para(
        "Le mode **shared** du microphone n'est pas un détail : en mode exclusif, "
        "l'ouverture du flux prendrait la main sur le périphérique et "
        "**empêcherait Teams ou Zoom de l'utiliser**. On ne peut pas enregistrer "
        "une visioconférence dont on a volé le micro."
    )
    d.para(
        "Format commun : **16 kHz, mono, virgule flottante** — celui qu'attendent "
        "les modèles de la brique 1."
    )

    d.h3("Détection du loopback — trois niveaux de repli")
    d.numbered([
        "**`pyaudiowpatch`** — énumère les périphériques WASAPI marqués comme "
        "loopback et cherche celui qui correspond au **haut-parleur par défaut** "
        "de Windows, par comparaison de noms. À défaut, prend le premier trouvé.",
        "**`soundcard`** — récupère le haut-parleur par défaut en mode loopback.",
        "**« Stereo Mix »** — cherche un périphérique d'entrée dont le nom "
        "contient `stereo mix`, `mixage stéréo` ou `what u hear`. Ce périphérique "
        "est **désactivé par défaut** sur Windows moderne ; c'est un repli "
        "historique.",
    ])
    d.warning(
        "Si les trois échouent : **microphone seul, sans erreur visible**. "
        "L'enregistrement d'une visioconférence se réduit alors à ce que le micro "
        "capte des haut-parleurs, ce qui ne fonctionne pas du tout au casque. "
        "L'information est exposée par une propriété du magnétophone, mais rien ne "
        "l'impose à l'utilisateur."
    )

    d.h3("Le ducking — pourquoi une simple addition ne marche pas")
    d.para(
        "Si l'utilisateur est sur les **haut-parleurs de son portable** et non au "
        "casque, la voix du participant distant est captée **deux fois** : "
        "numériquement, propre, par le loopback ; et acoustiquement, dégradée et "
        "légèrement décalée, par le microphone."
    )
    d.para(
        "Les additionner produit une voix doublée, avec un effet d'écho — "
        "désastreux pour la reconnaissance vocale, et pour la diarisation qui "
        "verrait deux locuteurs là où il n'y en a qu'un."
    )
    d.schema(SCH / "s6_ducking.png",
             "Schéma 6 — Le ducking : décision de gain fenêtre par fenêtre")
    d.para(
        "Le loopback garde toujours un gain de **0,9**. Le gain du microphone est "
        "lissé d'une fenêtre à l'autre pour éviter les clics audibles à chaque "
        "changement de décision."
    )

    d.h3("Deux mixages, pas un seul")
    d.para(
        "C'est le point le plus subtil de la brique : le même signal est mixé "
        "**deux fois, par deux codes différents**."
    )
    d.table(
        ["", "Mixage hors ligne", "Mixage temps réel"],
        [
            ["Quand", "à l'arrêt, en une passe", "en continu, toutes les 50 ms"],
            ["Destination", "`audio.wav` — le fichier conservé", "le pipeline de transcription"],
            ["Découpage", "fenêtres fixes de 120 ms", "un bloc par cycle, ≈ 50 ms, variable"],
            ["Ducking", "gain recalculé par fenêtre", "gain reporté d'un bloc à l'autre"],
        ],
        widths=[1.4, 2.8, 2.8],
    )
    d.para(
        "Les six paramètres de ducking sont **dupliqués** dans les deux fonctions. "
        "Modifier l'un sans l'autre fait diverger le fichier audio du transcript."
    )
    d.warning(
        "**Les deux mixages ne recalent pas les flux de la même façon.** Le "
        "microphone et le loopback ne démarrent pas au même instant — le thread "
        "loopback est lancé avant l'ouverture du flux micro. L'écart est mesuré "
        "sur les horodatages des premiers blocs de chaque flux, puis :\n"
        "— **hors ligne**, le flux en retard est **complété par des zéros** au "
        "début (`recorder.py:291`) ;\n"
        "— **en direct**, le flux en avance est **rogné** de son surplus "
        "(`recorder.py:638`).\n"
        "Les deux opérations alignent bien le micro sur le loopback, mais **ne "
        "conservent pas la même origine des temps** : compléter par des zéros "
        "préserve le début du flux le plus précoce, rogner le supprime. L'origine "
        "de la chronologie temps réel et celle du fichier `audio.wav` diffèrent "
        "donc de l'écart entre les deux premiers blocs.\n"
        "**Conséquence à vérifier** — le fichier de tours de parole sert à "
        "surligner le transcript en synchronisation avec la lecture de l'audio. Un "
        "décalage systématique s'y reporterait. Ce point est **déduit du code, non "
        "mesuré** : à confirmer sur un enregistrement réel avant de le traiter "
        "comme un défaut."
    )

    d.h3("Robustesse du flux micro")
    d.para(
        "Le flux est enveloppé dans une boucle de reconnexion : **5 tentatives**, "
        "délai initial de 2 s avec un facteur 1,5 plafonné à 10 s "
        "(`recorder.py:234`). Cas visé : un casque Bluetooth qui se déconnecte, ou "
        "un changement de périphérique par défaut en cours de réunion. L'attente "
        "entre deux tentatives est **interruptible** — un arrêt pendant la "
        "reconnexion n'attend pas les dix secondes."
    )
    d.warning(
        "Une reconnexion réussie reprend la capture, mais **le temps écoulé "
        "pendant la coupure n'est pas compensé** : les échantillons sont "
        "simplement concaténés. La chronologie de l'enregistrement se contracte "
        "donc du temps de la coupure, ce qui désaligne tout ce qui suit par "
        "rapport aux horaires réels."
    )

    d.h3("Le fichier produit")
    d.para(
        "L'enregistrement est écrit en **WAV 16 kHz, mono, PCM 16 bits signé**, "
        "après limitation d'amplitude. Le backend le déplace ensuite vers "
        "`audio.wav` dans le dossier de la réunion."
    )

    # ── 4.5 ──────────────────────────────────────────────────────────────────
    d.h2("4.5 Le pipeline temps réel")

    d.h3("Chargement des modèles")
    d.para(
        "Le démarrage précharge trois modèles et les **fait tourner à vide une "
        "fois** :"
    )
    d.table(
        ["Modèle", "Préchauffage"],
        [["Extracteur d'empreintes resnet34", "un vecteur de zéros de 1,2 s"],
         ["Silero VAD", "un bloc de 512 échantillons nuls"],
         ["sherpa-onnx", "chargé dans le worker de reconnaissance"]],
        widths=[3.0, 4.0],
    )
    d.para(
        "Le préchauffage n'est pas décoratif : la première inférence déclenche des "
        "allocations et des optimisations de graphe qui prennent 1 à 3 secondes. "
        "Sans lui, les toutes premières fenêtres de parole seraient traitées trop "
        "lentement et la file prendrait du retard dès le départ."
    )
    d.note(
        "**Le VAD est optionnel.** S'il ne charge pas, le pipeline continue avec "
        "un repli sur l'énergie du signal — dégradé mais fonctionnel "
        "(`live_processor.py:149`)."
    )

    d.h3("Le worker de reconnaissance vocale")
    d.para(
        "Même modèle et même configuration que la brique 1, à une exception près : "
        "**deux threads au lieu de quatre**, avec le commentaire « laisse du CPU "
        "aux autres workers »."
    )
    d.para(
        "La différence de fond est ailleurs : le worker **interroge le décodeur "
        "toutes les 2 secondes** pour récupérer les mots déjà produits, au lieu "
        "d'attendre la fin. C'est ce qui alimente le LLM temps réel."
    )
    d.para(
        "À chaque interrogation, le décodeur renvoie **la totalité** des sous-mots "
        "depuis le début ; le worker compare à un compteur pour n'émettre que les "
        "nouveaux. La liste de mots est donc **remplacée** à chaque tour, pas "
        "complétée. À l'arrêt, 0,5 s de silence est injecté pour faire sortir le "
        "dernier token — même mécanisme qu'en différé."
    )

    d.h3("Le worker d'empreintes — la différence majeure avec le mode différé")
    d.para("C'est ici que le temps réel et le différé divergent vraiment.")
    d.para(
        "**En différé (brique 1)** — le VAD découpe d'abord tout l'audio en zones "
        "de parole, puis on pose une fenêtre glissante **à l'intérieur de chaque "
        "zone**."
    )
    d.para(
        "**En temps réel** — on ne peut pas attendre la fin pour segmenter. Le "
        "worker maintient un tampon, y découpe une **grille fixe** de fenêtres de "
        "1,2 s tous les 0,6 s, et pour chacune demande simplement : « y a-t-il de "
        "la parole là-dedans ? »"
    )
    d.schema(SCH / "s7_fenetrage.png",
             "Schéma 7 — Fenêtrage en mode différé et en mode temps réel")
    d.para(
        "Le test de parole découpe la fenêtre en blocs de 512 échantillons — la "
        "taille qu'attend Silero — et renvoie vrai **dès qu'un seul bloc** dépasse "
        "une probabilité de 0,4."
    )
    d.warning(
        "**Conséquence** — une fenêtre temps réel peut contenir 0,2 s de parole et "
        "1 s de silence, et produire quand même une empreinte : de mauvaise "
        "qualité, puisque l'essentiel de la fenêtre ne porte pas de voix. Le mode "
        "différé, lui, ne place ses fenêtres qu'à l'intérieur de zones déjà "
        "identifiées comme parlées.\n"
        "**C'est exactement la source des empreintes bruitées** qui a rendu "
        "nécessaire le gel du clusterer après amorçage (§3.4, étape 5) : sans lui, "
        "ces empreintes ne ressemblaient à aucun centroïde et créaient des "
        "locuteurs fantômes en série."
    )
    d.para(
        "En cas d'exception, le worker pose un indicateur d'erreur — ce qui suffit "
        "à faire échouer la finalisation et donc à déclencher le repli différé."
    )

    d.h3("Le clustering en continu")
    d.para("Chaque empreinte est passée au clusterer à état (§3.4, étape 5) :")
    d.bullets([
        "**avant 1 000 empreintes** — environ 10 minutes de parole : mise en "
        "tampon, aucune étiquette rendue ;",
        "**à la millième** — l'estimation se déclenche sur le lot, les centroïdes "
        "et le seuil automatique sont calculés, les étiquettes attribuées "
        "rétroactivement ;",
        "**ensuite** — chaque empreinte est rattachée au centroïde le plus proche, "
        "sans jamais créer de nouveau locuteur.",
    ])
    d.para(
        "Le déclenchement est journalisé de façon très visible "
        "(`live_processor.py:540`) : *« Bootstrap diarisation déclenché ! NMESC sur "
        "N empreintes → K locuteurs détectés, seuil online calibré à X. »* C'est la "
        "**première trace à chercher** pour diagnostiquer un problème de locuteurs."
    )
    d.warning(
        "**Avant ce déclenchement, aucun mot n'a de vrai locuteur** — la fonction "
        "de résolution renvoie un libellé générique. Ce n'est visible que du LLM "
        "temps réel, qui consomme les tours de parole au fil de l'eau. Le "
        "transcript final, lui, est réétiqueté entièrement à la fin."
    )

    d.h3("La finalisation")
    d.para("Séquence exécutée à l'arrêt de l'enregistrement (`live_processor.py:251`) :")
    d.numbered([
        "arrêt des workers, puis une sentinelle dans chaque file pour débloquer "
        "ceux qui attendent ;",
        "attente de la fin des trois threads, plafonnée à 60 secondes ;",
        "si un indicateur d'erreur est posé → **retour en échec**, rien n'est écrit ;",
        "si le LLM temps réel est actif, il est finalisé **d'abord** (brique 3) ;",
        "clustering final — force l'amorçage si la réunion a duré moins de dix "
        "minutes et que le seuil n'a jamais été atteint ;",
        "construction des segments — fusion des empreintes consécutives d'un même "
        "locuteur, avec une tolérance de 0,1 s ;",
        "alignement mots ↔ locuteurs et regroupement en tours de parole — "
        "**exactement les fonctions de la brique 1** ;",
        "écriture du transcript, des mots et des tours de parole.",
    ])
    d.note(
        "Deux garde-fous notables : un désalignement entre le nombre d'étiquettes "
        "et le nombre d'empreintes est **tronqué** plutôt que de faire échouer le "
        "traitement (`live_processor.py:305`) ; et l'absence totale de segment "
        "renvoie un échec — aucune parole détectée — plutôt que d'écrire un "
        "transcript vide."
    )

    # ── 4.6 ──────────────────────────────────────────────────────────────────
    d.h2("4.6 Ce qui est partagé avec la brique 1 — et ce qui ne l'est pas")
    d.table(
        ["Élément", "Mode différé", "Temps réel", "Partagé ?"],
        [
            ["Modèle de reconnaissance", "Zipformer FR", "identique",
             "**oui** — threads différents"],
            ["Reconstruction des mots", "`_tokens_to_words`", "identique", "**oui**"],
            ["Modèle d'empreinte", "resnet34", "identique", "**oui**"],
            ["Méthode d'extraction", "fichier temporaire par fenêtre", "en mémoire",
             "non — chemins différents"],
            ["Détection de parole", "sur tout le fichier", "par fenêtre",
             "**non — réimplémenté**"],
            ["Fenêtrage", "dans les zones de parole", "grille fixe",
             "**non — logique différente**"],
            ["Clustering", "estimation batch", "clusterer à état",
             "même algorithme, deux implémentations"],
            ["Construction des segments", "`build_segments`", "version locale",
             "**non — réimplémenté**"],
            ["Alignement mots ↔ locuteurs", "midpoint", "identique", "**oui**"],
            ["Format de sortie", "identique", "identique", "**oui**"],
        ],
        widths=[2.0, 1.9, 1.5, 1.6],
    )
    d.warning(
        "**Trois éléments sont réimplémentés** — détection de parole, fenêtrage, "
        "construction des segments — et deux partagent un algorithme via deux "
        "implémentations distinctes. Aucun test ne vérifie qu'ils restent "
        "cohérents. Une correction appliquée d'un seul côté produit deux "
        "transcripts différents pour le même audio, selon qu'il a été enregistré "
        "ou importé."
    )

    # ── 4.7 ──────────────────────────────────────────────────────────────────
    d.h2("4.7 Point de branchement vers le LLM temps réel")
    d.para(
        "Un seul crochet, piloté par un champ du corps de la requête de démarrage. "
        "Il relève de la brique « Génération de compte rendu »."
    )
    d.para(
        "Techniquement optionnel, il est en pratique **toujours activé** : les "
        "trois points d'entrée qui démarrent un enregistrement — le bouton du "
        "panneau principal, la fenêtre de la barre des tâches, et le raccourci "
        "Electron — l'activent tous."
    )
    d.para("Sous cette condition unique, trois objets sont instanciés d'un bloc :")
    d.table(
        ["Objet", "Rôle"],
        [
            ["`TurnBuilder`", "assemble les mots décodés en tours de parole, au fil de l'eau"],
            ["`StreamingTopicChunker`",
             "détecte les ruptures de sujet par embeddings et ferme des blocs thématiques"],
            ["`LiveLLMWorker`",
             "extrait chaque bloc fermé via le serveur de langue local"],
        ],
        widths=[2.2, 4.8],
    )
    d.para(
        "Si l'un d'eux échoue à s'initialiser, les trois sont abandonnés et la "
        "captation continue **sans compte rendu progressif**. La transcription et "
        "la diarisation temps réel, elles, ne dépendent de rien de tout cela et "
        "restent toujours actives : c'est le cœur de cette brique, et il est "
        "volontairement léger."
    )

    # ── 4.8 ──────────────────────────────────────────────────────────────────
    d.h2("4.8 Configuration")
    d.code("""SAMPLE_RATE        = 16 000
EMBED_WIN_S        = 1.2      # fenêtre d'empreinte — identique au mode différé
EMBED_HOP_S        = 0.6      # pas — identique au mode différé
VAD_CHUNK_SAMPLES  = 512      # taille de bloc exigée par Silero
BOOTSTRAP_SIZE     = 1000     # environ 10 min à un pas de 0,6 s

BLOCK_SIZE         = 1 024    # taille de bloc du flux micro""")
    d.para(
        "Paramètres de ducking, dupliqués dans les deux fonctions de mixage : seuil "
        "d'activité du système 0,015 ; gain micro normal 0,8 ; gain micro étouffé "
        "0,08 ; rapport de bascule 1,6 ; gain système 0,9 ; lissage 0,25."
    )
    d.para("Rien n'est exposé dans l'interface : tout ajustement passe par le code.")

    # ── 4.9 ──────────────────────────────────────────────────────────────────
    d.h2("4.9 API et fichiers produits")
    d.table(
        ["Endpoint", "Rôle"],
        [
            ["`POST /api/record/start`",
             "démarre captation et pipeline temps réel. Corps optionnel : réunion "
             "d'agenda, activation du LLM, participants, entreprises, contexte"],
            ["`POST /api/record/stop`", "arrête, assemble, crée le traitement"],
            ["`GET /api/record/status`",
             "resynchronise l'interface — bouton et chronomètre — si l'utilisateur "
             "a changé de page"],
            ["`POST /api/record/cancel`",
             "réinitialise un enregistrement fantôme, backend coincé après un arrêt raté"],
        ],
        widths=[2.4, 4.6],
    )
    d.note(
        "Un seul enregistrement à la fois : le magnétophone et le processeur temps "
        "réel sont des variables **globales** du module backend. Le démarrage "
        "réinitialise automatiquement un état précédent resté coincé plutôt que de "
        "renvoyer une erreur."
    )
    d.table(
        ["Fichier", "Écrit par", "Consommé par"],
        [
            ["`audio.wav`", "l'arrêt — mixage hors ligne",
             "lecteur audio de l'application, et brique 1 en cas de repli"],
            ["`transcript.txt`", "la finalisation",
             "**normalisation → compte rendu**, et signal de court-circuit"],
            ["`turns.json`", "la finalisation",
             "vue Transcript synchronisée à l'audio"],
            ["`words.json`", "la finalisation", "débogage"],
            ["`.origin.recording`", "l'arrêt", "mémorise l'origine pour le repli différé"],
            ["`.calendar_event.json`", "l'arrêt, si réunion liée", "rattachement à l'agenda"],
        ],
        widths=[2.0, 2.0, 3.0],
    )

    # ── 4.10 ─────────────────────────────────────────────────────────────────
    d.h2("4.10 Limites connues")

    d.h3("Pas de loopback = visioconférence inexploitable")
    d.para(
        "Si les trois méthodes de détection échouent, l'enregistrement se poursuit "
        "**sans erreur visible**, en microphone seul. Sur une visioconférence au "
        "casque, les participants distants sont alors totalement absents du "
        "transcript."
    )

    d.h3("Origine des temps entre le fichier audio et le transcript")
    d.para("Voir §4.4. Point **déduit du code, non mesuré** — à confirmer avant d'agir.")

    d.h3("Perte silencieuse d'audio si les files saturent")
    d.para("Voir §4.3. Aucune journalisation quand un chunk est abandonné.")

    d.h3("Coût de la résolution de locuteur")
    d.para(
        "La fonction qui associe un locuteur à un instant fait un **parcours "
        "linéaire complet** de toutes les empreintes, pour chaque mot, à chaque "
        "interrogation de 2 secondes (`live_processor.py:444`). Le commentaire "
        "annonce une « recherche dichotomique grossière » ; le code est une boucle "
        "exhaustive. Le coût croît avec le carré de la durée de la réunion."
    )
    d.para(
        "Comme l'application active toujours le LLM temps réel, cette fonction "
        "tourne à chaque captation — l'atténuation théorique ne joue jamais en "
        "pratique."
    )

    d.h3("Paramètres de ducking dupliqués")
    d.para("Voir §4.4. Six constantes présentes en double.")

    d.h3("Perte de temps sur reconnexion micro")
    d.para("Voir §4.4. Une coupure contracte la chronologie.")

    d.h3("Le premier quart d'heure n'a pas de locuteurs")
    d.para(
        "Tant que l'amorçage n'a pas eu lieu — 1 000 empreintes, environ 10 minutes "
        "de parole effective — les tours de parole transmis au LLM temps réel "
        "portent un libellé générique. Sans effet sur le transcript final, qui est "
        "réétiqueté à la fin, mais le compte rendu progressif est rédigé « à "
        "l'aveugle » sur qui dit quoi pendant toute la première partie de la réunion."
    )

    d.h3("Aucun test automatisé")
    d.para(
        "Comme la brique 1. La vérification passe par une captation réelle et la "
        "lecture des traces."
    )

    # ── 4.11 ─────────────────────────────────────────────────────────────────
    d.h2("4.11 Vérifier une captation")
    d.para("Le pipeline se pilote par l'API, pas en ligne de commande. Backend lancé :")
    d.code("""curl -X POST http://127.0.0.1:8000/api/record/start
curl        http://127.0.0.1:8000/api/record/status
curl -X POST http://127.0.0.1:8000/api/record/stop""")
    d.h3("Les traces à suivre, dans l'ordre")
    d.table(
        ["Trace", "Signification"],
        [
            ["`Loopback pyaudiowpatch (défaut) : [i] <nom>`",
             "le son système est capté"],
            ["`Loopback non disponible — microphone seul`",
             "**visioconférence inexploitable**"],
            ["`Micro ouvert en WASAPI shared mode`",
             "coexistence avec Teams et Zoom assurée"],
            ["`Pipeline live prête en Xs — la file contient N chunks en attente`",
             "workers démarrés ; N mesure le retard initial"],
            ["`N embeddings extraits, clusterer en bootstrap (N/1000)`",
             "progression vers l'amorçage, toutes les 30 s"],
            ["`Bootstrap diarisation déclenché !`",
             "les locuteurs sont identifiés à partir d'ici"],
            ["`N mots décodés, file audio = M chunks en attente`",
             "**si M croît continûment**, la reconnaissance décroche du temps réel"],
            ["`transcript.txt écrit : N mots, N turns, K locuteurs`",
             "mode temps réel réussi"],
            ["`Pas de transcript live — diar batch tournera au lancement`",
             "**repli déclenché**"],
        ],
        widths=[3.4, 3.6],
    )
    d.h3("Points de contrôle")
    d.bullets([
        "Une file qui grandit sans redescendre est **le signal d'alerte "
        "principal** : les workers ne tiennent pas le temps réel et l'audio finira "
        "par être perdu.",
        "Un amorçage qui ne se déclenche jamais sur une réunion de plus de quinze "
        "minutes indique que le VAD rejette presque tout — micro muet, ou mauvais "
        "périphérique.",
        "Un nombre de locuteurs très supérieur au nombre réel de participants "
        "signalerait un gel qui n'a pas joué son rôle ; très inférieur, un amorçage "
        "fait pendant un monologue d'introduction.",
    ])

    # ── 4.12 ─────────────────────────────────────────────────────────────────
    d.h2("4.12 Résumé pour une reprise")
    d.numbered([
        "Deux sources captées en parallèle — microphone en **WASAPI shared**, pour "
        "ne pas voler le périphérique à Teams, et son système par loopback avec "
        "deux niveaux de repli.",
        "Le **ducking** est indispensable dès que l'utilisateur n'est pas au "
        "casque : sans lui, la voix du distant est doublée et la diarisation invente "
        "un locuteur.",
        "Le même signal est mixé **deux fois par deux codes différents** — un pour "
        "le fichier, un pour le temps réel — avec des paramètres dupliqués et un "
        "recalage temporel qui ne préserve pas la même origine des temps (§4.4).",
        "Le magnétophone démarre **avant** que les modèles soient chargés ; les "
        "chunks s'empilent dans des files bornées et les workers les rattrapent.",
        "Le fenêtrage temps réel est une **grille fixe filtrée par le VAD**, là où "
        "le mode différé fenêtre à l'intérieur des zones de parole. C'est la raison "
        "d'être du gel du clusterer de la brique 1.",
        "Le repli est **binaire** : en cas de problème, rien n'est écrit et le "
        "backend relance toute la brique 1.",
        "Trois éléments sont **réimplémentés** par rapport à la brique 1, sans test "
        "pour garantir leur cohérence.",
    ])
    d.note(
        "**Premier chantier si l'on doit fiabiliser** — mesurer l'écart d'origine "
        "des temps entre le fichier audio et les tours de parole (§4.4). C'est le "
        "seul point qui, s'il se confirme, dégrade une fonctionnalité visible par "
        "l'utilisateur : le surlignage du transcript pendant la lecture."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   5. Brique 3 — Génération du compte rendu
# ═════════════════════════════════════════════════════════════════════════════
def section_5_compte_rendu(d: YeleDoc) -> None:
    d.h1("5. Brique 3 — Génération du compte rendu")

    d.kv_table([
        ("Socle et moteur local", "`meeting_minutes_pipeline.py`"),
        ("Variante temps réel", "`audio_capture/live_llm.py`"),
        ("Moteur API", "`mistral_minutes.py`"),
        ("Prétraitement", "`normalize_transcript.py`"),
        ("Rôle", "transformer un transcript attribué par locuteur en compte rendu "
                 "de réunion structuré"),
    ], label_w=4.2)

    d.h2("5.1 Les trois moteurs")
    d.para(
        "Il y a **un seul format de sortie** — `compte_rendu.md` — produit par "
        "trois chemins différents selon le contexte."
    )
    d.schema(SCH / "s8_trois_moteurs.png",
             "Schéma 8 — Les trois moteurs de compte rendu et leur point de convergence")
    d.para(
        "**Le point à retenir : les deux chemins locaux partagent le même code.** "
        "La variante temps réel ne réimplémente ni les prompts, ni les appels au "
        "modèle, ni l'assemblage — elle appelle les mêmes fonctions que le moteur "
        "différé. Seul le **découpage en blocs** est réécrit, parce qu'il doit "
        "fonctionner en flux (§5.5)."
    )
    d.para(
        "Le moteur Mistral, lui, est complètement indépendant : aucune ligne "
        "partagée, aucun découpage, un seul appel API (§5.6)."
    )
    d.h3("Qui déclenche quoi")
    d.table(
        ["Contexte", "Moteur", "Quand le compte rendu est prêt"],
        [
            ["Enregistrement dans l'application", "**live local**",
             "**au clic sur Stop** — le traitement est marqué terminé, "
             "l'utilisateur n'a rien à lancer"],
            ["Audio importé, ou repli d'enregistrement", "**batch local** (défaut)",
             "après plusieurs dizaines de minutes"],
            ["Idem, si l'utilisateur choisit Mistral", "**batch Mistral**",
             "le temps d'un appel API"],
        ],
        widths=[2.4, 1.6, 3.0],
    )
    d.para(
        "Le choix entre local et Mistral vient d'un sélecteur du panneau de "
        "traitement, dont la valeur par défaut est **local**. Il transite par le "
        "corps de la requête de lancement, que le backend traduit en nom de "
        "sous-commande (`backend/main.py:673`)."
    )

    d.h2("5.2 La chaîne après réunion")
    d.code("""transcript.txt                       (brique 1 ou 2)
   │
   ├─► backend.exe normalize  ─────► transcript.normalized.txt
   │
   └─► backend.exe minutes | mistral-minutes  ─────► compte_rendu.md
          arguments     : --transcript --output [--participants] [--entreprises]
          environnement : MEETING_CONTEXT / MEETING_PARTICIPANTS / MEETING_ENTREPRISES
                          MISTRAL_API_KEY  (mode mistral uniquement)""")
    d.note(
        "**Participants et entreprises sont transmis deux fois** — en argument "
        "**et** en variable d'environnement. Ce n'est pas une redondance : "
        "l'argument est lu par le point d'entrée du moteur et passé à la "
        "résolution des locuteurs ; la variable d'environnement est lue bien plus "
        "bas, par les fonctions qui construisent les prompts et qui n'ont pas "
        "accès aux arguments de la ligne de commande. Le **contexte libre**, lui, "
        "ne passe que par l'environnement."
    )
    d.para(
        "La clé Mistral est injectée depuis les paramètres de l'application "
        "uniquement quand le mode correspondant est retenu. Le backend vérifie sa "
        "présence **avant** de lancer le sous-processus et fait échouer le "
        "traitement avec un message explicite (`main.py:679`)."
    )

    d.h3("La normalisation du transcript")
    d.para("Une seule chose, mais elle compte : **une ligne = une phrase**.")
    d.table(
        ["Entrée", "Sortie"],
        [["`[00:03.20 - 00:11.45]  SPEAKER_00 : bonjour à tous. "
          "On commence par le point deux.`",
          "`SPEAKER_00: bonjour à tous.`\n`SPEAKER_00: On commence par le point deux.`"]],
        widths=[3.5, 3.5],
    )
    d.bullets([
        "**Les horodatages sont supprimés** — le commentaire du code l'assume : "
        "« ignorés pour économiser des tokens ». Le compte rendu ne contient donc "
        "aucun horaire, et le modèle n'a aucune notion de durée.",
        "Le découpage en phrases protège les abréviations françaises courantes "
        "(`M.`, `Mme.`, `cf.`, `etc.`, `env.`…) pour ne pas couper dessus.",
        "Un **découpage dur à 300 caractères** s'applique aux phrases trop "
        "longues — cas fréquent en reconnaissance vocale, où une absence de "
        "ponctuation produit des « phrases » de plusieurs lignes.",
    ])
    d.para(
        "Cette granularité par phrase est ce qui rend le découpage sémantique "
        "exploitable : les fenêtres portent sur 3 phrases, pas sur 3 tours de "
        "parole de longueur arbitraire."
    )

    # ── 5.3 ──────────────────────────────────────────────────────────────────
    d.h2("5.3 Le socle partagé")
    d.para(
        "Le fichier `meeting_minutes_pipeline.py` joue deux rôles : **moteur local "
        "après réunion**, et **bibliothèque** dont la variante temps réel consomme "
        "presque tout."
    )

    d.h3("Configuration")
    d.code("""# Découpage sémantique
embedding_model          = "all-MiniLM-L6-v2"
boundary_window_size     = 3        # phrases par fenêtre
boundary_smoothing_sigma = 2.0      # lissage de la courbe de similarité
boundary_percentile      = 5.0      # seuil : les 5 % de similarités les plus basses
boundary_min_distance    = 10       # écart minimal entre deux frontières
max_chunk_chars          = 15000    # au-delà → re-découpage récursif

# Modèle de langue local
llm_model_path      = Ministral 3B Instruct — quantifié Q4_K_M
llm_n_ctx           = 16384         # contexte total, réparti entre les slots
llm_n_threads       = 6
llm_n_gpu_layers    = 0             # processeur uniquement
llm_temperature     = 0.2
llm_repeat_penalty  = 1.1
llm_kv_cache_type   = "q8_0"        # cache d'attention quantifié
llm_server_port     = 8765
llm_server_startup_timeout = 86400  # 24 h — autant dire aucune limite
llm_section_timeout        = 86400

plan_attack_mode = "perchunk\"""")
    d.note(
        "Les deux temporisations à 86 400 secondes ne sont pas un oubli : sur un "
        "portable en processeur seul, un bloc peut prendre plusieurs minutes, et "
        "une limite mal calibrée ferait échouer un traitement qui aurait fini par "
        "aboutir. Le parti pris est de **ne jamais abandonner**."
    )

    d.h3("Le découpage sémantique")
    d.para(
        "C'est ce qui décide du plan du compte rendu : chaque bloc deviendra un "
        "« sujet abordé »."
    )
    d.schema(SCH / "s9_decoupage_semantique.png",
             "Schéma 9 — Du transcript aux blocs thématiques par chute de similarité")
    d.para(
        "L'intuition : deux passages consécutifs qui parlent du même sujet ont des "
        "vecteurs proches. Une **chute** de similarité signale un changement de "
        "sujet. Le lissage évite de réagir aux micro-variations, le seuil au "
        "percentile s'adapte automatiquement à chaque réunion, et la distance "
        "minimale empêche de hacher la réunion en micro-sections."
    )
    d.para(
        "Le garde-fou des 15 000 caractères est structurel : au-delà, un bloc ne "
        "tient plus dans la fenêtre de contexte du modèle. Le re-découpage est "
        "**récursif** — on ré-analyse le bloc trop gros, on coupe à sa vallée la "
        "plus profonde, et on recommence sur chaque moitié tant que c'est nécessaire."
    )

    d.h3("Le serveur de modèle local")
    d.para(
        "Le démarrage lance `llama-server.exe` et attend que sa sonde de santé "
        "réponde. Options retenues :"
    )
    d.code("""--ctx-size 16384      --parallel N        --flash-attn on
--cache-ram 0         --cache-type-k q8_0 --cache-type-v q8_0
--batch-size 4096     --ubatch-size 1024  --threads 6
--log-disable""")
    d.para(
        "Le contexte total est **constant** quel que soit le nombre de slots : le "
        "serveur le découpe en parts égales. Augmenter le parallélisme ne coûte "
        "donc pas de mémoire, tant que chaque bloc tient dans sa part."
    )
    d.warning(
        "**L'option de cache mémoire est explicitement désactivée** pour corriger "
        "une fuite. La valeur par défaut de certaines variantes du serveur est de "
        "8 Gio de cache de prompt en mémoire hôte, ce qui **saturait la mémoire "
        "après une dizaine de blocs et provoquait un arrêt silencieux du processus "
        "par Windows**. Le cache de préfixe par slot, lui, reste actif — c'est "
        "celui qui fait le travail utile, puisque les trois appels d'un même bloc "
        "partagent leur préfixe."
    )
    d.warning(
        "**Une optimisation de décodage a été retirée après mesure**, pas par "
        "oubli : régression de 5 % sur l'appel de résumé — sortie courte et "
        "reformulée, taux d'acceptation trop bas pour rentabiliser la passe de "
        "vérification — et effet neutre sur les deux autres appels."
    )

    d.h3("Les prompts et les entités figées")
    d.para(
        "Le prompt système est construit dynamiquement. Sa colonne vertébrale est "
        "un ensemble de règles de non-invention :"
    )
    d.note(
        "*Ne mentionne QUE ce qui est EXPLICITEMENT dit — n'invente JAMAIS "
        "d'informations, décisions, actions, chiffres, dates, échéances — ne "
        "développe JAMAIS un sigle.*"
    )
    d.para(
        "Par-dessus, si l'utilisateur a saisi des participants ou des entreprises, "
        "un bloc **entités figées** est ajouté :"
    )
    d.note(
        "*Les listes ci-dessous sont la vérité. Le transcript contient des erreurs "
        "phonétiques sur les noms propres : corrige-les silencieusement vers la "
        "forme EXACTE de la liste. Si un nom ne correspond à AUCUN élément de la "
        "liste, ne le cite pas.*"
    )
    d.para(
        "C'est la réponse au problème central du couple reconnaissance vocale + "
        "modèle de langue : la transcription écrit les noms propres "
        "phonétiquement, et un modèle à qui l'on ne dit rien reproduit l'erreur, "
        "voire l'aggrave en la « corrigeant » vers un nom plausible mais faux."
    )
    d.warning(
        "Ce bloc est répété **deux fois** : dans le prompt système, et à nouveau à "
        "la **fin du prompt utilisateur**. C'est un ancrage délibéré aux deux "
        "extrémités du contexte — les modèles de petite taille perdent "
        "l'information placée au milieu."
    )

    d.h3("Les appels au modèle et le JSON contraint")
    d.para(
        "Tous les appels passent par une fonction unique, en HTTP sur l'API "
        "compatible du serveur local : température 0,2, pénalité de répétition "
        "1,1, plus une liste de séquences d'arrêt."
    )
    d.para(
        "**Le point important** : quand un schéma JSON est fourni, il est passé en "
        "mode strict. Le décodage est alors **contraint au niveau des tokens** — "
        "le modèle ne *peut pas* produire du JSON invalide."
    )
    d.para(
        "C'est ce qui rend le pipeline fiable avec un modèle de 3 milliards de "
        "paramètres : on ne demande pas au modèle de bien se tenir, on l'en "
        "empêche structurellement. Le plafond de 2 items par bloc dans le plan "
        "d'attaque, par exemple, est imposé par la grammaire du schéma, pas par "
        "une instruction en français."
    )

    d.h3("Du bloc au compte rendu")
    d.schema(SCH / "s10_chunk_vers_cr.png",
             "Schéma 10 — Trois appels par bloc, puis un assemblage entièrement déterministe")
    d.para("Pour **chaque bloc**, trois appels dans le mode par défaut :")
    d.table(
        ["#", "Appel", "Produit"],
        [["1", "RÉSUMÉ", "titre, contexte, points-clés"],
         ["2", "EXTRACTION", "décisions actées"],
         ["3", "PLAN", "0 à 2 items d'action"]],
        widths=[0.6, 2.0, 4.4],
    )
    d.para("Le troisième appel distingue deux natures d'items :")
    d.bullets([
        "**engagement** — quelqu'un s'est explicitement engagé. Responsable et "
        "échéance sont repris tels quels, avec un filet : un responsable de la "
        "forme `SPEAKER_07` est remplacé par un tiret, le modèle ayant recopié une "
        "étiquette de diarisation au lieu d'un nom ;",
        "**suggestion** — recommandation déduite. Responsable et échéance sont "
        "**forcés** au tiret, pour qu'on ne puisse jamais présenter une "
        "recommandation comme un engagement pris.",
    ])

    d.h3("Résolution des locuteurs")
    d.para(
        "Un appel dédié envoie les **80 premières lignes** du transcript au modèle "
        "avec la liste des participants, et lui demande d'associer chaque "
        "étiquette `SPEAKER_XX` à un nom et une entreprise (`meeting_minutes_"
        "pipeline.py:1185`)."
    )
    d.para(
        "Le pari : une réunion professionnelle commence par un tour de table. "
        "C'est ce qui permet de remplacer les étiquettes anonymes par de vrais noms "
        "dans tout le compte rendu. N'est exécuté **que si** l'utilisateur a saisi "
        "des participants."
    )

    d.h3("L'assemblage — entièrement déterministe")
    d.para(
        "La fonction d'assemblage ne fait **aucun appel au modèle**. Elle compose "
        "le markdown à partir des structures JSON déjà produites :"
    )
    d.code("""# Compte rendu de réunion
## 1. Participants        <- seulement si les locuteurs ont été résolus
## 2. Résumé              <- 1 appel LLM
## 3. Sujets abordés      <- une sous-section par bloc
## 4. Décisions           <- tableau, agrégation de tous les blocs
## 5. Plan d'attaque      <- tableau, engagements puis suggestions""")
    d.para(
        "La numérotation est gérée par un compteur qui n'avance que sur les "
        "sections réellement émises : sans participants, « Résumé » devient la "
        "section 1 et non la 2."
    )
    d.warning(
        "**La structure du document ne dépend jamais du modèle de langue.** Le "
        "modèle remplit des cases ; le squelette, les tableaux, la numérotation et "
        "l'échappement des barres verticales sont du code. Un modèle de 3 "
        "milliards de paramètres ne peut donc pas casser la mise en forme. C'est la "
        "décision d'architecture la plus structurante de cette brique."
    )

    # ── 5.4 ──────────────────────────────────────────────────────────────────
    d.h2("5.4 Le moteur local après réunion")
    d.para("Huit étapes, chronométrées individuellement.")
    d.table(
        ["#", "Étape", "Appels au modèle"],
        [["0", "chargement du transcript", "—"],
         ["0b", "résolution des locuteurs (si participants saisis)", "1"],
         ["1", "fenêtres glissantes", "—"],
         ["2", "vecteurs MiniLM", "—"],
         ["3", "détection des frontières", "—"],
         ["4", "construction des blocs", "—"],
         ["5", "**génération des sections**", "**3 × nombre de blocs**"],
         ["6", "résumé exécutif", "1"],
         ["7", "plan d'attaque", "0 en mode par défaut"],
         ["8", "assemblage markdown", "—"]],
        widths=[0.5, 4.5, 2.0],
    )
    d.para(
        "Total en configuration par défaut : **3 × nombre de blocs + 1**, plus 1 "
        "si les locuteurs sont résolus. Une réunion découpée en 8 blocs demande "
        "donc environ **26 appels** au modèle local."
    )
    d.para(
        "**Ces appels sont séquentiels.** L'option de parallélisation vaut 1 par "
        "défaut et le backend ne la passe jamais. Justification mesurée et "
        "documentée : sur processeur, l'inférence est limitée par la bande passante "
        "mémoire, pas par le nombre de cœurs, et le banc d'essai cité dans l'aide "
        "de l'option ne montre aucun gain au-delà d'un slot."
    )
    d.warning(
        "**Un cache de sections existe et peut surprendre.** L'étape 5 écrit un "
        "fichier de sections à côté de la sortie, et **le relit s'il existe** "
        "(`meeting_minutes_pipeline.py:1542`). Relancer un traitement sur le même "
        "dossier réutilise donc les sections précédentes sans rappeler le modèle — "
        "pratique pour itérer sur l'assemblage, **piégeux si l'on croit tester une "
        "modification de prompt**. Le paramètre qui le désactive existe mais n'est "
        "pas exposé par le backend."
    )
    d.warning(
        "**Le serveur de modèle est démarré deux fois** quand la résolution des "
        "locuteurs tourne : une première fois avec un seul slot pour cette "
        "résolution, puis de nouveau avec le nombre de slots calculé — et le "
        "démarrage commence par tuer ce qui écoute sur le port. On paie donc deux "
        "chargements du modèle."
    )
    d.para(
        "Deux fichiers de débogage sont écrits à côté du compte rendu : un "
        "récapitulatif d'assemblage (nombre de sections, de décisions, "
        "d'engagements) et un fichier de métriques (durées par étape, mémoire, "
        "nombre d'appels)."
    )

    # ── 5.5 ──────────────────────────────────────────────────────────────────
    d.h2("5.5 Le moteur temps réel")
    d.para(
        "Même destination, contrainte inverse : on ne dispose jamais de la "
        "totalité du texte."
    )
    d.code("""mots décodés par la reconnaissance vocale (brique 2, toutes les 2 s)
   │
   ├─ TurnBuilder                 assemble les mots en tours de parole
   ├─ découpage en phrases        même granularité que la normalisation différée
   │
   ├─ StreamingTopicChunker       détection de frontières EN FLUX
   │     └─ à chaque bloc fermé → envoi au worker
   │
   └─ LiveLLMWorker               pool de slots sur le serveur local
         └─ generate_section_json(bloc)   <- LA MÊME fonction que le différé

au clic sur Stop → finalisation
   résumé exécutif + plan d'attaque + assemblage   <- les mêmes fonctions
   → compte_rendu.md""")

    d.h3("Le chunker en flux — la vraie difficulté")
    d.para(
        "Le mode différé calcule un seuil **global** — le percentile de toutes les "
        "similarités — ce qui suppose de connaître toute la réunion. En direct, "
        "c'est impossible : il faut décider maintenant, sans savoir ce qui vient."
    )
    d.para("Le seuil global est donc remplacé par trois mécanismes :")
    d.table(
        ["Paramètre", "Valeur", "Rôle"],
        [
            ["`window_size`", "3", "identique au mode différé"],
            ["`smoothing_sigma`", "2,0", "identique, mais lissage **causal**"],
            ["`rolling_n`", "20", "seuil calculé sur les 20 dernières similarités seulement"],
            ["`k_sigma`", "2,0", "seuil = moyenne − 2 × écart-type de cette fenêtre"],
            ["`confirm_delay`", "5", "un creux doit tenir 5 fenêtres avant d'être validé"],
            ["`min_chunk_turns`", "10", "pas de bloc de moins de 10 phrases"],
            ["`max_chunk_chars`", "15 000", "identique au mode différé"],
        ],
        widths=[2.0, 1.0, 4.0],
    )
    d.code("""recent    = similarités_lissées[-20:]
seuil     = recent.moyenne() - 2.0 * recent.écart_type()
si dernière_similarité < seuil  →  candidat de frontière""")
    d.para(
        "Le délai de confirmation est la contrepartie de l'irréversibilité : **un "
        "bloc émis est parti au modèle, on ne peut plus revenir dessus**. Le mode "
        "différé peut réviser ses frontières autant qu'il veut avant de découper ; "
        "le temps réel doit attendre d'être sûr."
    )
    d.warning(
        "**Aucune frontière ne peut être détectée avant 20 similarités "
        "accumulées** — la détection sort immédiatement en deçà. À 3 phrases par "
        "fenêtre, cela représente les 22 premières phrases de la réunion. Combiné "
        "au minimum de 10 phrases par bloc et au délai de confirmation de 5 "
        "fenêtres, le premier bloc ne peut donc pas être fermé tôt : le modèle "
        "reste inactif pendant le début de la réunion."
    )
    d.para(
        "Le garde-fou de taille traite le cas du sujet unique qui s'éternise : "
        "plutôt que d'attendre la fin — ce qui laisserait le modèle inactif "
        "pendant toute la réunion puis lui donnerait tout d'un coup — on force la "
        "fermeture. Et on la force **à la vallée sémantique la plus profonde parmi "
        "les candidats en attente**, pas au tour de parole courant : c'est "
        "l'équivalent en flux du re-découpage récursif du mode différé."
    )

    d.h3("Le worker")
    d.para(
        "Les blocs fermés sont consommés depuis une file et soumis à un pool de "
        "threads, dont la taille vaut **1** par défaut."
    )
    d.note(
        "Le choix séquentiel est documenté et mesuré : sur processeur, l'inférence "
        "est limitée par la bande passante mémoire, pas par le nombre de cœurs. Le "
        "commentaire cite un banc d'essai montrant **environ 0 % de gain** entre "
        "deux slots et le séquentiel. Un récapitulatif de parallélisme est "
        "journalisé à la fin pour vérifier ce qui s'est réellement passé."
    )
    d.para(
        "Les sections peuvent se terminer dans le désordre ; la finalisation les "
        "retrie par instant de début avant le résumé et le plan d'attaque, qui "
        "attendent un ordre chronologique. Le serveur de modèle est arrêté dans un "
        "bloc de nettoyage, quelle que soit l'issue."
    )
    d.warning(
        "**Le compte rendu produit en temps réel n'a jamais de section "
        "« Participants ».** La finalisation appelle l'assemblage sans mapping de "
        "locuteurs (`live_llm.py:684`), alors que le mode différé le résout dès que "
        "l'utilisateur a saisi des participants. Les sujets peuvent en outre citer "
        "une étiquette générique pour tout ce qui a été traité avant l'amorçage de "
        "la diarisation — soit les dix premières minutes environ (§4.5)."
    )

    # ── 5.6 ──────────────────────────────────────────────────────────────────
    d.h2("5.6 Le moteur Mistral")
    d.para(
        "L'exact opposé du moteur local : **un seul appel API, tout le transcript "
        "d'un coup.**"
    )
    d.kv_table([
        ("Modèle", "`mistral-large-latest` — surchargeable par variable d'environnement"),
        ("Température", "0,2"),
        ("Temporisation", "300 s"),
        ("Découpage", "**aucun**"),
        ("Dépendances", "bibliothèque standard uniquement — aucun import du socle"),
    ], label_w=3.6)
    d.para(
        "Le plan du document n'est pas assemblé par du code : il est **dicté au "
        "modèle** dans le prompt utilisateur, section par section, avec les nombres "
        "attendus — 3 à 8 sujets, 2 à 6 points par sujet, 4 à 10 items de plan "
        "dont 2 à 4 recommandations."
    )
    d.para(
        "Les règles de non-invention et le bloc d'entités figées sont repris, dans "
        "une formulation plus développée que la version locale : le budget de "
        "contexte n'est pas un problème ici."
    )
    d.note(
        "Une particularité qui a demandé un correctif : la réponse est débarrassée "
        "des délimiteurs de bloc de code que le modèle place fréquemment autour de "
        "son markdown pour « l'isoler ». Sans cela, tout le compte rendu arrivait "
        "dans l'éditeur comme un unique bloc en chasse fixe."
    )

    # ── 5.7 ──────────────────────────────────────────────────────────────────
    d.h2("5.7 Les trois moteurs en regard")
    d.table(
        ["", "Live local", "Batch local", "Batch Mistral"],
        [
            ["Modèle", "Ministral 3B Q4", "Ministral 3B Q4", "mistral-large-latest"],
            ["Exécution", "processeur local", "processeur local", "API distante"],
            ["Découpage", "flux causal", "global, percentile", "**aucun**"],
            ["Vecteurs MiniLM", "oui", "oui", "—"],
            ["Appels au modèle", "3 / bloc + 1", "3 / bloc + 1 (+1)", "**1**"],
            ["Structure du document", "code déterministe", "code déterministe",
             "**dictée au modèle**"],
            ["JSON contraint", "oui", "oui", "non"],
            ["Section Participants", "**jamais**", "si participants saisis", "via le prompt"],
            ["Connexion requise", "non", "non", "**oui**"],
            ["Latence perçue", "quasi nulle", "dizaines de minutes", "un appel"],
        ],
        widths=[1.8, 1.7, 1.8, 1.7],
    )
    d.para(
        "Les deux colonnes locales partagent tout sauf la première ligne de "
        "traitement. La colonne Mistral ne partage rien."
    )

    # ── 5.8 ──────────────────────────────────────────────────────────────────
    d.h2("5.8 Fichiers produits")
    d.table(
        ["Fichier", "Écrit par", "Rôle"],
        [
            ["`compte_rendu.md`", "les trois moteurs", "**le livrable**"],
            ["`transcript.normalized.txt`", "la normalisation", "entrée des moteurs différés"],
            ["`compte_rendu.sections.json`", "batch local", "**cache** des sections (§5.4)"],
            ["`compte_rendu.assembly.json`", "batch local", "débogage — comptes de sections"],
            ["`compte_rendu.metrics.json`", "batch local", "durées par étape, mémoire, appels"],
        ],
        widths=[2.6, 1.8, 2.6],
    )

    # ── 5.9 ──────────────────────────────────────────────────────────────────
    d.h2("5.9 Limites connues")

    d.h3("Le compte rendu n'a aucune notion du temps")
    d.para(
        "La normalisation supprime les horodatages pour économiser des tokens. "
        "Aucun moteur ne peut donc situer un sujet dans la réunion, ni indiquer une "
        "durée. Les instants circulent bien dans les structures internes — ils "
        "servent à trier les sections — mais ne parviennent jamais au modèle."
    )

    d.h3("Le cache de sections est invisible")
    d.para(
        "Voir §5.4. Une modification de prompt sans suppression du fichier de "
        "cache n'a **aucun effet, silencieusement**. C'est le premier piège pour "
        "qui reprend cette brique."
    )

    d.h3("Double démarrage du serveur de modèle")
    d.para("Voir §5.4. Deux chargements du modèle quand les locuteurs sont résolus.")

    d.h3("Le temps réel ne nomme pas les participants")
    d.para("Voir §5.5.")

    d.h3("Aucune temporisation effective en local")
    d.para(
        "Un bloc qui part en boucle bloque le traitement une journée entière. Le "
        "choix est assumé (§5.3), mais rien ne détecte ni ne signale une génération "
        "anormalement longue."
    )

    d.h3("Le moteur Mistral n'a aucun garde-fou structurel")
    d.para(
        "Pas de JSON contraint, pas d'assemblage déterministe : si le modèle "
        "s'écarte du plan demandé, le markdown produit s'en écarte aussi. Le seul "
        "filet est le retrait du bloc de code englobant. En contrepartie, le modèle "
        "est bien plus capable — le compromis est cohérent."
    )

    d.h3("Aucun test automatisé")
    d.para("Comme les briques 1 et 2.")

    # ── 5.10 ─────────────────────────────────────────────────────────────────
    d.h2("5.10 Vérifier le fonctionnement")
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"

# normalisation seule
python -m backend.run_app normalize transcript.txt transcript.normalized.txt

# moteur local (défaut)
$env:MEETING_PARTICIPANTS = "Marie Dupont, Jean Martin"
$env:MEETING_ENTREPRISES  = "Yele Consulting, RTE"
python -m backend.run_app minutes --transcript transcript.normalized.txt `
                                  --output compte_rendu.md

# moteur Mistral
$env:MISTRAL_API_KEY = "..."
python -m backend.run_app mistral-minutes --transcript transcript.normalized.txt `
                                          --output compte_rendu_mistral.md""")
    d.h3("Points de contrôle")
    d.bullets([
        "`N chunks thématiques créés` — moins de 3 blocs sur une réunion d'une "
        "heure signale un découpage qui n'a pas fonctionné : transcript trop court, "
        "ou similarités trop uniformes. Plus de 15, un hachage excessif.",
        "Chaque bloc doit journaliser **résumé**, **extraction** et **plan** en "
        "mode par défaut. Deux seulement signifie que l'autre mode de plan est "
        "actif.",
        "`Plan d'attaque (perchunk) : N items assemblés … sans appel LLM final` — "
        "confirme le chemin déterministe.",
        "**Avant de tester une modification de prompt, supprimer le fichier de "
        "cache des sections** (§5.9).",
        "Côté temps réel, chercher la fermeture d'un bloc par le chunker puis son "
        "traitement par le worker. Un chunker qui ne ferme jamais rien produit un "
        "compte rendu vide au clic sur Stop.",
    ])

    # ── 5.11 ─────────────────────────────────────────────────────────────────
    d.h2("5.11 Résumé pour une reprise")
    d.numbered([
        "Trois chemins, un seul livrable : **live local**, **batch local**, "
        "**batch Mistral**.",
        "Les deux chemins locaux **partagent tout** sauf le découpage — mêmes "
        "prompts, mêmes appels, même assemblage. Une modification de prompt affecte "
        "les deux.",
        "**La structure du document est du code, pas du modèle.** Le modèle remplit "
        "des cases via des schémas JSON contraints au niveau des tokens ; les "
        "titres, tableaux et numérotations sont assemblés déterministiquement. "
        "C'est ce qui rend un modèle de 3 milliards de paramètres utilisable.",
        "Les **entités figées** — participants, entreprises — sont ancrées deux "
        "fois dans le prompt pour corriger les erreurs phonétiques de la "
        "reconnaissance vocale sur les noms propres.",
        "Le **découpage sémantique** décide du plan : fenêtres de 3 phrases, chute "
        "de similarité, seuil au percentile en différé, seuil glissant avec "
        "confirmation différée en temps réel.",
        "Le moteur Mistral est **structurellement différent** : un appel, aucun "
        "garde-fou de code, le plan dicté dans le prompt.",
        "Les horodatages sont **supprimés** avant le modèle — le compte rendu n'a "
        "aucune notion de temps.",
    ])
    d.note(
        "**Premier piège pour qui reprend** — le cache de sections (§5.9). Il fait "
        "croire qu'une modification de prompt n'a pas d'effet."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   6. Brique 4 — Backend API
# ═════════════════════════════════════════════════════════════════════════════
def section_6_backend(d: YeleDoc) -> None:
    d.h1("6. Brique 4 — Backend API")

    d.kv_table([
        ("Fichiers", "`backend/main.py` (~1 860 l., 28 endpoints), "
                     "`graph_calendar.py`, `job_logger.py`, `resource_monitor.py`, "
                     "`run_app.py`"),
        ("Adresse", "`127.0.0.1:8000` — jamais exposé sur le réseau"),
        ("Rôle", "orchestrer les briques 1 à 3, exposer l'état à l'interface, "
                 "gérer la persistance des réunions"),
    ], label_w=3.0)

    d.h2("6.1 Ce que fait le backend — et ce qu'il ne fait pas")
    d.para(
        "Le backend est un serveur FastAPI local, lancé par Electron au démarrage "
        "de l'application. **Il ne calcule presque rien lui-même** : il orchestre "
        "des sous-processus (briques 1 et 3), héberge la captation (brique 2, qui "
        "tourne dans son propre processus), et expose l'état à l'interface."
    )
    d.warning(
        "**Il n'y a aucune base de données.** C'est le choix d'architecture le "
        "plus structurant de cette brique, et tout le reste en découle."
    )

    d.h2("6.2 Le système de fichiers tient lieu de base de données")
    d.schema(SCH / "s11_stockage.png",
             "Schéma 11 — L'organisation du stockage : dossiers de réunion, "
             "catégories et réglages")
    d.para(
        "Le chemin du dossier Documents est résolu par une **API Windows** et non "
        "par une construction de chemin naïve (`main.py:87`) — c'est ce qui permet "
        "de suivre le dossier réel quand la redirection de dossiers OneDrive est "
        "active, ce qui est le cas dans la plupart des environnements d'entreprise."
    )
    d.h3("Réunion ou catégorie ?")
    d.para(
        "Il n'y a **pas de métadonnée** : la distinction est déduite du contenu "
        "(`main.py:267`). Un dossier qui contient un fichier audio ou un transcript "
        "brut est une **réunion** ; sinon, c'est une **catégorie**."
    )
    d.para(
        "Les « dossiers » de l'interface sont donc de vrais sous-dossiers, sur **un "
        "seul niveau** de profondeur. L'utilisateur peut les créer et les "
        "réorganiser directement dans l'Explorateur : l'application les retrouvera "
        "au prochain démarrage."
    )
    d.note(
        "**Rien de sensible ne va dans Documents.** C'est délibéré : ce dossier est "
        "synchronisé par OneDrive. Y placer un jeton de rafraîchissement Microsoft "
        "reviendrait à le répliquer dans le cloud et sur tous les postes de "
        "l'utilisateur."
    )

    d.h2("6.3 Le modèle de traitement")
    d.para("Un traitement est un objet **purement en mémoire** (`main.py:195`).")
    d.table(
        ["Champ", "Sens"],
        [
            ["`status`", "`draft` → `pending` → `queued` → `running` → `done` / `error`"],
            ["`step`", "libellé affiché dans l'interface"],
            ["`source`", "`audio` ou `transcript` — import Teams"],
            ["`origin`", "`recording` ou `upload` — pilote le mode de clustering (brique 1)"],
            ["`out_dir`", "le dossier de la réunion — **la seule donnée réellement persistante**"],
            ["`context`", "participants, entreprises, contexte, choix du moteur"],
            ["`calendar`", "réunion d'agenda liée, ou rien"],
            ["`folder`", "catégorie, ou racine"],
            ["`created_at`", "date de création du dossier — stable même après renommage"],
        ],
        widths=[1.8, 5.2],
    )
    d.schema(SCH / "s12_cycle_job.png",
             "Schéma 12 — États d'un traitement, rechargement au démarrage et idempotence")
    d.warning(
        "**Les identifiants de traitement ne survivent pas à un redémarrage.** Ils "
        "sont générés aléatoirement au moment du rechargement (`main.py:299`). Un "
        "identifiant n'est valable que pour la session en cours : il ne doit jamais "
        "être stocké côté interface ni figurer dans un lien partagé."
    )

    d.h2("6.4 Le rechargement au démarrage")
    d.para(
        "La reconstruction repart des seuls fichiers présents : l'existence d'un "
        "compte rendu suffit à marquer le traitement comme terminé, le marqueur "
        "d'origine restitue le mode de clustering, et le marqueur d'agenda "
        "restitue le lien à la réunion."
    )
    d.h3("Deux points de conception")
    d.para(
        "**Le rechargement est lancé au niveau du module, pas dans le gestionnaire "
        "de démarrage du serveur.** Le commentaire l'explique : le balayage lit "
        "**intégralement** chaque compte rendu et chaque transcript, donc son coût "
        "croît avec l'historique. En le déportant dans un thread de fond, le "
        "serveur peut lier le port immédiatement et répondre à la sonde de santé "
        "tout de suite — Electron n'attend pas. Les réunions apparaissent "
        "progressivement, l'interface interrogeant la liste en continu."
    )
    d.para(
        "**Un nettoyage rétroactif a lieu au passage.** Les réunions terminées "
        "voient leurs fichiers intermédiaires purgés : les anciens dossiers "
        "encombrés sont épurés au premier démarrage suivant une mise à jour."
    )
    d.warning(
        "**Tout l'historique reste en mémoire.** Le markdown et le transcript "
        "**complets** de chaque réunion sont conservés dans l'objet, et la liste "
        "des traitements les renvoie tous à chaque appel — que l'interface les "
        "affiche ou non. L'empreinte mémoire et la taille des réponses croissent "
        "linéairement avec le nombre de réunions archivées (§6.11)."
    )

    d.h2("6.5 L'orchestration du pipeline")
    d.schema(SCH / "s13_orchestration.png",
             "Schéma 13 — Enchaînement des sous-processus sous verrou global")
    d.h3("Un traitement à la fois")
    d.para(
        "Le verrou est **global au processus** : deux réunions ne peuvent jamais "
        "être traitées simultanément. C'est cohérent avec la nature du travail — un "
        "serveur de modèle qui sature déjà le processeur, et la collision de "
        "fichiers temporaires signalée en §3.4."
    )
    d.para(
        "Pendant le traitement, la mise en veille du système est **bloquée** : sans "
        "cela, un portable s'endormirait au milieu d'un traitement de vingt minutes."
    )
    d.h3("Pourquoi des sous-processus")
    d.table(
        ["Mode", "Commande"],
        [["Figé (application livrée)",
          "`backend.exe <sous-commande> …` — le même exécutable se rappelle lui-même"],
         ["Développement", "`python -m backend.run_app <sous-commande> …`"]],
        widths=[2.2, 4.8],
    )
    d.para(
        "Deux raisons cumulées : **l'isolation mémoire** — la diarisation et le "
        "modèle de langue montent à plusieurs gigaoctets, le processus meurt à la "
        "fin et rend tout — et le fait qu'un exécutable figé **ne peut pas** "
        "exécuter `python -m module`."
    )
    d.para(
        "La sortie du sous-processus est lue ligne à ligne et réémise préfixée de "
        "l'identifiant du traitement, avec un filet en cas de console restée dans "
        "un encodage hérité. L'environnement est propagé intégralement — c'est ce "
        "qui transmet les chemins des modèles aux briques 1 et 3."
    )
    d.h3("Le nettoyage")
    d.para(
        "En fin de traitement, seuls **sept fichiers** sont conservés dans le "
        "dossier de la réunion : l'audio, le compte rendu en markdown et en Word, "
        "le marqueur d'agenda, le transcript, les tours de parole et le renommage "
        "des locuteurs. Tout le reste est supprimé. Le dossier étant visible par "
        "l'utilisateur dans l'Explorateur, il doit rester lisible."
    )
    d.warning(
        "**Ce nettoyage supprime aussi les fichiers déposés par l'utilisateur.** La "
        "fonction parcourt le dossier et supprime **tout fichier absent de la "
        "liste**, et elle est appelée à chaque traitement **et à chaque "
        "rechargement de l'historique**, donc à chaque démarrage de l'application. "
        "Un utilisateur qui range ses notes ou une pièce jointe dans le dossier de "
        "réunion les perd au prochain lancement, sans message. Voir §6.11."
    )

    d.h2("6.6 Les 28 endpoints")
    d.h3("Santé et paramètres")
    d.table(
        ["Endpoint", "Rôle"],
        [["`GET /api/health`", "sonde utilisée par Electron pour savoir quand afficher la fenêtre"],
         ["`GET /api/settings`", "indique si une clé Mistral est enregistrée — **jamais la clé**"],
         ["`PUT /api/settings`", "enregistre ou efface la clé"]],
        widths=[2.4, 4.6],
    )
    d.h3("Calendrier Microsoft")
    d.para("`GET /status` · `POST /login` · `POST /logout` · `GET /upcoming` — voir §6.7.")
    d.h3("Enregistrement")
    d.para(
        "`POST /start` · `POST /stop` · `GET /status` · `POST /cancel` — décrits en "
        "brique 2. Le magnétophone et le processeur temps réel sont des variables "
        "**globales** : un seul enregistrement à la fois."
    )
    d.h3("Import")
    d.table(
        ["Endpoint", "Rôle"],
        [["`POST /api/process/upload`", "fichier audio → dossier de réunion"],
         ["`POST /api/process/upload-transcript`", "`.txt` ou `.docx` Teams (§6.9)"]],
        widths=[3.0, 4.0],
    )
    d.h3("Cycle de vie d'un traitement")
    d.table(
        ["Endpoint", "Rôle"],
        [["`POST /api/jobs/{id}/process`", "lance le traitement en tâche de fond"],
         ["`GET /api/jobs`", "tous les traitements, par date décroissante"],
         ["`GET /api/jobs/{id}`", "un traitement"],
         ["`PATCH /api/jobs/{id}`", "renommer — refusé si en cours"],
         ["`DELETE /api/jobs/{id}`", "supprimer le dossier — refusé si en cours"],
         ["`POST /api/jobs/{id}/open-folder`", "ouvrir dans l'Explorateur"]],
        widths=[2.8, 4.2],
    )
    d.note(
        "**Le lancement est idempotent** (`main.py:1500`) : si le traitement est "
        "déjà terminé et que le compte rendu existe, la réponse le signale sans "
        "rien relancer. C'est ce qui permet au compte rendu produit en temps réel "
        "d'être simplement constaté."
    )
    d.h3("Contenus")
    d.table(
        ["Endpoint", "Rôle"],
        [["`GET /api/jobs/{id}/audio`", "flux audio pour le lecteur intégré"],
         ["`GET /api/jobs/{id}/turns`", "tours de parole + mapping des noms"],
         ["`PATCH /api/jobs/{id}/speakers`", "renommer les locuteurs"],
         ["`GET /api/jobs/{id}/download`", "compte rendu Word, ou transcript"],
         ["`PATCH /api/jobs/{id}/report`",
          "enregistrer le markdown édité — **régénère le Word**"]],
        widths=[2.8, 4.2],
    )
    d.para(
        "Le renommage des locuteurs mérite une note : le mapping est stocké à "
        "part. **Le fichier de tours de parole n'est jamais modifié** — les "
        "étiquettes brutes y restent la source de vérité, et l'interface applique "
        "le mapping au rendu. Un renommage est donc toujours réversible : une "
        "valeur vide retire l'entrée."
    )
    d.h3("Dossiers (catégories)")
    d.table(
        ["Endpoint", "Rôle"],
        [["`GET /api/folders`", "liste des catégories"],
         ["`POST /api/folders`", "créer — refusé si le nom existe"],
         ["`DELETE /api/folders/{nom}`", "supprimer — refusé si elle contient des réunions"],
         ["`POST /api/jobs/{id}/folder`", "déplacer une réunion, ou la ramener à la racine"]],
        widths=[2.8, 4.2],
    )
    d.para(
        "Le déplacement est un vrai déplacement de dossier sur le disque, suivi de "
        "la réécriture de tous les chemins mémorisés dans le traitement."
    )

    d.h2("6.7 Le calendrier Microsoft")
    d.para(
        "Intégration Microsoft Graph pour proposer les réunions à venir au moment "
        "de démarrer un enregistrement. **Modèle d'authentification : flux par code "
        "d'appareil, client public.**"
    )
    d.code("""POST /api/calendar/login
   └─► initiation du flux — renvoie un code et une URL à l'utilisateur
   └─► thread de fond : attente de la validation  (bloquant, jusqu'à ~15 min)
          l'interface interroge GET /api/calendar/status""")
    d.h3("Trois conséquences importantes")
    d.bullets([
        "**Aucun secret n'est embarqué dans le binaire distribué.** Un client "
        "public n'en a pas besoin ; il n'y a donc rien à extraire de "
        "l'exécutable.",
        "**Permission déléguée en lecture seule sur le calendrier.** Chaque "
        "salarié se connecte avec son propre compte et l'application ne voit que "
        "son agenda. Ce n'est pas une application de service qui lirait les "
        "agendas de tous.",
        "**Le flux est bloquant**, d'où le thread de fond et l'interrogation "
        "périodique par l'interface plutôt qu'une réponse HTTP qui resterait "
        "ouverte un quart d'heure.",
    ])
    d.para(
        "Les jetons sont mis en cache dans un fichier **chiffré** par les services "
        "de protection de données de Windows, donc lié au compte Windows de "
        "l'utilisateur. L'identifiant client et le locataire sont en dur, avec "
        "surcharge possible par variables d'environnement — prévu pour un futur "
        "passage multi-locataires."
    )
    d.note(
        "Toutes les fonctions du module sont **synchrones** — les bibliothèques "
        "sous-jacentes le sont. Les endpoints les appellent donc dans un fil "
        "d'exécution séparé pour ne pas bloquer le serveur."
    )

    d.h2("6.8 Conversion Markdown vers Word")
    d.para(
        "Le convertisseur est **écrit à la main**, sans bibliothèque de "
        "conversion : il lit le markdown ligne par ligne et pilote la génération du "
        "document."
    )
    d.table(
        ["Markdown", "Rendu Word"],
        [["`#` à `######`", "styles de titre natifs"],
         ["`- ` / `* `", "liste à puces"],
         ["`1. `", "liste numérotée"],
         ["`> `", "citation en retrait"],
         ["délimiteurs de code", "bloc de code"],
         ["tableau GFM", "vrai tableau Word"],
         ["`**gras**`, `*italique*`", "styles en ligne"]],
        widths=[2.4, 4.6],
    )
    d.para(
        "Les tableaux sont détectés par la conjonction d'une ligne en barres "
        "verticales **et** d'une ligne de séparation juste en dessous — c'est la "
        "règle GitHub, et elle évite de confondre un tableau avec une phrase "
        "contenant des barres verticales."
    )
    d.para(
        "La conversion est déclenchée deux fois : en fin de traitement, et à "
        "chaque enregistrement du compte rendu édité dans l'application."
    )
    d.note(
        "Ce convertisseur impose une contrainte à l'éditeur de l'interface : le "
        "markdown produit par l'édition doit correspondre exactement à ce que ce "
        "code sait lire. Voir §7.6."
    )

    d.h2("6.9 Import d'un transcript Teams")
    d.para(
        "Un module dédié convertit un export Teams au format Word vers le format "
        "interne. Il reconnaît les horodatages et les lignes de nom de participant."
    )
    d.para(
        "Ce chemin saute entièrement les briques 1 et 2 : le traitement est créé "
        "avec une source de type transcript, et le pipeline part directement à la "
        "normalisation."
    )

    d.h2("6.10 Journalisation, supervision et contraintes Windows")
    d.h3("Journalisation")
    d.table(
        ["Module", "Produit"],
        [["`job_logger.py`",
          "un journal détaillé par traitement, étape par étape, avec récapitulatif"],
         ["`resource_monitor.py`",
          "un échantillonnage mémoire toutes les 30 secondes"]],
        widths=[2.0, 5.0],
    )
    d.warning(
        "**Les deux sont désactivés en dur dans l'application livrée** "
        "(`main.py:71`). En mode figé, **aucune variable d'environnement standard "
        "ne les réactive** — les utilisateurs finaux n'écrivent rien dans leur "
        "dossier personnel. Seule une trappe non documentée permet de déboguer une "
        "installation packagée. En développement, les deux sont actifs par défaut."
    )
    d.para(
        "Le journal d'accès du serveur est désactivé, parce que l'interface "
        "interroge la liste des traitements en continu. Un intercepteur maison ne "
        "journalise que les erreurs."
    )
    d.h3("Les contraintes Windows et OneDrive")
    d.para("Une part notable du code de cette brique n'existe que pour ça.")
    d.table(
        ["Situation", "Traitement"],
        [
            ["Fichier `.docx` en lecture seule ou verrouillé par OneDrive",
             "la suppression réessaie après avoir rétabli les droits d'écriture, "
             "et **renvoie la liste des chemins qui ont résisté**"],
            ["Suppression d'une réunion qui échoue",
             "réponse **423 Locked** avec un message actionnable — et **le "
             "traitement est remis en mémoire**, pour que l'interface ne montre pas "
             "une réunion disparue qui existe encore sur disque"],
            ["Téléchargement d'un fichier ouvert dans Word",
             "le fichier est lu **en mémoire** avant la réponse, précisément pour "
             "transformer l'erreur de permission en 423 explicite plutôt qu'en "
             "erreur serveur opaque"],
            ["Nom de dossier saisi par l'utilisateur",
             "caractères interdits et caractères de contrôle retirés, points et "
             "espaces de fin supprimés, noms réservés préfixés, troncature à 200 "
             "caractères"],
            ["Ouverture de l'Explorateur",
             "passe par l'exécutable de l'Explorateur et non par l'ouverture "
             "générique : un processus en arrière-plan n'a pas le droit de passer "
             "au premier plan, mais l'Explorateur si"],
        ],
        widths=[2.4, 4.6],
    )

    d.h2("6.11 Limites connues")

    d.h3("Les fichiers de l'utilisateur sont supprimés")
    d.para(
        "Voir §6.5. Le nettoyage supprime **tout fichier** du dossier de réunion "
        "absent d'une liste de sept noms, à chaque démarrage de l'application. Le "
        "dossier étant visible dans l'Explorateur — et l'application proposant "
        "explicitement de l'ouvrir — y déposer un document est un geste naturel."
    )

    d.h3("Le marqueur d'origine est détruit par ce même nettoyage")
    d.para(
        "Le marqueur qui mémorise qu'une réunion vient d'un enregistrement **n'est "
        "pas dans la liste des fichiers conservés**, alors que le marqueur d'agenda "
        "y est. Il est donc supprimé dès la fin du premier traitement. L'impact "
        "réel est limité — un traitement déjà terminé ne se relance pas — mais "
        "l'intention du code est annulée et l'origine remontée à l'interface "
        "devient fausse."
    )

    d.h3("La suppression de dossier n'assainit pas son nom")
    d.para(
        "Asymétrie nette avec ses voisins : la création de dossier et le "
        "déplacement d'une réunion assainissent le nom reçu ; la suppression prend "
        "le paramètre d'URL tel quel. Un nom remontant l'arborescence résoudrait "
        "vers un dossier parent, que les garde-fous existants ne rattraperaient "
        "pas."
    )
    d.note(
        "Point **non testé** — l'essai porterait sur un dossier réel. L'exploitation "
        "suppose par ailleurs un client qui ne normalise pas le chemin. Le "
        "correctif tient en une ligne : appliquer la même fonction d'assainissement "
        "que les endpoints voisins."
    )

    d.h3("La liste des traitements renvoie tout l'historique")
    d.para(
        "Voir §6.4. Le markdown et le transcript **intégraux** de toutes les "
        "réunions, à chaque appel — et l'interface interroge cet endpoint toutes "
        "les 2,5 secondes, le processus Electron toutes les 5 secondes (§7.2 et "
        "§8.10). La correction naturelle consiste à retirer ces deux champs de la "
        "liste : ils sont déjà servis par l'endpoint qui renvoie un traitement seul."
    )

    d.h3("La clé Mistral est stockée en clair")
    d.para(
        "Alors que le jeton Microsoft, dans le même dossier, est chiffré par les "
        "services de protection de Windows. Le soin pris sur l'un souligne "
        "l'absence de soin sur l'autre."
    )

    d.h3("Autres limites")
    d.bullets([
        "**Identifiants éphémères** — régénérés à chaque démarrage (§6.3).",
        "**Un seul enregistrement, un seul traitement** — variables globales et "
        "verrou. Choix cohérent pour une application de bureau mono-utilisateur, "
        "mais rien n'est prévu pour en sortir.",
        "**Aucune authentification sur l'API.** Le serveur n'est pas accessible "
        "depuis le réseau, mais **tout processus tournant sur la machine** peut "
        "appeler ses endpoints — y compris lire les comptes rendus et déclencher un "
        "enregistrement.",
        "**Le contrôle d'origine accepte les pages locales**, nécessaire parce "
        "qu'Electron charge l'interface depuis le système de fichiers. Combiné au "
        "point précédent, une page web locale malveillante pourrait dialoguer avec "
        "l'API.",
        "**Catégories sur un seul niveau** — une réunion rangée plus profond par "
        "l'utilisateur **disparaît** de l'application, sans erreur : elle reste sur "
        "disque mais n'est plus listée.",
        "**Aucun test automatisé.**",
    ])

    d.h2("6.12 Vérifier le fonctionnement")
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"
python -m backend.run_app server        # 127.0.0.1:8000

# dans un autre terminal
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/folders""")
    d.note(
        "Le serveur expose aussi une documentation interactive sur `/docs` — "
        "pratique pour parcourir les 28 endpoints et leurs schémas sans lire le "
        "code."
    )
    d.h3("Points de contrôle")
    d.table(
        ["Trace au démarrage", "Interprétation"],
        [
            ["`Dossier des réunions : <chemin>`",
             "vérifie que la résolution a bien trouvé le dossier suivi par "
             "OneDrive, et non un dossier local vide"],
            ["`Historique rechargé : N réunion(s)`",
             "arrive **après** que le port réponde, c'est normal (§6.4). Une liste "
             "vide pendant quelques secondes au démarrage signifie que le balayage "
             "n'est pas terminé"],
            ["`Debug toggles : job_log=…, ram_monitor=…`", "confirme le mode"],
            ["Réponse **423**",
             "n'est pas un défaut : c'est le code qui signale un fichier verrouillé "
             "par Word ou OneDrive (§6.10)"],
        ],
        widths=[2.6, 4.4],
    )

    d.h2("6.13 Résumé pour une reprise")
    d.numbered([
        "**Aucune base de données.** Le système de fichiers fait foi : un dossier "
        "par réunion, des marqueurs cachés pour les métadonnées. L'état en mémoire "
        "est reconstruit à chaque démarrage.",
        "Une réunion se distingue d'une catégorie par la **seule présence d'un "
        "fichier audio ou d'un transcript brut**.",
        "Les **identifiants de traitement sont éphémères**.",
        "Le rechargement de l'historique tourne dans un **thread de fond** pour ne "
        "pas retarder l'ouverture de l'application, mais charge tout en mémoire.",
        "Le backend **n'exécute pas** les briques 1 et 3 : il les lance en "
        "sous-processus, pour l'isolation mémoire et parce qu'un exécutable figé ne "
        "peut pas lancer un module Python.",
        "Un **verrou global** garantit un seul traitement à la fois, et la mise en "
        "veille est bloquée pendant.",
        "Les données sensibles sont **hors du dossier synchronisé** — sauf la clé "
        "Mistral, stockée en clair (§6.11).",
        "Une part notable du code existe pour absorber les **fichiers verrouillés "
        "par Word et OneDrive**.",
    ])
    d.note(
        "**Premier point à corriger** — le nettoyage qui supprime les fichiers "
        "déposés par l'utilisateur (§6.11). C'est le seul défaut de cette brique "
        "qui provoque une perte de données silencieuse."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   7. Brique 5 — Shell Electron
# ═════════════════════════════════════════════════════════════════════════════
def section_7_electron(d: YeleDoc) -> None:
    d.h1("7. Brique 5 — Shell Electron")

    d.kv_table([
        ("Fichiers", "`electron/main.js` (~1 430 l.) et `electron/preload.js` (72 l.)"),
        ("Rôle", "héberger l'application — cycle de vie du backend, fenêtres, "
                 "barre des tâches, notifications"),
    ], label_w=3.0)
    d.note(
        "Ce chapitre couvre ce que fait le shell **à l'exécution**. Le packaging, "
        "le téléchargement des modèles au premier lancement et la publication des "
        "versions relèvent du chapitre 9. La mise à jour automatique figure ici "
        "uniquement pour la contrainte d'arrêt qu'elle impose au backend."
    )

    d.h2("7.1 Ce qu'est vraiment ce shell")
    d.para(
        "Electron n'affiche pas seulement une fenêtre : il est le **superviseur de "
        "processus** de l'application. Il démarre le backend Python, attend qu'il "
        "soit prêt, lui transmet les chemins des modèles, le tue proprement à la "
        "sortie, et continue de vivre en arrière-plan même quand l'utilisateur "
        "ferme la fenêtre."
    )
    d.warning(
        "**L'interface parle au backend en HTTP direct**, pas par messages "
        "internes. Le pont de préchargement n'expose qu'une adresse et quelques "
        "canaux d'événements ; toutes les données transitent par l'API de la "
        "brique 4."
    )

    d.h2("7.2 La séquence de démarrage")
    d.schema(SCH / "s14_demarrage.png",
             "Schéma 14 — Séquence de démarrage et règles d'arrêt du backend")
    d.h3("Le splash n'est pas cosmétique")
    d.para(
        "Le démarrage à froid du backend figé — chargement de Python, des "
        "bibliothèques de calcul et des moteurs d'inférence — prend plusieurs "
        "secondes. Sans splash, l'utilisateur double-clique et ne voit rien. La "
        "séquence est donc : afficher **d'abord** une fenêtre légère, démarrer le "
        "backend **ensuite**, et ne créer la vraie fenêtre qu'une fois la sonde de "
        "santé opérationnelle."
    )
    d.para(
        "Le contenu du splash et celui de la fenêtre de téléchargement sont "
        "**écrits en ligne dans le code** et chargés directement — pas de fichier "
        "supplémentaire à packager, pas d'étape de build pour deux écrans statiques."
    )
    d.h3("La bascule splash → fenêtre principale")
    d.para(
        "La fenêtre est créée masquée pour ne jamais peindre de blanc : elle "
        "apparaît et le splash disparaît dans la même image. Un filet de sécurité "
        "la révèle au bout de huit secondes si l'événement attendu ne se déclenche "
        "pas."
    )
    d.warning(
        "**L'idempotence de la révélation corrige un défaut précis**, expliqué en "
        "commentaire : sans un drapeau de garde, le filet de sécurité rappellerait "
        "l'affichage après coup. Or une fenêtre **réduite** est considérée comme "
        "non visible — l'application se serait donc dé-minimisée toute seule huit "
        "secondes après le démarrage."
    )

    d.h2("7.3 Le cycle de vie du backend")
    d.h3("Démarrage")
    d.para(
        "Le lancement construit l'environnement du processus fils — c'est le point "
        "de passage de toute la configuration de déploiement :"
    )
    d.code("""MODELS_DIR   SHERPA_DIR   PRETRAINED_DIR   LLAMA_BIN_DIR   MINILM_DIR
HF_HUB_OFFLINE = 1        TRANSFORMERS_OFFLINE = 1
PYTHONIOENCODING = utf-8
BACKEND_HOST = 127.0.0.1  BACKEND_PORT = 8000""")
    d.table(
        ["Mode", "Commande", "Répertoire de travail"],
        [["Développement", "`python -u -m backend.run_app server`", "racine du dépôt"],
         ["Production", "`backend.exe server`", "dossier de l'exécutable"]],
        widths=[1.6, 3.4, 2.0],
    )
    d.para(
        "La fenêtre de console est masquée. Les deux flux de sortie sont relayés "
        "vers ceux d'Electron, préfixés pour être distinguables."
    )
    d.h3("Attente de disponibilité")
    d.para(
        "La sonde de santé est interrogée toutes les 500 ms, avec une temporisation "
        "par requête de 2 s et un plafond global de **90 secondes**."
    )
    d.warning(
        "Sur une machine lente, ou au premier démarrage après une mise à jour — "
        "cache de fichiers froid, antivirus qui inspecte un exécutable fraîchement "
        "écrit — ces 90 secondes peuvent être dépassées. L'application affiche "
        "alors un échec de démarrage et quitte, **sans distinguer un backend lent "
        "d'un backend cassé**."
    )
    d.h3("Arrêt")
    d.table(
        ["Fonction", "Comportement"],
        [
            ["Arrêt simple",
             "tue **l'arbre entier** de processus, pas le seul processus racine : "
             "le serveur web engendre des fils, et le serveur de modèle en est un. "
             "Un signal sur la racine seule **laisse des orphelins** sous Windows"],
            ["Arrêt avec attente",
             "même chose, mais renvoie la main à la mort effective du processus, "
             "avec un plafond de 6 secondes"],
        ],
        widths=[1.8, 5.2],
    )
    d.warning(
        "**La seconde variante existe à cause d'un blocage observé en production.** "
        "L'ancien code demandait l'arrêt puis lançait immédiatement "
        "l'installation. Tant que le backend et le serveur de modèle tiennent les "
        "fichiers, l'installeur reste bloqué sur un accès refusé — mise à jour "
        "figée. Le plafond de 6 secondes est délibéré : mieux vaut une mise à jour "
        "qui continue qu'une application bloquée sur sa boîte de dialogue."
    )

    d.h2("7.4 La fenêtre principale")
    d.kv_table([
        ("Dimensions", "1280 × 800, minimum 900 × 600"),
        ("Isolation du contexte", "**activée**"),
        ("Intégration Node", "**désactivée**"),
        ("Bac à sable", "**actif**"),
    ], label_w=4.4)
    d.para(
        "La posture de sécurité est celle recommandée : l'interface n'a aucun "
        "accès à l'environnement d'exécution Node ; elle ne voit que ce que le "
        "pont de préchargement expose explicitement (§7.5)."
    )
    d.h3("Quatre comportements notables")
    d.bullets([
        "**Le titre est verrouillé** — les tentatives de la page de le modifier "
        "sont annulées, sinon le titre de la page écraserait celui de "
        "l'application.",
        "**Les liens externes s'ouvrent dans le navigateur système**, via un "
        "gestionnaire qui refuse systématiquement l'ouverture interne.",
        "**La recherche dans la page** passe par le moteur natif d'Electron, "
        "piloté depuis l'interface. Le choix est expliqué en commentaire : cela "
        "fonctionne quel que soit le mode de rendu — markdown affiché ou éditeur "
        "en édition directe.",
        "**Fermer la fenêtre ne quitte pas l'application** — §7.6.",
    ])

    d.h2("7.5 Le pont de préchargement")
    d.para(
        "Un unique objet est exposé à l'interface, sans jamais donner accès aux "
        "primitives d'Electron."
    )
    d.table(
        ["Clé", "Contenu"],
        [
            ["adresse du backend", "`http://127.0.0.1:8000`"],
            ["recherche", "démarrer, arrêter, recevoir les résultats"],
            ["notifications", "ouvrir une réunion depuis une notification d'agenda"],
            ["barre des tâches", "ouvrir un traitement, message de première "
                                 "réduction, signalement d'un changement de réglage"],
            ["fenêtre de la barre des tâches",
             "ouvrir l'application, quitter, démarrer et arrêter un enregistrement"],
        ],
        widths=[2.2, 4.8],
    )
    d.para(
        "Chaque abonnement renvoie **sa propre fonction de désabonnement**, pour "
        "que les composants de l'interface nettoient leurs écouteurs au démontage."
    )
    d.note(
        "Les boutons de la fenêtre de la barre des tâches **délèguent toutes leurs "
        "actions au processus principal** plutôt que d'appeler l'API directement. "
        "Le commentaire l'explique : sinon il faudrait dupliquer la logique — "
        "notifications natives, ouverture de la fenêtre, gestion d'état — entre "
        "cette fenêtre et le menu contextuel."
    )

    d.h2("7.6 Le mode arrière-plan")
    d.para(
        "C'est le comportement par défaut, en **retrait volontaire** : fermer la "
        "fenêtre **cache** l'application au lieu de la quitter. Le processus "
        "Electron et le backend continuent de tourner — sans quoi les "
        "notifications et l'enregistrement depuis la barre des tâches cesseraient "
        "de fonctionner."
    )
    d.schema(SCH / "s15_mode_tray.png",
             "Schéma 15 — Le mode arrière-plan : fermeture, icône et notifications")
    d.h3("La fenêtre de la barre des tâches")
    d.para(
        "Un second niveau d'interface : une petite fenêtre sans bordure, ancrée à "
        "l'icône, qui charge une route dédiée de l'interface. Elle offre les mêmes "
        "actions dans une présentation plus riche que le menu contextuel."
    )
    d.h3("Lancement au démarrage de Windows")
    d.para(
        "Le réglage utilise le mécanisme natif de Windows, avec un argument "
        "spécifique. Au démarrage de session, l'application se réduit donc "
        "directement dans la barre des tâches au lieu d'ouvrir sa fenêtre — "
        "présente « au cas où », sans s'imposer."
    )

    d.h2("7.7 Les notifications")
    d.table(
        ["Mécanisme", "Déclenchement", "Fréquence"],
        [
            ["« Compte rendu prêt »",
             "détection de la transition d'un traitement vers l'état terminé, en "
             "comparant avec l'ensemble vu au tour précédent",
             "toutes les **5 s**"],
            ["Rappel avant réunion",
             "un minuteur est programmé pour chaque réunion commençant dans "
             "l'heure ; deux structures évitent les doublons",
             "sondage toutes les **5 min**"],
            ["Rappel de fin de réunion",
             "programmé à l'heure de fin déclarée, uniquement pour un "
             "enregistrement rattaché à une réunion ayant une fin future",
             "à l'échéance"],
        ],
        widths=[1.8, 3.8, 1.4],
    )
    d.note(
        "Une ligne de configuration déclare l'identité de l'application auprès de "
        "Windows. Sans elle, les notifications s'affichent sous un nom générique "
        "avec une icône par défaut. Elle doit correspondre à l'identifiant déclaré "
        "pour l'empaquetage."
    )

    d.h2("7.8 La mise à jour automatique")
    d.para(
        "Désactivée en développement. En production : téléchargement en fond sans "
        "rien demander, installation au prochain arrêt, et une boîte de dialogue "
        "proposant de redémarrer immédiatement."
    )
    d.para(
        "Si l'utilisateur accepte, l'arrêt **avec attente** du backend est "
        "exécuté avant de lancer l'installation — voir §7.3."
    )
    d.warning(
        "**Toutes les erreurs de mise à jour sont silencieuses** — seulement "
        "journalisées en console. C'est délibéré : un poste hors ligne ne doit pas "
        "bloquer l'application. Mais la conséquence est qu'un poste qui ne se met "
        "jamais à jour — jeton expiré, proxy bloquant, dépôt inaccessible — ne le "
        "signale nulle part. **Rien dans l'interface ne montre la version "
        "installée ni la date de la dernière vérification.**"
    )

    d.h2("7.9 La compatibilité réseau d'entreprise")
    d.para(
        "Deux options autorisent le moteur de rendu à répondre automatiquement aux "
        "authentifications intégrées exigées par les proxys d'entreprise. Sans "
        "elles, le téléchargement des modèles et la vérification des mises à jour "
        "échouent derrière un proxy authentifié, sans message exploitable."
    )
    d.warning(
        "La délégation est accordée à **tous les hôtes**, sans restriction. C'est "
        "le réglage le plus permissif ; une liste explicite serait plus sûre."
    )

    d.h2("7.10 Limites connues")

    d.h3("Trois sondages simultanés sur le même backend")
    d.table(
        ["Origine", "Cible", "Fréquence"],
        [["processus principal — état de la barre des tâches", "état d'enregistrement", "4 s"],
         ["processus principal — notification « compte rendu prêt »",
          "**liste des traitements**", "5 s"],
         ["interface — liste des réunions", "**liste des traitements**", "2,5 s"]],
        widths=[3.4, 2.2, 1.4],
    )
    d.para(
        "La liste des traitements renvoie le markdown et le transcript intégraux "
        "de **tout** l'historique (§6.11). Elle est donc récupérée en entier "
        "**deux fois par tranche de 5 secondes, par deux processus différents**, "
        "alors que le processus principal n'a besoin que de l'identifiant et de "
        "l'état. Voir §8.9 pour le tableau complet."
    )

    d.h3("Autres limites")
    d.bullets([
        "**Le délai de 90 secondes ne distingue pas lent de cassé** (§7.3).",
        "**L'état des mises à jour est invisible** (§7.8) — ni version affichée, "
        "ni date de dernière vérification, ni signalement d'échec.",
        "**La délégation d'authentification est ouverte à tous les hôtes** (§7.9).",
        "**Une application qui ne se ferme pas vraiment** — le comportement est "
        "recherché, mais il surprend. La découverte se fait par la notification "
        "affichée à la première fermeture ; si l'utilisateur la manque, il n'a plus "
        "d'indication hors l'icône.",
        "**Aucun test automatisé** — un seul fichier de test existe dans tout le "
        "projet, et il couvre le téléchargement des modèles (chapitre 9).",
    ])

    d.h2("7.11 Vérifier le fonctionnement")
    d.code("""# terminal 1 — interface en rechargement à chaud
cd webapp ; npm run dev

# terminal 2 — Electron + backend depuis les sources
& ".\\meeting_assistant\\Scripts\\Activate.ps1"
cd electron ; npm run dev:hot""")
    d.h3("Traces à suivre au démarrage")
    d.table(
        ["Trace", "Signification"],
        [["`spawn backend: …`", "commande réellement lancée — vérifie le mode"],
         ["`[backend] …`", "sortie du processus Python, relayée"],
         ["`backend exited (code=…)`",
          "arrêt du backend ; un code non nul en cours de session est anormal"],
         ["`[updater] …`", "seule trace des mises à jour (§7.8)"]],
        widths=[2.4, 4.6],
    )
    d.h3("Points de contrôle")
    d.bullets([
        "Fermer la fenêtre doit **cacher** l'application, pas la quitter : "
        "l'icône reste dans la barre des tâches et le processus du backend vit "
        "toujours.",
        "Pendant un enregistrement, l'icône doit porter la pastille rouge et le "
        "menu afficher la durée écoulée.",
        "Après une mise à jour acceptée, **aucun processus du backend ni du "
        "serveur de modèle ne doit subsister** dans le gestionnaire de tâches — "
        "sinon l'installeur restera bloqué (§7.3).",
    ])

    d.h2("7.12 Résumé pour une reprise")
    d.numbered([
        "Electron est le **superviseur de processus** : il démarre le backend, lui "
        "transmet les chemins des modèles par variables d'environnement, attend sa "
        "sonde de santé, et le tue par **arbre de processus**.",
        "La séquence de démarrage est ordonnée et bloquante : modèles → splash → "
        "backend → attente → fenêtre. Toute erreur ferme proprement.",
        "L'interface parle au backend **en HTTP direct**. Le pont de préchargement "
        "n'expose qu'une adresse et des canaux d'événements — isolation du "
        "contexte, pas d'intégration Node, bac à sable actif.",
        "L'application **vit en arrière-plan par défaut** : fermer la fenêtre la "
        "cache.",
        "L'attente de la mort effective du backend avant une mise à jour n'est pas "
        "une précaution théorique : sans elle, l'installeur se bloque sur des "
        "fichiers verrouillés.",
        "Trois mécanismes de notification indépendants, tous par sondage du backend.",
    ])
    d.note(
        "**Premier chantier si l'on doit optimiser** — les trois sondages "
        "simultanés (§7.10), dont deux récupèrent l'intégralité de l'historique "
        "toutes les 5 secondes."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   8. Brique 6 — Frontend
# ═════════════════════════════════════════════════════════════════════════════
def section_8_frontend(d: YeleDoc) -> None:
    d.h1("8. Brique 6 — Frontend")

    d.kv_table([
        ("Dossier", "`webapp/` — 18 composants, 5 modules utilitaires, 2 pages"),
        ("Technologie", "Next.js 15 / React 19 / TypeScript / Tailwind, en export statique"),
        ("Rôle", "l'interface de l'application, servie en statique et chargée par Electron"),
    ], label_w=3.0)

    d.h2("8.1 Une application à état, pas un site à routes")
    d.para("Next.js est utilisé en **export statique**. Il n'y a que deux pages :")
    d.table(
        ["Route", "Chargée par", "Rôle"],
        [["`/`", "fenêtre principale d'Electron", "toute l'application"],
         ["`/tray-popup`", "fenêtre de la barre des tâches", "interface réduite"]],
        widths=[1.4, 2.6, 3.0],
    )
    d.para(
        "La page principale n'utilise **aucun routage**. Trois variables d'état "
        "déterminent à elles seules ce qui s'affiche."
    )
    d.schema(SCH / "s16_navigation.png",
             "Schéma 16 — Navigation par état : trois variables, cinq vues")
    d.para(
        "C'est cohérent avec la cible : dans une fenêtre Electron chargée depuis le "
        "système de fichiers, une adresse ne se partage pas et le bouton "
        "« précédent » n'existe pas. Le prix à payer est que **la navigation n'est "
        "pas adressable** — rien ne permet de rouvrir directement une réunion par "
        "un lien."
    )

    d.h3("Le raccord avec Electron")
    d.para("L'adresse du backend est résolue en trois temps :")
    d.numbered([
        "celle exposée par le pont de préchargement, dans Electron ;",
        "une variable d'environnement de compilation, pour le développement en "
        "navigateur ;",
        "une valeur de repli codée en dur.",
    ])
    d.para(
        "C'est ce qui permet d'ouvrir l'interface dans un simple navigateur, sans "
        "Electron, pendant le développement."
    )
    d.para(
        "Le pont de préchargement sert uniquement aux **événements** : la page "
        "principale s'abonne à trois canaux au montage."
    )
    d.note(
        "Le canal de « première réduction en arrière-plan » mérite un détour : la "
        "fenêtre venant d'être cachée, **une fenêtre modale dans l'interface serait "
        "invisible**. L'interface déclenche donc une notification système, et pose "
        "un drapeau de persistance locale pour ne le faire qu'une fois."
    )

    d.h2("8.2 La synchronisation d'état : du sondage, partout")
    d.para(
        "Il n'y a ni WebSocket, ni flux d'événements serveur, ni gestionnaire "
        "d'état global. Chaque composant qui a besoin d'une donnée fraîche la "
        "redemande à intervalle fixe."
    )
    d.para("La justification est écrite dans le code :")
    d.note(
        "*Pourquoi un sondage plutôt qu'un flux : un seul enregistrement actif à la "
        "fois, deux secondes de latence sont largement acceptables, et ça reste "
        "robuste si le backend redémarre pendant que l'application tourne — le "
        "composant se resynchronise tout seul.*"
    )
    d.para("L'argument de robustesse est réel : un backend redémarré ne casse rien.")
    d.schema(SCH / "s17_sondages.png",
             "Schéma 17 — Charge de sondage cumulée sur la liste des traitements")
    d.h3("Le tableau complet")
    d.table(
        ["Origine", "Cible", "Intervalle"],
        [
            ["**Sidebar**", "liste des traitements + dossiers", "2,5 s"],
            ["**SearchOverlay**", "idem", "2,5 s"],
            ["ReportsPage *(si affichée)*", "idem", "2,5 s"],
            ["FoldersPage *(si affichée)*", "idem", "2,5 s"],
            ["Sidebar", "état d'enregistrement", "2 s"],
            ["MeetingsHome", "état d'enregistrement", "2 s"],
            ["JobPanel *(réunion ouverte)*", "un traitement", "1,5 s"],
            ["MeetingsHome *(connecté à l'agenda)*", "liste des traitements", "4 s"],
            ["MeetingsHome *(connexion en cours)*", "état de la connexion", "3 s"],
            ["Sidebar", "état de la connexion", "10 s"],
            ["Fenêtre barre des tâches *(si ouverte)*", "agenda + traitements", "4 s"],
        ],
        widths=[3.0, 2.4, 1.6],
    )
    d.warning(
        "**Le hook de récupération n'est pas mutualisé.** Sa propre documentation "
        "le dit : « chaque consommateur a son propre intervalle ». Le code de "
        "récupération n'est plus dupliqué, mais les requêtes le sont.\n"
        "Et **la recherche globale interroge le backend même fermée** — elle est "
        "rendue en permanence avec une simple propriété d'ouverture, et un hook ne "
        "peut pas être conditionnel. Elle sonde donc en continu une liste qu'elle "
        "n'affiche pas."
    )
    d.para(
        "Les trois briques 4, 5 et 6 signalent le même défaut ; c'est ici qu'on en "
        "voit l'accumulation."
    )

    d.h2("8.3 La timeline unifiée")
    d.para("Deux sources qui ne se connaissent pas sont fusionnées :")
    d.code("""réunions à venir  (agenda Microsoft)
réunions enregistrées  (traitements)

clé de liaison :  identifiant d'événement du traitement == identifiant de l'événement""")
    d.para(
        "La construction produit deux listes : les **à venir** — événements "
        "d'agenda sans traitement associé, triés par heure croissante — et les "
        "**enregistrées**, plus récentes d'abord. Un événement d'agenda "
        "**disparaît des « à venir » dès qu'il a été enregistré** : c'est le "
        "traitement qui le représente désormais."
    )
    d.h3("Trois règles métier qui vivent ici")
    d.table(
        ["Règle", "Comportement"],
        [
            ["Nom affiché",
             "si le libellé ressemble à un dossier auto-daté et qu'un sujet "
             "d'agenda existe, on affiche le sujet. Un renommage manuel gagne "
             "toujours"],
            ["Entreprises devinées",
             "extraction du domaine de chaque adresse, mise à l'écart d'une liste "
             "de fournisseurs grand public, capitalisation du reste. Ce sont les "
             "valeurs pré-remplies qui alimenteront les *entités figées* du prompt "
             "(§5.3)"],
            ["Dates de l'agenda",
             "les fractions de seconde sont retirées avant l'analyse. Le "
             "commentaire assume l'hypothèse : le poste est à l'heure de Paris, et "
             "le service renvoie l'heure locale sans décalage"],
        ],
        widths=[1.8, 5.2],
    )

    d.h2("8.4 Le pré-remplissage depuis l'agenda")
    d.para(
        "Un **module singleton** de trois fonctions autour d'une variable, avec une "
        "sémantique « une seule fois » : la lecture vide la valeur."
    )
    d.para(
        "Le choix est justifié dans le fichier : le trajet de la donnée traverse "
        "cinq composants et un changement d'onglet. La faire descendre en "
        "propriétés alourdirait toute la chaîne pour une donnée consommée une seule "
        "fois. L'application étant une page unique sans rechargement, un module "
        "suffit."
    )
    d.para(
        "Ce que ça transporte : participants, entreprises devinées, et un contexte "
        "composé — sujet, organisateur, lieu, nature de la réunion, puis **la "
        "description complète** de l'invitation."
    )
    d.note(
        "La description n'est pas tronquée, volontairement : elle part telle quelle "
        "dans le prompt système du backend, et couper masquerait des sigles ou des "
        "instructions utiles."
    )

    d.h2("8.5 La vue réunion")
    d.h3("Des onglets, dont un optionnel")
    d.bullets([
        "**Compte rendu** — toujours présent, non fermable.",
        "**Transcript** — ouvert par un bouton, fermable par une croix. Son état "
        "est persisté localement, pour que la disposition suive l'utilisateur d'une "
        "réunion à l'autre.",
    ])
    d.h3("Un seul élément audio, monté haut")
    d.code("""MeetingDetail
   ├─ <audio>          <- monté UNE SEULE FOIS, dès qu'un audio existe
   ├─ JobPanel         (lecteur visible, contrôles)
   └─ TranscriptView   (reçoit la référence : navigation + surlignage)""")
    d.para(
        "L'élément est monté au niveau du conteneur **même quand le lecteur n'est "
        "pas visible**. Sans cela, la vue transcript ne pourrait pas se "
        "synchroniser avant que l'utilisateur ait ouvert le lecteur."
    )
    d.note(
        "Corollaire soigné : cliquer sur une ligne du transcript déplace la lecture "
        "**et** demande au parent d'afficher le lecteur — sinon l'audio se "
        "lancerait sans aucun contrôle visible, ni pause ni curseur."
    )

    d.h2("8.6 La vue transcript")
    d.para(
        "Elle consomme les tours de parole et le mapping des noms — les deux "
        "fichiers dont les briques 1, 2 et 4 décrivent la production."
    )
    d.h3("Synchronisation avec l'audio")
    d.para(
        "Un écouteur sur la progression de lecture cherche le tour de parole "
        "contenant l'instant courant. La recherche est **linéaire**, et le "
        "commentaire l'assume : quelques centaines de tours pour une réunion d'une "
        "heure, une recherche dichotomique n'apporterait rien."
    )
    d.para(
        "Le défilement automatique n'a lieu que si **l'index change et que "
        "l'élément est hors du cadre visible** — sinon la liste vibrerait à chaque "
        "impulsion de l'audio."
    )
    d.h3("Renommage des locuteurs")
    d.para(
        "L'interface propose les participants issus de l'agenda pour remplacer les "
        "étiquettes. La mise à jour est **optimiste** : l'état local change "
        "immédiatement, la requête part ensuite, et en cas d'échec on recharge "
        "depuis le backend pour resynchroniser."
    )
    d.para(
        "Le mapping est stocké séparément côté backend ; le fichier de tours de "
        "parole conserve les étiquettes brutes (§6.6). Un renommage reste donc "
        "toujours réversible."
    )

    d.h2("8.7 L'éditeur de compte rendu")
    d.para("C'est la partie la plus délicate du frontend.")
    d.schema(SCH / "s18_editeur.png",
             "Schéma 18 — L'aller-retour markdown → HTML → markdown et ses règles maison")
    d.para(
        "Chaque enregistrement traverse donc **markdown → HTML → markdown**, avec "
        "une temporisation d'une seconde après la dernière frappe."
    )
    d.h3("Trois règles maison pour les tableaux")
    d.para("Le convertisseur standard ne suffisait pas, et le code explique pourquoi :")
    d.note(
        "*La règle de tableau standard laisse le tableau en HTML brut dès que la "
        "première ligne ne passe pas son test strict — or l'éditeur émet des "
        "paragraphes dans les cellules. Et le convertisseur Word du backend ne lit "
        "QUE le markdown de tableau : document cassé.*"
    )
    d.table(
        ["Règle", "Rôle"],
        [
            ["Déballage des cellules", "retire les paragraphes que l'éditeur place "
                                       "dans les cellules"],
            ["Reconstruction du tableau",
             "**reconstruit** chaque tableau de façon déterministe, en normalisant "
             "le nombre de colonnes et en échappant les barres verticales"],
            ["Filet de sécurité",
             "aucune balise de tableau ne doit survivre en HTML dans le markdown"],
        ],
        widths=[2.2, 4.8],
    )
    d.para(
        "L'échappement automatique du convertisseur est par ailleurs neutralisé : "
        "l'éditeur garantissant la structure, il ne ferait que polluer la sortie."
    )
    d.warning(
        "C'est un exemple net de **couplage entre briques** : le format produit ici "
        "doit correspondre exactement à ce que le convertisseur Word du backend "
        "sait lire (§6.8).\n"
        "**Et l'aller-retour n'est pas neutre** : ouvrir un compte rendu et taper "
        "un seul caractère réécrit **tout** le fichier tel que le convertisseur le "
        "re-sérialise — espacements, style des titres, marqueurs de liste. Le "
        "résultat reste du markdown valide et lisible par le backend, mais ce n'est "
        "pas nécessairement l'octet à octet de ce que le modèle avait produit."
    )

    d.h2("8.8 Les autres composants")
    d.table(
        ["Composant", "Rôle"],
        [
            ["Sidebar", "navigation, réunions récentes, pastille « enregistrement "
                        "en cours » cliquable, accès aux paramètres"],
            ["MeetingsHome", "vue d'accueil : agenda et timeline fusionnée, "
                             "connexion Microsoft"],
            ["OnboardingView", "page capture : enregistrer, importer un audio, "
                               "importer un transcript"],
            ["Recorder", "bouton d'enregistrement, minuteur, **reprise d'un "
                         "enregistrement déjà en cours au montage**"],
            ["JobPanel", "état du traitement, sélecteur local / Mistral, lecteur "
                         "audio, actions"],
            ["ReportsPage / FoldersPage", "listes, filtrage par dossier"],
            ["JobHistory", "liste groupée par jour"],
            ["SearchOverlay", "recherche globale"],
            ["ReportFindBar", "recherche **dans** le compte rendu — délègue au "
                              "moteur natif d'Electron (§7.4)"],
            ["SettingsDialog", "clé Mistral, compte Microsoft, préférences de fenêtre"],
            ["Uploader / TranscriptUploader", "envoi de fichiers"],
            ["MiniCalendar, ThemeToggle", "utilitaires d'affichage"],
        ],
        widths=[2.2, 4.8],
    )
    d.h3("Deux comportements notables")
    d.bullets([
        "**La reprise d'enregistrement.** Au montage, le composant interroge "
        "l'état côté backend : si un enregistrement est en cours, il restitue le "
        "minuteur et le bouton d'arrêt. C'est ce qui rend la pastille de la barre "
        "latérale fonctionnelle après une navigation.",
        "**Le raccourci de recherche a deux comportements.** Sans réunion ouverte, "
        "il ouvre la recherche globale ; avec une réunion ouverte, la barre de "
        "recherche du compte rendu le capte et lance la recherche native.",
    ])

    d.h2("8.9 Limites connues")

    d.h3("Le sondage se multiplie par le nombre de composants montés")
    d.para(
        "Voir §8.2. Mutualiser le hook de récupération — un intervalle unique "
        "partagé par un contexte React — diviserait le trafic par deux ou trois "
        "**sans toucher au backend**. C'est le levier d'optimisation le plus "
        "rentable du projet."
    )

    d.h3("L'aller-retour de l'éditeur réécrit tout le fichier")
    d.para("Voir §8.7.")

    d.h3("La navigation n'est pas adressable")
    d.para(
        "Voir §8.1. Ni lien profond, ni historique de navigation. Acceptable dans "
        "une fenêtre Electron, bloquant si l'interface devait un jour être servie "
        "sur le web."
    )

    d.h3("Le fuseau horaire est supposé")
    d.para(
        "Voir §8.3. Le poste est supposé à l'heure de Paris. Un utilisateur en "
        "déplacement verrait des horaires décalés."
    )

    d.h3("Aucun test automatisé")
    d.para("Ni test unitaire, ni test de rendu.")

    d.h2("8.10 Vérifier le fonctionnement")
    d.code("""cd webapp
npm run dev        # http://localhost:3000""")
    d.para(
        "L'interface fonctionne dans un navigateur ordinaire, sans Electron : la "
        "résolution d'adresse retombe sur le backend local (§8.1). Il suffit que "
        "celui-ci tourne."
    )
    d.para(
        "Ce qui **ne fonctionne pas** hors Electron : la recherche dans le compte "
        "rendu, les notifications natives, la reprise depuis la barre des tâches — "
        "tout ce qui passe par le pont de préchargement. Le code utilise "
        "systématiquement l'appel optionnel pour que l'absence du pont ne casse "
        "rien."
    )
    d.h3("Points de contrôle")
    d.bullets([
        "L'onglet réseau des outils de développement montre le **rythme réel des "
        "sondages** (§8.2) — c'est le moyen le plus direct de constater le problème.",
        "Après édition d'un compte rendu, vérifier que le fichier Word a bien été "
        "régénéré et que les **tableaux** y sont des tableaux, pas du texte brut : "
        "c'est ce que valident les trois règles de conversion (§8.7).",
        "Un renommage de locuteur doit **survivre à un rechargement** de la "
        "fenêtre : il est persisté côté backend, pas seulement en mémoire.",
    ])

    d.h2("8.11 Résumé pour une reprise")
    d.numbered([
        "**Pas de routage** : une seule page, trois variables d'état commutent "
        "entre cinq vues. Un second point d'entrée sert la barre des tâches.",
        "**Pas de gestionnaire d'état, pas de WebSocket** : tout est du sondage "
        "HTTP direct vers le backend. Le raccord Electron ne sert qu'aux événements.",
        "Le sondage **se multiplie par le nombre de composants montés** — c'est le "
        "principal levier d'optimisation (§8.9).",
        "La **timeline** fusionne agenda et réunions enregistrées. Les règles de "
        "nommage, de devinette d'entreprises et de composition du contexte vivent "
        "dans un module utilitaire dédié.",
        "L'**éditeur** fait un aller-retour markdown → HTML → markdown à chaque "
        "enregistrement, avec trois règles de conversion maison pour que les "
        "tableaux restent lisibles par le convertisseur Word du backend.",
        "La **vue transcript** est le point de convergence des briques 1, 2 et 4 : "
        "elle consomme les tours de parole et le mapping des noms, et se "
        "synchronise à l'audio par un élément monté haut dans la hiérarchie.",
    ])
    d.note(
        "**Premier chantier si l'on doit optimiser** — mutualiser le hook de "
        "récupération en un intervalle unique partagé (§8.9). C'est du code "
        "frontend seul, sans impact sur le backend, et cela réduit immédiatement "
        "le trafic le plus lourd de l'application."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   9. Brique 7 — Build & distribution
# ═════════════════════════════════════════════════════════════════════════════
def section_9_build(d: YeleDoc) -> None:
    d.h1("9. Brique 7 — Build & distribution")

    d.kv_table([
        ("Fichiers", "`build/backend.spec`, `electron/package.json`, "
                     "`electron/build-app.js`, `electron/downloader.js`, "
                     "`electron/model_manifest.js`, `scripts/prepare_assets.py`"),
        ("Rôle", "transformer le dépôt en un installeur Windows, le publier, et "
                 "le mettre à jour sur les postes"),
    ], label_w=3.0)
    d.note(
        "Les **procédures opérationnelles** — commandes exactes, ordre des étapes, "
        "dépannage — sont déjà écrites dans les fiches `WORKFLOW.md` et `BUILD.md` "
        "du dépôt. Ce chapitre explique **comment c'est construit et pourquoi**, "
        "pas comment le lancer."
    )

    d.h2("9.1 Ce que contient l'installeur — et ce qu'il ne contient pas")
    d.schema(SCH / "s19_installeur.png",
             "Schéma 19 — Composition de l'installeur et téléchargement au premier lancement")
    d.para(
        "**Les ~2,3 Go de modèles ne sont pas dans l'installeur.** Le commentaire "
        "du fichier de configuration donne la raison : les fichiers volumineux "
        "partent par un autre canal pour que le même exécutable de 32 Mo n'ait pas "
        "besoin d'être reconstruit quand les modèles changent."
    )
    d.para(
        "Découplage utile : publier une nouvelle version de l'application ne "
        "réexpédie pas 2,3 Go à chaque poste."
    )

    d.h2("9.2 Le figeage du backend")
    d.para(
        "La compilation produit un exécutable en **mode un-dossier**, avec la "
        "console conservée pour que les traces du backend restent lisibles. Le "
        "point d'entrée est le répartiteur multi-mode décrit en §6.5."
    )
    d.h3("Trois catégories de dépendances à déclarer")
    d.numbered([
        "**Paquets à collecter intégralement** — seize paquets : moteurs "
        "d'inférence, bibliothèques audio, bibliothèques scientifiques, "
        "authentification Microsoft, génération de documents Word. Le paquet de "
        "détection de parole porte un commentaire explicite : son sous-paquet de "
        "données contient le modèle, et c'est ce qui fait que le VAD est **embarqué "
        "dans l'exécutable**, à la différence des deux autres modèles.",
        "**Imports résolus par chaîne de caractères** — le serveur web charge ses "
        "protocoles et sa boucle d'événements par nom au démarrage. Sans ces "
        "déclarations, l'exécutable démarre puis **renvoie une erreur à la première "
        "requête**.",
        "**Modules du projet appelés par sous-commande** — le répartiteur les "
        "atteint par un mécanisme que l'analyse statique ne voit pas.",
    ])
    d.warning(
        "**Tout nouveau module doit être ajouté à cette troisième liste.** Un "
        "module oublié produit un exécutable qui **se construit sans erreur et "
        "plante à l'exécution** — le pire des symptômes, puisque la construction "
        "passe au vert."
    )
    d.para(
        "Des exclusions retirent les bibliothèques graphiques et interactives "
        "tirées transitivement par les paquets scientifiques : inutiles ici, et "
        "coûteuses en taille."
    )

    d.h2("9.3 L'empaquetage Electron")
    d.table(
        ["Réglage", "Valeur", "Effet"],
        [
            ["Type d'installeur", "assistant", "pas d'installation muette"],
            ["Portée", "**par utilisateur**", "**pas de droits administrateur requis**"],
            ["Chemin d'installation", "imposé", "l'utilisateur ne le choisit pas"],
            ["Raccourcis", "bureau + menu Démarrer", ""],
        ],
        widths=[1.8, 1.8, 3.4],
    )
    d.para(
        "L'installation par utilisateur est cohérente avec le reste : les modèles "
        "vont dans un dossier utilisateur, les réglages aussi. **Rien n'exige "
        "d'élévation**, ce qui compte en environnement d'entreprise verrouillé."
    )
    d.warning(
        "**Aucune signature de code n'est configurée.** L'installeur déclenche donc "
        "l'avertissement de réputation de Windows — « éditeur inconnu » — que "
        "chaque utilisateur doit contourner à la main. C'est le principal frein au "
        "déploiement à grande échelle, et cela se résout par l'achat d'un "
        "certificat, pas par du code."
    )
    d.note(
        "**La version pilote tout** : nom de l'artefact, étiquette de la "
        "publication, et comparaison pour la mise à jour automatique. C'est la "
        "**seule valeur à modifier** pour publier — sans incrément, les postes "
        "installés ne voient pas la nouvelle version."
    )

    d.h2("9.4 Les modèles : téléchargement au premier lancement")
    d.h3("Le manifeste")
    d.para(
        "Une liste **statique**, sans aucun appel d'API pour la construire. Chaque "
        "entrée porte quatre champs :"
    )
    d.table(
        ["Champ", "Rôle"],
        [["nom de l'asset", "sur la publication — **pas** une adresse"],
         ["adresse de repli", "vers la source secondaire"],
         ["chemin de destination", "sous le dossier utilisateur"],
         ["taille exacte attendue",
          "sert à la fois de vérification d'intégrité et de reprise"]],
        widths=[2.2, 4.8],
    )
    d.para(
        "Le commentaire précise qu'une partie de la liste était auparavant "
        "énumérée dynamiquement, et qu'elle a été figée : cela supprimait une "
        "dépendance réseau supplémentaire, sur un point d'accès souvent filtré par "
        "les pare-feux."
    )
    d.h3("Pourquoi cette source en priorité")
    d.note(
        "*Ces URLs sont autorisées par défaut dans la quasi-totalité des systèmes "
        "d'information d'entreprise — les développeurs en ont besoin partout. Cela "
        "évite le filtrage des plateformes d'intelligence artificielle, souvent "
        "bloquées chez les grands comptes.*"
    )
    d.para(
        "Et pourquoi un dépôt **privé** : ne pas rediffuser publiquement des "
        "modèles tiers dont les licences ne couvrent pas forcément le miroir "
        "public, et réutiliser le jeton déjà embarqué pour les mises à jour."
    )
    d.h3("La contrainte du dépôt privé")
    d.para("C'est le détail qui coûte le plus cher à redécouvrir :")
    d.warning(
        "L'adresse de téléchargement **de type navigateur ne fonctionne pas** avec "
        "un jeton sur un dépôt privé — elle exige un cookie de session web et "
        "renvoie une erreur de ressource introuvable."
    )
    d.para("Le chemin correct, implémenté par le téléchargeur :")
    d.numbered([
        "interroger l'API pour lister les assets de la publication, chacun avec "
        "son adresse d'API ;",
        "demander cette adresse en précisant qu'on attend un flux binaire — la "
        "réponse est une redirection vers une adresse signée temporaire.",
    ])
    d.para(
        "Le manifeste ne stocke donc que le **nom** de l'asset ; l'adresse est "
        "résolue au moment du téléchargement, puis mise en cache."
    )

    d.h3("Le choix de la pile réseau")
    d.para(
        "C'est le choix technique le plus important de cette brique. Le "
        "téléchargeur utilise la **pile réseau du moteur de rendu**, et non celle "
        "de l'environnement d'exécution JavaScript."
    )
    d.para("Elle honore **automatiquement** :")
    d.bullets([
        "le proxy système et ses mécanismes de découverte automatique ;",
        "l'authentification proxy ;",
        "l'inspection SSL d'entreprise — certificats injectés dans le magasin de "
        "Windows ;",
        "le retrait de l'en-tête d'autorisation sur une redirection inter-domaines, "
        "comme le ferait un navigateur — **indispensable** pour les assets de dépôt "
        "privé.",
    ])
    d.note(
        "Le commentaire résume : *« se comporte exactement comme un navigateur, qui "
        "marche partout en entreprise »*, et cite le cas concret d'un client dont "
        "le navigateur passe par un proxy alors qu'un appel réseau direct est "
        "bloqué par le pare-feu — donc expiration de délai."
    )

    d.h3("Robustesse du téléchargement")
    d.table(
        ["Mécanisme", "Détail"],
        [
            ["**Reprise**", "en-tête de plage d'octets calculé sur la taille du "
                            "fichier déjà présent — un incident à 1,8 Go du modèle "
                            "de langue ne repart pas de zéro"],
            ["**Nouvelles tentatives**", "3 par fichier, avec attente croissante"],
            ["**Délai d'inactivité**", "120 secondes"],
            ["**Intégrité**", "comparaison de la taille exacte ; un fichier trop "
                              "gros est supprimé et retéléchargé"],
            ["**Reprise après coupure**", "un fichier déjà à la bonne taille est ignoré"],
            ["**Repli**", "si la source primaire échoue *ou* si l'asset est absent"],
        ],
        widths=[2.0, 5.0],
    )
    d.note(
        "La source réellement utilisée est remontée à la fenêtre de progression. Le "
        "commentaire explique pourquoi : *« utile pour vérifier en entreprise que "
        "la source primaire passe bien et qu'on ne retombe pas silencieusement sur "
        "le repli »*."
    )

    d.h2("9.5 Les deux jetons")
    d.schema(SCH / "s20_jetons.png",
             "Schéma 20 — Séparation stricte des deux jetons et flux de publication")
    d.table(
        ["Jeton", "Droits", "Où il vit", "À quoi il sert"],
        [
            ["Lecture", "lecture seule",
             "**embarqué dans l'application**",
             "télécharger les mises à jour **et** les modèles"],
            ["Écriture", "lecture + écriture",
             "uniquement sur la machine de build",
             "créer la publication et téléverser les fichiers"],
        ],
        widths=[1.0, 1.4, 2.2, 2.4],
    )
    d.para(
        "Le point subtil : l'outil d'empaquetage est invoqué en mode « ne jamais "
        "publier ». Il ne contacte donc **jamais** le dépôt. Sa configuration de "
        "publication ne lui sert qu'à une chose — graver le jeton de lecture dans "
        "le fichier de mise à jour. La publication réelle est faite ensuite, "
        "séparément, avec le jeton d'écriture."
    )
    d.para(
        "C'est ce qui garantit que le jeton en écriture ne peut pas se retrouver "
        "dans le paquet distribué."
    )
    d.warning(
        "**Le jeton de lecture, lui, est extractible de l'application** — c'est "
        "inévitable puisqu'elle doit s'authentifier seule. Le risque est borné par "
        "ses droits : lecture seule, sur un seul dépôt, qui ne contient que des "
        "installeurs et des modèles publics par ailleurs. À savoir cependant : "
        "quiconque installe l'application peut lire ce dépôt."
    )

    d.h2("9.6 La publication")
    d.code("""1. compilation du backend        → exécutable figé
2. compilation de l'interface    → export statique
3. empaquetage (sans publier)    → installeur + fichier de version + carte de blocs
4. création ou réutilisation de la publication distante
5. envoi des trois artefacts, en remplaçant les homonymes""")
    d.para(
        "**L'opération est idempotente** : republier la même version réutilise la "
        "publication existante et remplace les artefacts, au lieu d'échouer ou de "
        "créer des doublons."
    )
    d.para(
        "Les trois artefacts sont indispensables — le fichier de version porte le "
        "numéro et l'empreinte, la carte de blocs permet les mises à jour "
        "différentielles, et l'installeur est le livrable."
    )

    d.h2("9.7 La mise à jour automatique")
    d.para(
        "Le mécanisme d'exécution est décrit en §7.8. Côté distribution, le "
        "fichier de configuration écrit dans l'application désigne le dépôt et "
        "porte le jeton de lecture."
    )
    d.para("Deux conditions sine qua non :")
    d.bullets([
        "**la version doit être incrémentée** — sans cela, aucun poste ne voit la "
        "nouveauté ;",
        "**les trois artefacts** doivent être présents sur la publication.",
    ])
    d.para(
        "Et une contrainte d'exécution : l'arrêt du backend et du serveur de modèle "
        "doit être **effectif** avant que l'installeur n'écrase les fichiers, sinon "
        "il reste bloqué sur un accès refusé (§7.3)."
    )

    d.h2("9.8 Les pièges du build")
    d.para(
        "Ils reviennent à chaque construction et ont tous la même cause : **le "
        "dossier de travail est synchronisé par OneDrive**."
    )
    d.table(
        ["Symptôme", "Correctif"],
        [
            ["La compilation de l'interface échoue sur son dossier de cache",
             "supprimer ce dossier à la main"],
            ["Le figeage du backend échoue sur un accès refusé",
             "supprimer les dossiers de sortie ; tuer les processus du backend et "
             "du serveur de modèle encore vivants"],
            ["L'empaquetage échoue sur le dossier de publication",
             "supprimer ce dossier"],
            ["Mise à jour figée sur le poste de test",
             "terminer l'application et ses processus fils dans le gestionnaire de "
             "tâches"],
        ],
        widths=[3.4, 3.6],
    )
    d.note(
        "**Procédure recommandée avant une publication** : suspendre la "
        "synchronisation OneDrive et supprimer les trois dossiers de sortie."
    )

    d.h2("9.9 Limites connues")
    d.bullets([
        "**Aucune signature de code** (§9.3) — l'avertissement de Windows apparaît "
        "à chaque installation.",
        "**Le jeton de lecture est distribué avec l'application** (§9.5) — "
        "inhérent au modèle ; les droits sont volontairement minimaux.",
        "**L'intégrité des modèles repose sur la taille seule** — aucune empreinte "
        "cryptographique n'est vérifiée. Un fichier corrompu qui conserverait la "
        "bonne taille passerait le contrôle. Le risque réel est faible — transport "
        "chiffré de bout en bout, source maîtrisée — mais une somme de contrôle "
        "serait plus solide, et le manifeste s'y prête déjà.",
        "**La liste des modules déclarés est une dette permanente** (§9.2) — tenue "
        "à la main, et son oubli ne se voit qu'à l'exécution.",
        "**Le build dépend d'un dossier synchronisé** (§9.8) — travailler hors du "
        "dossier OneDrive supprimerait toute cette catégorie de problèmes.",
    ])
    d.note(
        "**Un seul test automatisé existe dans tout le projet**, et il couvre la "
        "logique de repli du téléchargeur. C'est significatif : c'est justement la "
        "partie la plus exposée aux réseaux d'entreprise."
    )

    d.h2("9.10 Résumé pour une reprise")
    d.numbered([
        "L'installeur contient **le code, pas les modèles**. Les 2,3 Go sont "
        "téléchargés au premier lancement, ce qui découple la publication "
        "applicative des modèles.",
        "Le backend est figé avec **trois listes à tenir à la main**. Un oubli se "
        "voit à l'exécution, pas à la construction.",
        "Le téléchargeur utilise la **pile réseau du moteur de rendu** — c'est ce "
        "qui le fait fonctionner derrière un proxy d'entreprise, avec inspection "
        "SSL et redirection inter-domaines.",
        "Un dépôt privé **impose de passer par l'API** ; l'adresse de "
        "téléchargement de type navigateur échoue avec un jeton.",
        "Deux jetons strictement séparés : le **lecture seule** est embarqué, "
        "le **écriture** ne quitte jamais la machine de build. Le mode « ne jamais "
        "publier » de l'outil d'empaquetage garantit cette séparation.",
        "La **version** est la seule valeur à incrémenter pour publier.",
        "Presque tous les échecs de construction viennent de **la synchronisation "
        "du dossier de travail**.",
    ])
    d.note(
        "**Premier chantier si l'on veut fiabiliser le déploiement** — la signature "
        "de code (§9.3). C'est le seul point qui dégrade l'expérience de **tous** "
        "les utilisateurs, à chaque installation, et il ne se corrige pas dans le "
        "code."
    )


# ═════════════════════════════════════════════════════════════════════════════
#   10. Reprise du projet
# ═════════════════════════════════════════════════════════════════════════════
def section_10_reprise(d: YeleDoc) -> None:
    d.h1("10. Reprise du projet")

    d.para(
        "Ce chapitre est le mode d'emploi opérationnel : installer le projet sur "
        "une machine neuve, le lancer sans rien packager, produire l'installeur, "
        "publier une version, et savoir quels comptes externes créer ou "
        "transférer. Toutes les commandes sont à exécuter **depuis la racine du "
        "projet**, sauf mention contraire."
    )

    # ── 10.1 ─────────────────────────────────────────────────────────────────
    d.h2("10.1 Prérequis de la machine")
    d.table(
        ["Outil", "Version", "Sert à"],
        [
            ["Windows", "10 ou 11, 64 bits",
             "la captation du son système et l'empaquetage sont spécifiques à Windows"],
            ["Python", "3.10 ou plus", "le backend et toutes les briques de traitement"],
            ["Node.js", "20 ou plus", "l'interface et l'empaquetage Electron"],
            ["Git", "récent", "récupérer le dépôt et publier"],
        ],
        widths=[1.4, 1.8, 3.8],
    )
    d.note(
        "Le processeur suffit — aucune carte graphique n'est requise. En revanche "
        "la génération du compte rendu par le modèle local est longue sur une "
        "machine modeste : prévoir au moins 16 Go de mémoire vive pour un confort "
        "correct."
    )

    # ── 10.2 ─────────────────────────────────────────────────────────────────
    d.h2("10.2 Installation initiale")
    d.h4("1. Récupérer le dépôt et créer l'environnement Python")
    d.code("""git clone <adresse-du-dépôt> diarisation-final
cd diarisation-final

python -m venv meeting_assistant
& ".\\meeting_assistant\\Scripts\\Activate.ps1"

pip install -r requirements.txt          # dépendances d'exécution
pip install -r requirements-build.txt    # dépendances d'empaquetage""")
    d.h4("2. Installer les dépendances JavaScript")
    d.code("""cd webapp   ; npm install ; cd ..
cd electron ; npm install ; cd ..""")
    d.h4("3. Mettre en place les modèles pour le développement")
    d.para(
        "En développement, l'application **ne télécharge rien** : elle lit les "
        "modèles directement dans l'arborescence du projet. Les cinq emplacements "
        "suivants doivent donc être remplis à la main."
    )
    d.table(
        ["Emplacement attendu", "Contenu"],
        [
            ["`models/`", "le modèle de langue au format quantifié"],
            ["`sherpa-onnx-streaming-zipformer-fr-kroko/`",
             "les quatre fichiers du modèle de transcription"],
            ["`pretrained_models/resnet34/`", "le modèle d'empreinte vocale"],
            ["`bin/llama/`", "le serveur d'inférence et ses bibliothèques"],
            ["`assets/models_hf/all-MiniLM-L6-v2/`", "le modèle de découpage sémantique"],
        ],
        widths=[3.4, 3.6],
    )
    d.para(
        "Le dernier se récupère automatiquement — c'est le seul, et il faut une "
        "connexion :"
    )
    d.code("python scripts/prepare_assets.py")
    d.note(
        "Les quatre autres se récupèrent depuis la publication de modèles du dépôt "
        "de distribution (§10.4), ou depuis leurs sources d'origine listées dans le "
        "manifeste `electron/model_manifest.js`. Le manifeste donne pour chacun son "
        "nom, son adresse de repli et sa **taille exacte** — utile pour vérifier "
        "qu'un fichier est complet."
    )

    # ── 10.3 ─────────────────────────────────────────────────────────────────
    d.h2("10.3 Lancer en local, sans rien packager")
    d.para(
        "C'est le mode de travail quotidien. Trois variantes, de la plus légère à "
        "la plus complète."
    )

    d.h3("Variante A — le backend seul")
    d.para(
        "Utile pour tester les briques 1 à 4 sans interface : les endpoints "
        "répondent, et la documentation interactive est disponible."
    )
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"
python -m backend.run_app server

# puis, dans un autre terminal
curl http://127.0.0.1:8000/api/health
#   documentation interactive : http://127.0.0.1:8000/docs""")

    d.h3("Variante B — backend + interface dans un navigateur")
    d.para(
        "L'interface fonctionne dans un navigateur ordinaire : sa résolution "
        "d'adresse retombe sur le backend local. Ne fonctionnent pas dans ce "
        "mode : la recherche dans le compte rendu, les notifications natives et la "
        "barre des tâches — tout ce qui passe par Electron (§8.10)."
    )
    d.code("""# terminal 1
& ".\\meeting_assistant\\Scripts\\Activate.ps1"
python -m backend.run_app server

# terminal 2
cd webapp
npm run dev            # http://localhost:3000""")

    d.h3("Variante C — l'application complète, avec rechargement à chaud")
    d.para(
        "C'est le mode recommandé : Electron démarre le backend lui-même, injecte "
        "les chemins des modèles, et charge l'interface depuis le serveur de "
        "développement. Toute modification de l'interface est rechargée "
        "instantanément."
    )
    d.code("""# terminal 1 — interface
cd webapp
npm run dev

# terminal 2 — Electron + backend depuis les sources
& ".\\meeting_assistant\\Scripts\\Activate.ps1"
cd electron
npm run dev:hot""")
    d.table(
        ["Fichier modifié", "À faire"],
        [["`webapp/**`", "**rien** — rechargement automatique à la sauvegarde"],
         ["`backend/**`, `diar_pipeline/**`, `audio_capture/**`",
          "fermer et relancer le terminal 2"],
         ["`electron/main.js`, `electron/preload.js`", "fermer et relancer le terminal 2"]],
        widths=[2.8, 4.2],
    )
    d.note(
        "Une variante sans rechargement à chaud existe : compiler l'interface une "
        "fois (`npm run build` dans `webapp/`) puis lancer `npm run dev` dans "
        "`electron/`. Electron charge alors l'export statique depuis le disque, "
        "comme en production."
    )
    d.para(
        "Si l'interpréteur Python du projet n'est pas celui du système, le désigner "
        "par la variable d'environnement `PYTHON_BIN` avant de lancer Electron."
    )

    # ── 10.4 ─────────────────────────────────────────────────────────────────
    d.h2("10.4 Comptes externes, clés et jetons")
    d.schema(SCH / "s21_comptes.png",
             "Schéma 21 — Les trois dépendances externes et l'emplacement des secrets")

    d.h3("GitHub — un dépôt privé, deux usages, deux jetons")
    d.para(
        "Un **seul dépôt privé** sert à la fois à distribuer les versions de "
        "l'application et à héberger les modèles."
    )
    d.table(
        ["Contenu", "Repéré par", "Consommé par"],
        [
            ["installeurs, fichier de version, carte de blocs",
             "une étiquette par version", "la mise à jour automatique"],
            ["fichiers de modèles",
             "une étiquette fixe et unique", "le téléchargeur au premier lancement"],
        ],
        widths=[3.0, 2.0, 2.0],
    )
    d.h4("Créer les deux jetons")
    d.para(
        "Dans les paramètres développeur du compte GitHub, créer **deux jetons "
        "d'accès personnels à portée restreinte**, tous deux limités à ce seul "
        "dépôt :"
    )
    d.table(
        ["Jeton", "Permission", "Rôle"],
        [
            ["Lecture", "contenu du dépôt — **lecture seule**",
             "sera **embarqué dans l'application** : il télécharge les mises à "
             "jour et les modèles"],
            ["Écriture", "contenu du dépôt — **lecture et écriture**",
             "sert **uniquement à publier** ; ne quitte jamais la machine de build"],
        ],
        widths=[1.2, 2.4, 3.4],
    )
    d.para("Les coller dans un fichier `electron/.env`, déjà exclu du versionnement :")
    d.code("""GH_READ_TOKEN=<le jeton en lecture seule>
GH_TOKEN=<le jeton en écriture>""")
    d.warning(
        "Le jeton de lecture est **gravé dans l'application distribuée** : c'est "
        "inévitable, puisqu'elle doit s'authentifier seule pour télécharger. Le "
        "limiter à la lecture seule sur un seul dépôt est donc essentiel — ne "
        "jamais y mettre le jeton d'écriture."
    )
    d.h4("Créer la publication des modèles")
    d.para(
        "Une seule fois : créer dans ce dépôt une publication portant l'étiquette "
        "fixe attendue par le manifeste, et y téléverser les fichiers de modèles "
        "sous les noms exacts que le manifeste déclare. Le manifeste ne stocke que "
        "ces **noms** — un nom qui ne correspond pas fait basculer silencieusement "
        "sur la source de repli."
    )

    d.h3("Microsoft — l'accès au calendrier")
    d.para(
        "L'intégration de l'agenda suppose une **inscription d'application** dans "
        "l'annuaire de l'organisation. Trois réglages suffisent :"
    )
    d.numbered([
        "déclarer l'application comme **client public** — aucun secret à créer, "
        "et donc rien d'extractible du binaire ;",
        "ajouter la permission **déléguée** de lecture du calendrier — déléguée, "
        "donc chaque salarié ne voit que son propre agenda ;",
        "autoriser explicitement les **flux de client public**, faute de quoi le "
        "flux par code d'appareil est refusé par le service.",
    ])
    d.para(
        "L'identifiant d'application et celui de l'organisation sont inscrits en "
        "dur dans `backend/graph_calendar.py`, avec une surcharge possible par les "
        "variables d'environnement `GRAPH_CLIENT_ID` et `GRAPH_TENANT_ID`. Pour "
        "reprendre le projet dans une autre organisation, ce sont **les deux "
        "seules valeurs à changer**."
    )

    d.h3("Mistral — le moteur de compte rendu alternatif")
    d.para(
        "**Aucune configuration côté build.** La clé est saisie par chaque "
        "utilisateur dans les paramètres de l'application, et stockée sur son "
        "poste. Sans clé, le sélecteur de moteur reste sur le moteur local, qui ne "
        "dépend d'aucun service externe."
    )
    d.para(
        "Pour les scripts d'évaluation lancés en développement, une clé peut être "
        "placée dans un fichier `.env` à la racine, également exclu du "
        "versionnement :"
    )
    d.code("MISTRAL_API_KEY=<la clé>")

    # ── 10.5 ─────────────────────────────────────────────────────────────────
    d.h2("10.5 Packager le backend seul")
    d.para(
        "Étape indépendante, utile pour vérifier que le figeage passe avant de "
        "lancer l'empaquetage complet."
    )
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"
pyinstaller build/backend.spec --noconfirm --clean""")
    d.para("Résultat : un dossier `dist/backend/` contenant l'exécutable et ses dépendances.")
    d.h4("Le tester avant d'aller plus loin")
    d.para(
        "L'exécutable figé attend les mêmes variables d'environnement que celles "
        "qu'Electron lui injecte. Les poser à la main permet de le lancer seul :"
    )
    d.code("""$env:MODELS_DIR      = "$PWD\\models"
$env:SHERPA_DIR      = "$PWD\\sherpa-onnx-streaming-zipformer-fr-kroko"
$env:PRETRAINED_DIR  = "$PWD\\pretrained_models"
$env:LLAMA_BIN_DIR   = "$PWD\\bin\\llama"
$env:MINILM_DIR      = "$PWD\\assets\\models_hf\\all-MiniLM-L6-v2"

dist\\backend\\backend.exe server

# dans un autre terminal
curl http://127.0.0.1:8000/api/health""")
    d.warning(
        "**Si l'exécutable s'arrête immédiatement**, le lancer dans une console "
        "pour lire l'erreur : un module manquant se manifeste par une erreur "
        "d'import. Il faut alors l'ajouter à la liste des modules déclarés dans "
        "`build/backend.spec` et reconstruire (§9.2). C'est le défaut le plus "
        "fréquent, et il ne se voit **pas** à la construction."
    )

    # ── 10.6 ─────────────────────────────────────────────────────────────────
    d.h2("10.6 Packager l'application complète")
    d.para(
        "Les scripts d'empaquetage sont déclarés dans `electron/package.json` et "
        "s'exécutent **depuis le dossier `electron/`**."
    )
    d.table(
        ["Commande", "Ce qu'elle fait"],
        [
            ["`npm run build:python`", "fige le backend"],
            ["`npm run build:webapp`", "compile l'interface en export statique"],
            ["`npm run build:assets`", "récupère le modèle de découpage sémantique"],
            ["`npm run build:all`", "les deux premières, enchaînées"],
            ["`npm run dist`", "produit l'installeur à partir de ce qui est déjà compilé"],
            ["`npm run build:local`", "**tout compiler et produire l'installeur**, sans publier"],
            ["`npm run publish`", "**tout compiler, produire l'installeur et publier**"],
        ],
        widths=[2.2, 4.8],
    )
    d.h4("Avant chaque construction")
    d.numbered([
        "**Suspendre la synchronisation** du dossier de travail — c'est la cause "
        "de la quasi-totalité des échecs (§9.8).",
        "**Supprimer les dossiers de sortie** : le dossier de distribution du "
        "backend, celui de l'installeur, et le cache de compilation de l'interface.",
        "**Vérifier qu'aucun processus de l'application ne tourne encore** — un "
        "backend ou un serveur de modèle resté vivant verrouille les fichiers.",
    ])
    d.para(
        "Résultat : un installeur dans le dossier de publication, accompagné du "
        "fichier de version et de la carte de blocs."
    )

    # ── 10.7 ─────────────────────────────────────────────────────────────────
    d.h2("10.7 Publier une version")
    d.h4("1. Incrémenter la version")
    d.para(
        "Modifier le champ de version dans `electron/package.json`. **C'est la "
        "seule valeur à changer**, et elle est obligatoire : la mise à jour "
        "automatique ne se déclenche que si la version publiée est strictement "
        "supérieure à celle installée."
    )
    d.table(
        ["Nature du changement", "Incrément"],
        [["correctif", "le dernier chiffre"],
         ["nouvelle fonctionnalité", "le chiffre du milieu"],
         ["tant que l'usage reste interne", "garder le premier chiffre à zéro"]],
        widths=[3.5, 3.5],
    )
    d.h4("2. Vérifier les jetons")
    d.para(
        "Le fichier `electron/.env` doit contenir les deux jetons (§10.4). Le "
        "script s'arrête immédiatement si l'un manque."
    )
    d.h4("3. Construire et publier")
    d.code("""& ".\\meeting_assistant\\Scripts\\Activate.ps1"
cd electron
npm run publish""")
    d.para(
        "L'opération dure de cinq à quinze minutes, le figeage du backend étant "
        "l'étape la plus longue. Elle est **idempotente** : republier la même "
        "version réutilise la publication existante et remplace les artefacts."
    )
    d.h4("4. Vérifier")
    d.bullets([
        "Sur le dépôt : la publication doit apparaître avec ses **trois** "
        "artefacts — installeur, fichier de version, carte de blocs. Il en manque "
        "un et la mise à jour automatique ne fonctionnera pas.",
        "Sur un poste de test : relancer l'application **déjà installée** — pas "
        "l'installeur. Une boîte de dialogue doit proposer le redémarrage au bout "
        "de quelques secondes.",
    ])
    d.warning(
        "Si la mise à jour se fige sur le poste de test, terminer l'application et "
        "ses processus fils dans le gestionnaire de tâches : l'installeur reste "
        "bloqué tant que le backend ou le serveur de modèle tiennent les fichiers "
        "(§7.3)."
    )

    # ── 10.8 ─────────────────────────────────────────────────────────────────
    d.h2("10.8 Reprendre le projet dans une autre organisation")
    d.para("Sept points à reprendre, dans cet ordre.")
    d.table(
        ["#", "Point", "Où"],
        [
            ["1", "créer le dépôt privé de distribution et ses deux jetons",
             "compte GitHub de la nouvelle organisation"],
            ["2", "mettre à jour le propriétaire et le nom du dépôt",
             "`electron/build-app.js` et `electron/model_manifest.js`"],
            ["3", "créer la publication des modèles et y téléverser les fichiers",
             "sous les noms exacts du manifeste"],
            ["4", "créer l'inscription d'application pour le calendrier",
             "annuaire de la nouvelle organisation"],
            ["5", "remplacer l'identifiant d'application et celui de l'organisation",
             "`backend/graph_calendar.py`"],
            ["6", "changer l'identifiant d'application, le nom de produit et le "
                  "détenteur des droits", "`electron/package.json`"],
            ["7", "acquérir un certificat de signature de code",
             "supprime l'avertissement à l'installation (§9.3)"],
        ],
        widths=[0.5, 3.5, 3.0],
    )
    d.note(
        "Rien d'autre n'est spécifique à l'organisation : les modèles sont publics "
        "ou librement redistribuables, le moteur de compte rendu par défaut est "
        "local, et aucun service tiers n'est appelé pendant le traitement."
    )

    # ── 10.9 ─────────────────────────────────────────────────────────────────
    d.h2("10.9 Référence rapide des commandes")
    d.table(
        ["Besoin", "Commande", "Depuis"],
        [
            ["Backend seul", "`python -m backend.run_app server`", "racine"],
            ["Diarisation sur un fichier",
             "`python -m diar_pipeline.run -i AUDIO -o DOSSIER`", "racine"],
            ["Normaliser un transcript",
             "`python -m backend.run_app normalize IN.txt OUT.txt`", "racine"],
            ["Compte rendu local",
             "`python -m backend.run_app minutes --transcript T --output R.md`", "racine"],
            ["Compte rendu Mistral",
             "`python -m backend.run_app mistral-minutes --transcript T --output R.md`",
             "racine"],
            ["Interface seule", "`npm run dev`", "`webapp/`"],
            ["Application complète, rechargement à chaud", "`npm run dev:hot`", "`electron/`"],
            ["Figer le backend",
             "`pyinstaller build/backend.spec --noconfirm --clean`", "racine"],
            ["Compiler l'interface", "`npm run build`", "`webapp/`"],
            ["Installeur sans publier", "`npm run build:local`", "`electron/`"],
            ["Installeur **et** publication", "`npm run publish`", "`electron/`"],
            ["Récupérer le modèle de découpage",
             "`python scripts/prepare_assets.py`", "racine"],
            ["Régénérer cette documentation",
             "`python docs/generate_doc_technique.py`", "racine"],
        ],
        widths=[2.4, 3.6, 1.0],
    )

    d.h2("10.10 Où trouver quoi dans le dépôt")
    d.table(
        ["Chemin", "Contenu"],
        [
            ["`diar_pipeline/`", "brique 1 — diarisation et transcription"],
            ["`audio_capture/`", "brique 2 — captation et pipeline temps réel"],
            ["`meeting_minutes_pipeline.py`, `mistral_minutes.py`, "
             "`normalize_transcript.py`", "brique 3 — génération du compte rendu"],
            ["`backend/`", "brique 4 — API, calendrier, journalisation"],
            ["`electron/`", "briques 5 et 7 — shell, empaquetage, publication"],
            ["`webapp/`", "brique 6 — interface"],
            ["`build/backend.spec`", "configuration du figeage du backend"],
            ["`scripts/`", "préparation des modèles"],
            ["`docs/`", "cette documentation et son générateur"],
            ["`_bench_*`, `mlruns/`, `mlflow.db`",
             "travaux d'évaluation — **hors du produit livré**"],
        ],
        widths=[3.0, 4.0],
    )
    d.note(
        "Le dépôt contient aussi des travaux d'expérimentation non livrés — "
        "scripts d'évaluation, moteurs alternatifs, suivi d'expériences. Ils ne "
        "sont documentés dans aucun chapitre : ils ne tournent pas dans "
        "l'application. En cas de doute sur un fichier, vérifier s'il est suivi par "
        "le gestionnaire de versions — c'est le critère qui distingue le produit du "
        "banc d'essai."
    )


# ═════════════════════════════════════════════════════════════════════════════
SECTIONS = [
    section_1_vue_ensemble,
    section_2_architecture,
    section_3_diarisation,
    section_4_captation,
    section_5_compte_rendu,
    section_6_backend,
    section_7_electron,
    section_8_frontend,
    section_9_build,
    section_10_reprise,
]


def build(out: str | Path | None = None) -> str:
    print("[doc] génération des schémas…")
    for name, fn in S.ALL.items():
        fn()

    print("[doc] assemblage du document…")
    d = YeleDoc("Documentation Technique — Meeting Assistant")
    for i, sec in enumerate(SECTIONS):
        if i:
            d.page_break()
        sec(d)

    out = Path(out or HERE / "Documentation_Technique_Meeting_Assistant.docx")
    d.save(str(out))
    print(f"[doc] écrit → {out}")
    return str(out)


if __name__ == "__main__":
    build()
