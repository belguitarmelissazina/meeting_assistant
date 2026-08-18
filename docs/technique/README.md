# Documentation technique — Meeting Assistant

Documentation de reprise du projet, écrite brique par brique. Cible : un
développeur qui reprend le code sans l'avoir écrit.

## Périmètre

**Uniquement ce qui est livré dans l'application** — concrètement, le code
**suivi par git**, c'est lui qui part dans le build.

Le dossier de travail contient beaucoup d'autre chose : scripts de benchmark
(`_bench_*`), méthodes alternatives, tracking MLflow, et des chantiers en cours
non commités (orchestrateur agentique `local_minutes.py` + `_bench_orchestrator.py`,
assistant live Mistral, export DOCX). Rien de tout cela n'est documenté : ce sont
des travaux d'expérimentation, hors du produit livré.

Chaque document se termine par une section listant ce qui, dans les fichiers
concernés, ne fait pas partie de l'application — pour qu'un repreneur ne le
confonde pas avec de la logique livrée.

> ⚠ **L'arbre de travail n'est pas l'application.** Vérifier
> `git ls-files <fichier>` avant de documenter quoi que ce soit d'inhabituel :
> plusieurs fichiers d'apparence centrale ne sont pas suivis, et plusieurs
> fichiers suivis ont des modifications non commitées importantes. Cette
> documentation décrit systématiquement l'état **HEAD**.

Une brique = un périmètre fonctionnel, pas un périmètre de fichiers. Le
déploiement est traité **une seule fois**, dans la brique 7 — pas redit dans
chaque document.

## Les briques

| # | Brique | Document |
|---|--------|----------|
| 1 | Diarisation + transcription (batch) | [01-diarisation-transcription.md](01-diarisation-transcription.md) |
| 2 | Capture audio & pipeline temps réel | [02-capture-audio-live.md](02-capture-audio-live.md) |
| 3 | Génération de compte rendu (LLM) | [03-llm-compte-rendu.md](03-llm-compte-rendu.md) |
| 4 | Backend API (FastAPI) | [04-backend-api.md](04-backend-api.md) |
| 5 | Shell Electron | [05-electron.md](05-electron.md) |
| 6 | Frontend (Next.js) | [06-frontend.md](06-frontend.md) |
| 7 | Build & distribution | [07-build-distribution.md](07-build-distribution.md) |

Documents connexes, déjà existants et non repris ici : [WORKFLOW.md](../../WORKFLOW.md)
(procédures de développement et de publication) et [BUILD.md](../../BUILD.md).

### Pas de brique « benchmarks »

Le dépôt contient une trentaine de scripts d'évaluation (`_bench_*.py`,
`bench_tracking.py`, `mlflow_ui.py`, `mlruns/`) et le module
`diar_pipeline/tracking.py`. Ils ont servi à choisir la configuration actuelle —
modèle d'embedding, méthode de clustering, découpage sémantique, moteur LLM — et
resservent si un choix doit être rejustifié.

Ils ne sont **pas** documentés : ils ne tournent pas dans l'application, et pour
la plupart ne sont pas suivis par git. Un repreneur doit savoir qu'ils existent
et qu'il peut les ignorer pour comprendre le produit.

### Notes en attente d'arbitrage

Analyses complémentaires écrites mais **pas intégrées** aux documents. À classer :
soit fusionnées dans la brique concernée, soit écartées.

| Note | Concerne | Contenu |
|---|---|---|
| [_note-ducking-analyse.md](_note-ducking-analyse.md) | brique 2, §4.3 et §4.4 | limites du ducking (transitions, parole simultanée, casque non détecté) et divergence de constante de temps entre les deux mixages |

## Conventions

- Les références de code sont données sous la forme `fichier.py:ligne` et
  pointent vers la ligne exacte au moment de la rédaction. Le numéro peut
  dériver ; le nom de fonction, lui, reste valable.
- Les blocs **⚠** recensent les choix qui paraissent arbitraires mais corrigent
  un bug réel, souvent reproduit et documenté en commentaire dans le code. Ne
  pas les défaire sans avoir relu la justification.
- Les sections **Ce qui n'est PAS utilisé / dans l'application** listent ce qui
  existe dans les fichiers concernés sans être appelé en production. C'est
  délibérément explicite : sans ça, un repreneur perd du temps à maintenir du
  code mort.
- Ce qui est **déduit du code sans avoir été mesuré ou exécuté** est signalé
  comme tel. Aucun chiffre de performance de ce corpus ne provient d'un
  benchmark réel.

## Défauts identifiés en cours de rédaction

Relevés en lisant le code, vérifiés, et documentés dans leur brique. Aucun n'a
été corrigé.

| # | Défaut | Brique |
|---|---|---|
| 1 | `_cleanup_intermediate_files` supprime **tout fichier** du dossier de réunion absent d'une liste de sept noms — y compris ceux déposés par l'utilisateur — à chaque démarrage | 4 §5.4 |
| 2 | Le marqueur `.origin.recording` n'est pas dans cette liste : il est détruit par le nettoyage qu'il est censé survivre | 4 |
| 3 | `DELETE /api/folders/{name}` n'assainit pas le nom, contrairement à ses voisins → remontée d'arborescence possible | 4 §6 |
| 4 | `GET /api/jobs` renvoie tout l'historique intégral, sondé ~2×/s par quatre consommateurs | 4 §12.2, 5 §10.1, 6 §2 |
| 5 | La clé API Mistral est stockée en clair, alors que le jeton Microsoft du même dossier est chiffré par DPAPI | 4 §2.3 |
| 6 | Aucune signature de code : SmartScreen avertit à chaque installation | 7 §9.1 |
| 7 | Origine des temps possiblement décalée entre `audio.wav` et le transcript live (**déduit, non mesuré**) | 2 §4.4 |
