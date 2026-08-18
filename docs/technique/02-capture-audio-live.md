# Brique 2 — Capture audio & pipeline temps réel

**Package :** `audio_capture/` — [recorder.py](../../audio_capture/recorder.py)
(720 l.) et [live_processor.py](../../audio_capture/live_processor.py) (620 l.)
**Rôle :** capter le son de la réunion et produire le transcript **pendant**
qu'elle se déroule.

> **Périmètre.** Ce document couvre la captation audio et la production du
> transcript en temps réel. Le dossier contient aussi `live_llm.py` — le
> compte rendu progressif produit pendant la réunion, dont le sujet est le
> LLM. Il est traité dans la brique *Génération de compte rendu* ; ici on se
> limite au **point de branchement** vers lui (§7).

---

## 1. Rôle de la brique

C'est le chemin normal quand l'utilisateur clique sur « Enregistrer » dans
l'application. Deux choses se passent **simultanément** :

```
      🎙 micro  ────┐
                     ├──► mixage ──┬──► accumulation ──► audio.wav   (à la fin)
      🔊 système ───┘               │
                                    └──► LiveProcessor ──► transcript.txt
                                          (pendant la réunion)
```

Au moment où l'utilisateur clique sur Stop, **le transcript est déjà
quasiment terminé**. C'est toute la raison d'être de cette brique : un compte
rendu disponible quelques secondes après la fin d'une réunion d'une heure, au
lieu des minutes de diarisation batch qu'exigerait le même fichier uploadé
(brique 1, §8.1).

---

## 2. Les trois issues possibles

L'endpoint `POST /api/record/stop` peut se terminer de trois façons :

| Issue | Condition | Conséquence |
|---|---|---|
| **Succès live** | `finalize()` a écrit `transcript.txt` | brique 1 **court-circuitée**, on enchaîne sur normalisation + compte rendu |
| **Succès live + LLM** | le LLM live a aussi produit `compte_rendu.md` | job marqué `done` immédiatement — l'utilisateur n'a rien à lancer |
| **Échec live** | `finalize()` renvoie `False`, rien n'est écrit | **repli sur la brique 1**, en mode `--bootstrap-online` |

Le mécanisme de repli est délibérément binaire : le `LiveProcessor` **n'écrit
rien du tout** en cas de problème, plutôt que d'écrire un transcript partiel.
C'est ce qui permet au backend de décider par simple test d'existence du
fichier ([backend/main.py:607](../../backend/main.py#L607)).

Un fichier marqueur `.origin.recording` est déposé dans le dossier de la
réunion ([main.py:1352](../../backend/main.py#L1352)). Il sert à se souvenir,
même après un redémarrage de l'application, que ce dossier vient d'un
enregistrement — et donc qu'en cas de repli il faut lancer la brique 1 avec
`--bootstrap-online`.

---

## 3. Architecture — qui tourne en parallèle de quoi

Sept threads coexistent pendant une captation.

```
 POST /api/record/start
   │
   ├─► AudioRecorder.start()                         recorder.py:122
   │     │
   │     ├─ [T1] _record_loop  ─ ouvre le flux micro (WASAPI shared)
   │     │        └─ mic_callback : accumule + calcule le niveau RMS
   │     ├─ [T2] _loopback_worker ─ capture le son système
   │     └─ [T3] _live_mix_worker ─ mixe mic+système en continu (ducking)
   │                                 puis appelle on_chunk(mixed)
   │                                            │
   │                                            ▼
   └─► LiveProcessor.start()  (thread de fond)  push(chunk)
         │                                       │
         │                          ┌────────────┴────────────┐
         │                          ▼                          ▼
         │                     _asr_q                     _embed_q
         │                   (max 15 000)               (max 15 000)
         │                          │                          │
         ├─ [T4] _asr_worker ◄──────┘                          │
         │        sherpa-onnx streaming, num_threads=2         │
         │        poll des mots toutes les 2 s                 │
         │                                                      │
         ├─ [T5] _embed_worker ◄───────────────────────────────┘
         │        fenêtre 1,2 s / hop 0,6 s
         │        VAD silero → embedding resnet34
         │        └─► BootstrapOnlineClusterer.add()
         │
         └─ [T6] _turn_dispatch_worker   (si LLM live — activé par l'app)
                  drain TurnBuilder → chunker → LLM           → brique 3

 POST /api/record/stop
   └─► finalize() : join des workers, clustering final,
                    alignement mots ↔ locuteurs, écriture transcript.txt
```

### Le démarrage différé — un point de conception important

`record_start` lance le recorder **immédiatement**, mais `LiveProcessor.start()`
part dans un thread de fond ([main.py:1294](../../backend/main.py#L1294)). La
réponse HTTP revient tout de suite.

Pourquoi : charger les modèles (resnet34, silero, sherpa) prend **15 à 20
secondes**. Si on attendait, on perdrait les 20 premières secondes de la
réunion — souvent le moment où l'on annonce l'ordre du jour.

La solution : `self._running = True` **dès la construction** de l'objet, donc
`push()` accepte les chunks avant même que les workers existent. Ils s'empilent
dans les files, et les workers les rattrapent au démarrage. Le log l'annonce
explicitement : *« La file contient N chunks audio en attente. »*

> ⚠ **Les files sont bornées à 15 000 éléments**
> ([live_processor.py:56](../../audio_capture/live_processor.py#L56)). Au-delà,
> `put_nowait` lève `queue.Full` et le chunk est **silencieusement perdu** —
> le `except queue.Full: pass` de `push()` ne journalise rien. Le commentaire
> juste au-dessus (« Ne devrait pas arriver avec une queue non bornée ») est
> périmé : la file *est* bornée. Tant que les workers tiennent le temps réel, le
> cas ne se produit pas ; s'ils décrochent durablement, l'audio est perdu sans
> aucun signal.

---

## 4. La captation — `recorder.py`

### 4.1 Deux sources simultanées

| Source | Bibliothèque | Ce qu'elle capte |
|---|---|---|
| **Microphone** | `sounddevice`, WASAPI **shared mode** | la voix des personnes présentes dans la pièce |
| **Sortie système** (loopback) | `pyaudiowpatch` | la voix des participants distants (Teams, Zoom…) |

Le mode **shared** du micro n'est pas un détail : en mode exclusif, l'ouverture
du flux prendrait la main sur le périphérique et **empêcherait Teams ou Zoom de
l'utiliser**. On ne peut pas enregistrer une visio dont on a volé le micro.

Format commun : **16 kHz, mono, float32** — celui qu'attendent les modèles de
la brique 1.

### 4.2 Détection du loopback — trois niveaux de repli

`_find_loopback_device()` ([recorder.py:313](../../audio_capture/recorder.py#L313))
essaie dans l'ordre :

1. **`pyaudiowpatch`** — énumère les périphériques WASAPI marqués
   `isLoopbackDevice`, et cherche celui qui correspond au **haut-parleur par
   défaut** de Windows (comparaison de noms, après retrait du suffixe
   `[Loopback]`). À défaut, prend le premier loopback trouvé.
2. **`soundcard`** — `sc.get_microphone(spk.id, include_loopback=True)`.
3. **« Stereo Mix »** — cherche un périphérique d'entrée dont le nom contient
   `stereo mix`, `mixage stéréo` ou `what u hear`. Ce périphérique est
   **désactivé par défaut** sur Windows moderne ; c'est un repli historique.

Si les trois échouent : **micro seul**, sans erreur. L'enregistrement d'une
visio se réduit alors à ce que le micro capte des haut-parleurs, ce qui
fonctionne mal en casque. L'état est exposé par la propriété `has_loopback`.

### 4.3 Le ducking — pourquoi une simple addition ne marche pas

Si l'utilisateur est sur les **haut-parleurs de son portable** et non au casque,
la voix du participant distant est captée **deux fois** :

- **numériquement**, propre, par le loopback ;
- **acoustiquement**, dégradée et légèrement décalée, par le micro.

Les additionner produit une voix doublée, avec un effet d'écho — désastreux pour
l'ASR et pour la diarisation, qui verrait deux locuteurs là où il n'y en a qu'un.

`_mix_with_ducking()` ([recorder.py:522](../../audio_capture/recorder.py#L522))
décide **fenêtre par fenêtre** (120 ms) :

| Situation | Décision |
|---|---|
| loopback silencieux (`RMS ≤ 0.015`) | micro à gain normal **0,8** — l'utilisateur parle |
| loopback actif **et** micro plus faible que `1,6 × loopback` | micro **étouffé à 0,08** — ce que le micro capte n'est que la fuite acoustique |
| loopback actif **et** micro nettement plus fort | micro à gain normal — l'utilisateur parle **par-dessus** le distant |

Le loopback garde toujours un gain de **0,9**. Le gain du micro est lissé d'une
fenêtre à l'autre (`smoothing = 0.25`) pour éviter les clics audibles à chaque
changement de décision.

### 4.4 Deux mixages, pas un seul

C'est le point le plus subtil de la brique : le même signal est mixé **deux
fois, par deux codes différents**.

| | Mixage **offline** | Mixage **live** |
|---|---|---|
| Fonction | `_mix_with_ducking` | `_live_mix_worker` |
| Quand | à l'arrêt, en une passe | en continu, toutes les 50 ms |
| Destination | `audio.wav` (le fichier conservé) | `on_chunk()` → LiveProcessor |
| Ducking | par fenêtres de 120 ms | par bloc reçu, gain reporté d'un bloc à l'autre |

Les paramètres de ducking sont **dupliqués** dans les deux fonctions (`0.015`,
`0.8`, `0.08`, `1.6`, `0.9`, `0.25`). Modifier l'un sans l'autre fait diverger
le fichier audio du transcript.

> ⚠ **Les deux mixages ne recalent pas les flux de la même façon.** Le micro et
> le loopback ne démarrent pas au même instant (le thread loopback est lancé
> avant l'ouverture du flux micro). L'écart est mesuré sur les horodatages
> `_mic_first_chunk_time` / `_lb_first_chunk_time`, puis :
>
> - **offline** : le flux en retard est **complété par des zéros** au début
>   ([recorder.py:291](../../audio_capture/recorder.py#L291)) ;
> - **live** : le flux en avance est **rogné** de son surplus
>   ([recorder.py:638](../../audio_capture/recorder.py#L638)).
>
> Les deux opérations alignent bien le micro sur le loopback, mais **ne
> conservent pas la même origine des temps** : compléter par des zéros préserve
> le début du flux le plus précoce, rogner le supprime. L'origine de la
> timeline live et celle de `audio.wav` diffèrent donc de l'écart entre les
> deux premiers chunks.
>
> **Conséquence à vérifier :** `turns.json` sert à surligner le transcript en
> synchronisation avec la lecture de `audio.wav`. Un décalage systématique s'y
> reporterait. L'ampleur dépend du temps d'ouverture du flux micro — a priori
> quelques centaines de millisecondes, mais **ce point n'a pas été mesuré**,
> seulement déduit du code. À confirmer sur un enregistrement réel avant de le
> traiter comme un défaut.

### 4.5 Robustesse du flux micro

Le flux micro est enveloppé dans une boucle de reconnexion : **5 tentatives**,
délai initial de 2 s avec un facteur 1,5 plafonné à 10 s
([recorder.py:234](../../audio_capture/recorder.py#L234)). Cas visé : un casque
Bluetooth qui se déconnecte, ou un changement de périphérique par défaut en
cours de réunion.

L'attente entre deux tentatives est **interruptible** — un `stop()` pendant la
reconnexion n'attend pas les 10 secondes.

> ⚠ Une reconnexion réussie reprend la capture, mais **le temps écoulé pendant
> la coupure n'est pas compensé** : les échantillons sont simplement
> concaténés. La timeline de l'enregistrement se contracte donc du temps de la
> coupure, ce qui désaligne tout ce qui suit par rapport aux horodatages réels.

### 4.6 Le fichier produit

`_save_wav()` écrit un WAV **16 kHz, mono, PCM 16 bits signé** dans un fichier
temporaire, après clipping à `[-1, 1]`. Le backend le déplace ensuite vers
`<dossier réunion>/audio.wav`.

---

## 5. Le pipeline live — `live_processor.py`

### 5.1 Chargement des modèles

`start()` précharge trois modèles et les **fait tourner à vide une fois**
(*warmup*) :

| Modèle | Warmup |
|---|---|
| `_EmbeddingExtractor("resnet34")` | un vecteur de zéros de 1,2 s |
| Silero VAD | `torch.zeros(512)` |
| sherpa-onnx | (chargé dans le worker ASR) |

Le warmup n'est pas décoratif : la première inférence ONNX déclenche des
allocations et des optimisations de graphe qui prennent 1 à 3 secondes. Sans
lui, les toutes premières fenêtres de parole seraient traitées trop lentement et
la file prendrait du retard dès le départ.

**Le VAD est optionnel.** S'il ne charge pas, le pipeline continue avec un repli
sur l'énergie du signal (`RMS > 0.01`) — dégradé mais fonctionnel
([live_processor.py:149](../../audio_capture/live_processor.py#L149)).

### 5.2 Le worker ASR

Même modèle et même configuration que la brique 1, à une exception près :

| | Batch (brique 1) | Live |
|---|---|---|
| `num_threads` | 4 | **2** — *« laisse du CPU aux autres workers »* |

La différence de fond est ailleurs : le worker **interroge le décodeur toutes
les 2 secondes** (`POLL_INTERVAL`) pour récupérer les mots déjà produits, au
lieu d'attendre la fin. C'est ce qui alimente le LLM live en temps réel.

À chaque poll, `rec.tokens(stream)` renvoie **la totalité** des tokens depuis le
début ; le worker compare à `prev_words_count` pour n'émettre que les nouveaux.
`self._asr_words` est donc **remplacé** à chaque poll, pas complété.

À l'arrêt, 0,5 s de silence est injecté pour faire sortir le dernier token —
même mécanisme qu'en batch.

### 5.3 Le worker embeddings — et sa différence majeure avec le batch

C'est ici que le live et le batch divergent vraiment.

**En batch (brique 1) :** le VAD découpe d'abord tout l'audio en zones de
parole, puis on pose une fenêtre glissante **à l'intérieur de chaque zone**.

**En live :** on ne peut pas attendre la fin pour segmenter. Le worker maintient
un tampon, y découpe une **grille fixe** de fenêtres de 1,2 s tous les 0,6 s, et
pour chacune demande simplement « y a-t-il de la parole là-dedans ? »

```python
while len(buffer) >= EMBED_WIN_SAMPLES:        # 1,2 s
    window = buffer[:EMBED_WIN_SAMPLES]
    if self._window_has_speech(window):        # VAD par blocs de 512
        emb = self._extractor.extract_from_array(window, SAMPLE_RATE)
        ...
        self._clusterer.add(emb)
    buffer = buffer[EMBED_HOP_SAMPLES:]        # 0,6 s
```

`_window_has_speech()` découpe la fenêtre en blocs de 512 échantillons (la
taille qu'attend Silero) et renvoie `True` **dès qu'un seul bloc** dépasse une
probabilité de 0,4.

> **Conséquence :** une fenêtre live peut contenir 0,2 s de parole et 1 s de
> silence, et produire quand même un embedding — de mauvaise qualité, puisque
> l'essentiel de la fenêtre ne porte pas de voix. Le batch, lui, ne place ses
> fenêtres qu'à l'intérieur de zones déjà identifiées comme parlées. **C'est
> exactement la source des embeddings bruités** qui a rendu nécessaire le
> *freeze* post-bootstrap du clusterer (brique 1, §4.5) : sans lui, ces
> embeddings ne ressemblaient à aucun centroïde et créaient des locuteurs
> fantômes en série.

En cas d'exception, le worker pose `self._error` — ce qui suffit à faire
échouer `finalize()` et donc à déclencher le repli batch.

### 5.4 Le clustering en continu

Chaque embedding est passé à `BootstrapOnlineClusterer.add()` (brique 1, §4.5) :

- **avant 1 000 embeddings** (≈ 10 min) : mis en tampon, `add()` renvoie `None` ;
- **au 1 000ᵉ** : NMESC se déclenche sur le lot, les centroïdes et le seuil
  automatique sont calculés, les labels sont attribués rétroactivement ;
- **ensuite** : chaque embedding est rattaché au centroïde le plus proche, sans
  jamais créer de nouveau locuteur.

Le déclenchement est journalisé de façon très visible
([live_processor.py:540](../../audio_capture/live_processor.py#L540)) :
*« 🎯 Bootstrap diarisation déclenché ! NMESC sur N embeddings → K locuteurs
détectés, seuil online calibré à X. »* C'est le premier log à chercher pour
diagnostiquer un problème de locuteurs.

**Avant ce déclenchement, aucun mot n'a de vrai locuteur.** `_speaker_at_time()`
renvoie le littéral `SPEAKER_?`. Ce n'est visible que du LLM live, qui consomme
les tours de parole au fil de l'eau — le transcript final, lui, est réétiqueté
entièrement à la fin.

### 5.5 `finalize()` — l'assemblage

Appelé par `POST /api/record/stop`. Séquence
([live_processor.py:251](../../audio_capture/live_processor.py#L251)) :

1. `self._running = False`, puis une sentinelle `None` dans chaque file pour
   débloquer les workers en attente ;
2. `join(timeout=60)` sur les trois threads ;
3. si `self._error` est posé → **retourne `False`**, rien n'est écrit ;
4. si le LLM live est actif : on le finalise **d'abord** (brique 3) ;
5. `clusterer.finalize()` — force le bootstrap si la réunion a duré moins de
   10 minutes et que le seuil n'a jamais été atteint ;
6. `_build_segments(labels)` — fusionne les embeddings consécutifs de même
   locuteur, avec une tolérance de 0,1 s entre fenêtres ;
7. `align_words_to_speakers()` puis `words_to_turns()` — **exactement les
   fonctions de la brique 1** ;
8. écriture de `transcript.txt`, `words.json`, `turns.json`.

Deux garde-fous notables : un désalignement entre le nombre de labels et le
nombre d'embeddings est **tronqué** plutôt que de faire échouer le job
([live_processor.py:305](../../audio_capture/live_processor.py#L305)) ; et
l'absence totale de segment renvoie `False` (aucune parole détectée) plutôt que
d'écrire un transcript vide.

---

## 6. Ce qui est partagé avec la brique 1 — et ce qui ne l'est pas

| Élément | Batch | Live | Partagé ? |
|---|---|---|---|
| Modèle ASR | sherpa Zipformer FR | idem | ✅ même modèle, `num_threads` différent |
| Reconstruction des mots | `_tokens_to_words` | `_tokens_to_words` | ✅ même fonction |
| Modèle d'embedding | resnet34 via `_EmbeddingExtractor` | idem | ✅ même classe |
| Méthode d'extraction | `extract()` (fichier temporaire par fenêtre) | `extract_from_array()` (in-memory) | ❌ chemins différents |
| VAD | `run_vad()` sur tout le fichier | modèle Silero appelé par fenêtre | ❌ **réimplémenté** |
| Fenêtrage | à l'intérieur des zones de parole | grille fixe sur le flux | ❌ **logique différente** |
| Clustering | NMESC batch, ou `cluster_speakers_bootstrap_online` | `BootstrapOnlineClusterer` (stateful) | ⚠️ même algorithme, deux implémentations |
| Construction des segments | `build_segments()` | `_build_segments()` local | ❌ **réimplémenté** |
| Alignement mots ↔ locuteurs | `align_words_to_speakers` | idem | ✅ même fonction |
| Format de sortie | `format_transcript_txt` | idem | ✅ même fonction |

> ⚠ **Trois éléments sont réimplémentés** (VAD, fenêtrage, segments) et deux
> partagent un algorithme via deux implémentations distinctes. Aucun test ne
> vérifie qu'ils restent cohérents. Une correction appliquée d'un seul côté
> produit deux transcripts différents pour le même audio, selon qu'il a été
> enregistré ou uploadé.

---

## 7. Point de branchement vers le LLM live

Un seul crochet, piloté par le champ `enableLiveLlm` du payload de
`record/start`. Il relève de la brique *Génération de compte rendu*.

Techniquement optionnel, il est en pratique **toujours activé** : les trois
points d'entrée qui démarrent un enregistrement — le bouton du panneau
principal, la fenêtre de la barre des tâches, et le raccourci Electron —
envoient tous `enableLiveLlm: true`.

Sous cette condition unique, `start()` instancie trois objets d'un bloc
([live_processor.py:140](../../audio_capture/live_processor.py#L140)) :

| Objet | Rôle |
|---|---|
| `TurnBuilder` | assemble les mots décodés en tours de parole, au fil de l'eau |
| `StreamingTopicChunker` | détecte les ruptures de sujet (embeddings MiniLM) et ferme des chunks thématiques |
| `LiveLLMWorker` | extrait chaque chunk fermé via le **llama-server local** (Ministral 3B) |

Si l'un d'eux échoue à s'initialiser, les trois sont remis à `None` et la
captation continue **sans compte rendu progressif** — la transcription et la
diarisation live, elles, ne dépendent de rien de tout cela et restent toujours
actives. C'est le cœur de cette brique et il est volontairement léger.

Le worker `_turn_dispatch_worker` [T6] n'est lancé que si le `TurnBuilder`
existe. Le reste du pipeline live l'ignore complètement.

---

## 8. Configuration

Constantes en tête de
[live_processor.py:38-44](../../audio_capture/live_processor.py#L38) :

```python
SAMPLE_RATE        = 16_000
EMBED_WIN_S        = 1.2      # fenêtre d'embedding — identique au batch
EMBED_HOP_S        = 0.6      # pas — identique au batch
VAD_CHUNK_SAMPLES  = 512      # taille de bloc exigée par Silero
BOOTSTRAP_SIZE     = 1000     # ≈ 10 min à un pas de 0,6 s
```

Dans [recorder.py:29](../../audio_capture/recorder.py#L29) :

```python
SAMPLE_RATE = 16_000
BLOCK_SIZE  = 1_024           # taille de bloc du flux micro
```

Ducking (dupliqué dans les deux fonctions de mixage, §4.4) : `lb_active_rms =
0.015`, `mic_gain_normal = 0.8`, `mic_gain_ducked = 0.08`,
`user_over_remote_ratio = 1.6`, `lb_gain = 0.9`, `smoothing = 0.25`.

Rien n'est exposé dans l'interface : tout ajustement passe par le code.

---

## 9. API et fichiers produits

| Endpoint | Rôle |
|---|---|
| `POST /api/record/start` | démarre captation + pipeline live. Payload optionnel : `calendar`, `enableLiveLlm`, `participants`, `entreprises`, `contexte` |
| `POST /api/record/stop` | arrête, assemble, crée le job |
| `GET /api/record/status` | resynchronise l'interface (bouton, chronomètre) si l'utilisateur a changé de page |
| `POST /api/record/cancel` | réinitialise un enregistrement fantôme (backend coincé après un stop raté) |

Un seul enregistrement à la fois : `recorder` et `live_processor` sont des
variables **globales** du module backend. `record/start` réinitialise
automatiquement un état précédent resté coincé plutôt que de renvoyer une
erreur.

Fichiers écrits dans le dossier de la réunion :

| Fichier | Écrit par | Consommé par |
|---|---|---|
| `audio.wav` | `record/stop` (mixage offline) | lecteur audio de l'app, et brique 1 en cas de repli |
| `transcript.txt` | `LiveProcessor.finalize()` | ✅ **normalisation → compte rendu**, et signal de court-circuit |
| `turns.json` | idem | ✅ vue Transcript synchronisée à l'audio |
| `words.json` | idem | débogage |
| `.origin.recording` | `record/stop` | mémorise l'origine pour le repli batch |
| `.calendar_event.json` | `record/stop`, si réunion liée | rattachement à l'agenda |

---

## 10. Limites et pièges

### 10.1 Pas de loopback = visio inexploitable

Si les trois méthodes de détection échouent, l'enregistrement se poursuit **sans
erreur visible**, en micro seul. Sur une visio au casque, les participants
distants sont alors totalement absents du transcript. `has_loopback` expose
l'information, mais rien ne l'impose à l'utilisateur.

### 10.2 Origine des temps entre `audio.wav` et le transcript

Voir §4.4. Point déduit du code, **non mesuré** — à confirmer avant d'agir.

### 10.3 Perte silencieuse d'audio si les files saturent

Voir §3. Aucune journalisation quand un chunk est abandonné.

### 10.4 Coût de `_speaker_at_time`

[live_processor.py:444](../../audio_capture/live_processor.py#L444) fait un
**parcours linéaire complet** de tous les embeddings pour chaque mot, à chaque
poll de 2 secondes. Le commentaire annonce une « recherche dichotomique
grossière » ; le code est une boucle `for` exhaustive. Le coût croît avec le
carré de la durée de la réunion.

Comme l'application active toujours le LLM live, cette fonction tourne à chaque
captation — l'atténuation théorique (« elle n'est appelée que si le LLM live est
actif ») ne joue jamais en pratique.

### 10.5 Paramètres de ducking dupliqués

Voir §4.4. Six constantes présentes en double.

### 10.6 Perte de temps sur reconnexion micro

Voir §4.5. Une coupure contracte la timeline.

### 10.7 Le premier quart d'heure n'a pas de locuteurs

Tant que le bootstrap n'a pas eu lieu (1 000 embeddings ≈ 10 min de parole
effective), les tours de parole transmis au LLM live portent `SPEAKER_?`. Sans
effet sur le transcript final, qui est réétiqueté à la fin — mais le compte
rendu progressif est rédigé « à l'aveugle » sur qui dit quoi pendant toute la
première partie de la réunion.

### 10.8 Aucun test automatisé

Comme la brique 1. La vérification passe par une captation réelle et la lecture
des logs.

---

## 11. Vérifier une captation

Le pipeline se pilote par l'API, pas en ligne de commande. Backend lancé :

```powershell
# démarrer une captation simple (sans LLM live)
curl -X POST http://127.0.0.1:8000/api/record/start

# vérifier l'état
curl http://127.0.0.1:8000/api/record/status

# arrêter et déclencher l'assemblage
curl -X POST http://127.0.0.1:8000/api/record/stop
```

**Les logs à suivre, dans l'ordre :**

| Log | Signification |
|---|---|
| `Loopback pyaudiowpatch (défaut) : [i] <nom>` | ✅ le son système est capté |
| `Loopback non disponible — microphone seul` | ⚠️ visio inexploitable (§10.1) |
| `Micro ouvert en WASAPI shared mode (device=N)` | ✅ coexistence avec Teams/Zoom assurée |
| `[LIVE] ✓ Pipeline live prête en Xs — … La file contient N chunks en attente.` | ✅ workers démarrés ; `N` mesure le retard initial |
| `[LIVE][EMBED] N embeddings extraits, clusterer en bootstrap (N/1000)` | progression vers le bootstrap, toutes les 30 s |
| `[LIVE][DIAR] 🎯 Bootstrap diarisation déclenché !` | ✅ les locuteurs sont identifiés à partir d'ici |
| `[LIVE][ASR] N mots décodés, file audio = M chunks en attente` | ⚠️ si `M` **croît continûment**, l'ASR décroche du temps réel |
| `[LIVE][FINALIZE] ✓ transcript.txt écrit : N mots, N turns, K locuteurs` | ✅ mode live réussi |
| `Pas de transcript live — diar batch tournera au lancement` | ⚠️ repli déclenché |

**Points de contrôle :**

- Une file (`M`) qui grandit sans redescendre est le signal d'alerte principal :
  les workers ne tiennent pas le temps réel et l'audio finira par être perdu
  (§10.3).
- Un bootstrap qui ne se déclenche jamais sur une réunion de plus de 15 minutes
  indique que le VAD rejette presque tout — micro muet, ou mauvais périphérique.
- `K locuteurs` très supérieur au nombre réel de participants signalerait un
  *freeze* qui n'a pas joué son rôle ; très inférieur, un bootstrap fait pendant
  un monologue d'introduction.

---

## 12. Résumé pour une reprise

1. Deux sources captées en parallèle — micro (WASAPI **shared**, pour ne pas
   voler le périphérique à Teams) et son système (loopback WASAPI, avec deux
   niveaux de repli).
2. Le **ducking** est indispensable dès que l'utilisateur n'est pas au casque :
   sans lui, la voix du distant est doublée et la diarisation invente un
   locuteur.
3. Le même signal est mixé **deux fois par deux codes différents** — un pour le
   fichier, un pour le live — avec des paramètres dupliqués et un recalage
   temporel qui ne préserve pas la même origine des temps (§4.4).
4. Le recorder démarre **avant** que les modèles soient chargés ; les chunks
   s'empilent dans des files bornées et les workers les rattrapent.
5. Le fenêtrage live est une **grille fixe filtrée par le VAD**, là où le batch
   fenêtre à l'intérieur des zones de parole. C'est la raison d'être du *freeze*
   post-bootstrap de la brique 1.
6. Le repli est **binaire** : en cas de problème, `finalize()` n'écrit rien et
   le backend relance toute la brique 1.
7. Trois éléments (VAD, fenêtrage, segments) sont **réimplémentés** par rapport
   à la brique 1, sans test pour garantir leur cohérence.

**Premier chantier si l'on doit fiabiliser :** mesurer l'écart d'origine des
temps entre `audio.wav` et `turns.json` (§4.4). C'est le seul point qui, s'il se
confirme, dégrade une fonctionnalité visible par l'utilisateur — le surlignage
du transcript pendant la lecture.
