# Note — analyse du ducking (non intégrée)

**Statut : en attente d'arbitrage.** Ce fichier n'est pas un document de la
documentation technique. Il contient une analyse complémentaire du ducking
audio, à intégrer ou non dans
[02-capture-audio-live.md](02-capture-audio-live.md) — les emplacements
d'insertion sont indiqués à chaque section.

**Toutes les valeurs ci-dessous sont déduites du code, pas mesurées.** Aucun
enregistrement réel n'a été analysé. À vérifier avant d'en tirer des
conclusions opérationnelles.

---

## Rappel — les paramètres

Identiques dans les deux fonctions de mixage
([`_mix_with_ducking`](../../audio_capture/recorder.py#L522) et
[`_live_mix_worker`](../../audio_capture/recorder.py#L578)) :

```python
lb_active_rms          = 0.015   # seuil au-delà duquel le loopback est "actif"
mic_gain_normal        = 0.8
mic_gain_ducked        = 0.08    # -20 dB par rapport au gain normal
user_over_remote_ratio = 1.6
lb_gain                = 0.9
smoothing              = 0.25
```

Décision, par bloc :

```
si lb_rms > 0.015  ET  mic_rms < 1.6 × lb_rms   →  cible = 0.08   (fuite)
sinon                                            →  cible = 0.8    (parole locale)
```

Application, avec lissage :

```
gain = gain_précédent + (cible − gain_précédent) × 0.25
```

---

## 1. Ce que le ducking résout effectivement

*(à ajouter en tête du §4.3, avant le tableau des trois situations)*

En régime établi, quand le distant parle seul, le micro converge vers 0,08 et
le mixage est dominé par le loopback à 0,9. La voix du distant n'est donc
présente **qu'une seule fois**, dans sa version numérique propre. C'est le cas
majoritaire, et le problème du locuteur dédoublé y est réellement traité.

Ce que le ducking **n'est pas** : de l'annulation d'écho. Il ne soustrait
jamais la fuite du signal micro, il baisse le gain du micro entier pendant
qu'elle est présente. Tout ce que le micro capte d'autre pendant ce temps —
y compris la parole locale — est atténué dans la même proportion.

---

## 2. Les transitions — le régime transitoire dure ~1,4 s

*(à ajouter en fin de §4.3, après le tableau)*

Le lissage `0.25` fait converger le gain géométriquement :
`gain_n = cible + (gain_0 − cible) × 0.75ⁿ`.

En passant du gain normal 0,8 vers le gain étouffé 0,08 :

| blocs écoulés | 1 | 2 | 3 | 4 | 6 | 8 | 12 |
|---|---|---|---|---|---|---|---|
| **gain micro** | 0,62 | 0,49 | 0,38 | 0,31 | 0,21 | 0,15 | 0,10 |
| **atténuation** | −2 dB | −4 dB | −6 dB | −8 dB | −12 dB | −14 dB | −18 dB |

Il faut une douzaine de blocs pour approcher la cible. Le lissage est là pour
éviter les clics audibles à chaque bascule de décision — c'est un compromis
assumé entre artefacts et réactivité.

**Deux conséquences, et la seconde est la plus gênante :**

- **À l'attaque** (le distant commence à parler) : le début de sa prise de
  parole passe en double, avec une atténuation qui monte progressivement.
- **Au relâchement** (le distant se tait, l'utilisateur local répond) : le
  gain met le même temps à remonter de 0,08 vers 0,8. **Le début de chaque
  réponse locale est donc atténué**, typiquement de 12 à 20 dB sur les
  premières centaines de millisecondes. C'est le cas de figure classique d'un
  échange en visio — et le risque n'est plus un locuteur dédoublé, mais des
  mots simplement perdus par l'ASR en début de tour de parole.

---

## 3. La parole simultanée peut effacer l'utilisateur local

*(à ajouter en fin de §4.3)*

La condition d'étouffement est `mic_rms < 1,6 × lb_rms`. Si l'utilisateur parle
**en même temps** que le distant sans être nettement plus fort, il est classé
comme fuite acoustique et étouffé à 0,08.

Le seuil de 1,6 arbitre entre deux erreurs opposées :

- **trop bas** → l'utilisateur n'est jamais étouffé, la fuite passe et la voix
  du distant se dédouble ;
- **trop haut** → l'utilisateur est étouffé dès qu'il parle par-dessus le
  distant, et c'est sa voix qu'on perd.

Rien ne permet de distinguer, sur le seul rapport de niveaux, « micro captant
la fuite » de « utilisateur parlant en même temps ». Une annulation d'écho
véritable (AEC) le ferait, en soustrayant du signal micro une version filtrée
du loopback — mais aucune n'est en place ici.

---

## 4. Le code ne sait pas si l'utilisateur porte un casque

*(à ajouter en fin de §4.3, ou en §10 comme limite à part entière)*

Au casque, il n'y a **aucune fuite acoustique** : le ducking ne corrige rien.
Mais il s'applique quand même, à l'identique. Concrètement, au casque, dès que
le distant parle, la voix de l'utilisateur est atténuée s'il n'est pas 1,6 fois
plus fort — le ducking dégrade une situation qui n'avait pas de problème.

Windows n'expose pas de façon fiable si la sortie active est un casque ou des
haut-parleurs (un casque USB, Bluetooth ou jack se présente simplement comme le
périphérique de sortie par défaut). Deux pistes si le sujet devenait bloquant :

- exposer un réglage explicite « je suis au casque » qui désactive le ducking
  et se contente d'additionner les deux flux ;
- estimer la corrélation entre le loopback et le micro sur les premières
  secondes : forte corrélation = haut-parleurs, corrélation nulle = casque.
  Plus robuste, mais nettement plus de code.

---

## 5. Les deux mixages n'ont pas la même constante de temps

*(à ajouter au §4.4, comme seconde divergence, distincte de celle sur l'origine
des temps)*

C'est le point qui m'a échappé lors de la rédaction initiale. Les six
constantes sont bien dupliquées **à l'identique** entre les deux fonctions —
mais elles ne s'appliquent pas à des blocs de même durée.

| | Mixage **offline** (`audio.wav`) | Mixage **live** (transcription) |
|---|---|---|
| Découpage | fenêtres **fixes de 120 ms** (`window_ms=120`) | un bloc par cycle du worker, **≈ 50 ms** (`poll_interval=0.05`), variable |
| Une décision de gain | toutes les 120 ms | toutes les ~50 ms |
| Convergence (12 blocs) | **≈ 1,4 s** | **≈ 0,6 s** |

**Le ducking réagit donc environ 2,4 fois plus vite en live qu'en offline.**
Le fichier `audio.wav` conservé et le signal réellement envoyé à la
transcription ne sont pas exactement le même son.

Deux effets secondaires :

- **En live, la décision est plus bruitée.** Le RMS est estimé sur ~50 ms au
  lieu de 120 ms : moins d'échantillons, donc plus de variance, donc des
  bascules de décision plus fréquentes sur un signal au niveau intermédiaire.
- **La taille de bloc live n'est pas constante.** Le worker traite
  `min(len(mic_pending), len(lb_pending))` échantillons, avec un plancher de
  512 (32 ms). Selon la gigue d'arrivée des deux flux, un bloc peut valoir 32 ms
  comme 100 ms — la constante de temps du ducking varie donc au fil de
  l'enregistrement.

À noter : cette divergence est **indépendante** de celle déjà documentée au
§4.4 sur l'origine des temps (zéros ajoutés côté offline, échantillons rognés
côté live). Les deux se cumulent.

---

## 6. Ce qu'il faudrait mesurer pour trancher

Aucun de ces points ne justifie une modification tant qu'ils n'ont pas été
constatés sur un enregistrement réel. Protocole minimal :

1. **Une réunion en visio sur haut-parleurs**, avec alternance de prises de
   parole locale et distante, et au moins un passage en parole simultanée.
2. Comparer, sur `audio.wav` : le niveau du micro au début et à la fin de
   chaque tour distant → confirme ou infirme le §2.
3. Vérifier dans `transcript.txt` si des mots manquent en **début** de tours
   locaux suivant un tour distant → c'est la conséquence utilisateur du §2.
4. Compter les locuteurs détectés : un locuteur de trop, acoustiquement proche
   d'un participant distant, signerait une fuite insuffisamment étouffée.
5. **La même réunion au casque** : si l'utilisateur local est atténué en parole
   simultanée alors qu'aucune fuite n'existe, le §4 est confirmé.
