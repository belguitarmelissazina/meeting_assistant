# Compte rendu de réunion

*Source : `C:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\dicte_audio_3.normalized.txt`*

## 2. Executive Summary

La réunion a permis d’échanger sur les besoins spécifiques en matière d’intelligence artificielle générative au sein de la structure, avec un focus particulier sur la génération automatisée de rapports analytiques, l’orchestration de données hétérogènes et l’amélioration des outils de synthèse pour les opérateurs. Les discussions ont mis en lumière des projets concrets comme l’automatisation de la création de rapports d’études à partir de fichiers multimodaux (PowerPoint), ainsi que des explorations autour de l’orchestration via un module centralisé (MCP) pour traiter des données variées, notamment dans le cadre d’appels d’offres ou de réunions. Aucune décision définitive n’a été prise concernant les prochaines étapes techniques ou organisationnelles, mais une approche modulaire et itérative a été évoquée pour valider la faisabilité des solutions proposées, en intégrant des garde-fous pour garantir la qualité et la traçabilité des résultats. Les échanges ont également souligné l’importance de clarifier les besoins prioritaires avant d’envisager des déploiements spécifiques, notamment en matière d’interface utilisateur ou de gestion des données manuscrites.

## 3. Sujets abordés

### 1. Présentation des besoins et compétences en IA générative pour la génération automatisée de rapports analytiques

Discussion sur les attentes en matière d’IA générative, notamment pour transformer des données visuelles et textuelles (fichiers PPT) en rapports structurés et actionnables dans un contexte métier spécifique.

- Un projet de RTE vise à automatiser la création de rapports d’études sur la rentabilité des moyens de production à partir de fichiers PowerPoint riches en graphiques et peu textuels, pour accélérer leur rédaction sans altérer leur rigueur.
- La solution proposée repose sur une pipeline en cinq étapes : analyse légère des slides (OCR + description), assignation systématique des éléments aux sections prédéfinies du rapport via des règles métier et des descriptions détaillées.
- L’objectif initial était de créer un prototype fonctionnel en 25 jours, incluant ateliers, pour démontrer la valeur ajoutée de l’IA dans la génération de rapports, avec une boucle de correction itérative pour les membres de l’équipe.
- Les contraintes incluaient des templates structurés pour chaque section du rapport, mais le système pourrait théoriquement s’adapter à d’autres formats en intégrant un agent capable de sélectionner dynamiquement des directives générales.
- Maya a détaillé ses compétences sur des projets similaires (multimodalité, fine-tuning local, orchestration) et des outils comme Mistral ou VictoR pour le déploiement de modèles pré-entraînés, sans préciser d’échéances ou de décisions concrètes.

### 2. Validation et robustesse d’un outil de génération de rapports par templates multiples

Discussion sur la faisabilité d’une approche où un même agent utilise plusieurs modèles pour produire des chapitres distincts dans un rapport, avec mise en place de garde-fous techniques.

- L’outil permet de générer plusieurs versions de contenu à partir d’un ou plusieurs templates différents.
- La séparation par sections et l’attribution des slides à ces sections offrent une meilleure gestion des erreurs et une traçabilité pour leur correction rapide.
- Des artefacts intermédiaires (sorties brisées) sont créés pour faciliter la détection et la localisation des erreurs, comme les hallucinations ou incohérences dans chaque brique du rapport.
- Une boucle de correction itérative est mise en place via des commentaires par section, permettant une régénération automatisée du rapport à partir de ces retours humains.
- Des limites techniques mentionnées concernent notamment l’absence d’extraction chiffrée ou de vérification statistique des données extraites (hors scope), et la correction limitée aux niveaux de sections plutôt qu’au niveau global du document.

### 3. Synthèse et orchestration de données hétérogènes pour la rédaction et l’automatisation de synthèses

Les participants évoquent des projets internes visant à intégrer des outils spécialisés dans une logique d’orchestration pour traiter des cas d’usage comme les appels d’offres ou les réunions, en exploitant des données variées (CV, rapports, enregistrements vocaux).

- Un projet utilise N8N pour orchestrer plusieurs agents spécialisés dans la rédaction de réponses aux appels d’offres, à partir de données internes comme CV et références.
- Le second projet en cours cible la génération automatisée de synthèses de réunions via un outil interactif (chatbot), intégrant des outils internes ou externes pour extraire et traiter des notes existantes ou nouvelles (ex : enregistrements vocaux).
- L’objectif est d’améliorer la souveraineté technique en centralisant ces outils autour d’un système modulaire, sans dépendre de solutions extérieures comme des bouquets ou marchés publics.
- La synthèse vise aussi à renforcer la confidentialité et la précision des résultats en exploitant des données spécifiques au contexte interne (ex : données ouvertes sur l’énergie).
- L’orchestration se fait via un MCP pour gérer dynamiquement une liste d’outils, permettant par exemple d’ajouter des fonctionnalités comme la génération de mindmaps ou le traitement de données structurées (Sherpa/notes internes)

### 4. Amélioration des synthèses et gestion de projets via outils spécialisés

L'objectif est d'améliorer les retours synthétiques et d'adapter leurs usages pour renforcer la souveraineté technique dans l'environnement d'utilisation des outils.

- Il est proposé d'augmenter la qualité des synthèses et de les rendre plus complètes, mieux adaptées au contexte spécifique.
- Un cloisonnement est envisagé pour limiter l'accès à ces outils aux utilisateurs concernés (ex. : RTE), afin d'éviter une diffusion non contrôlée vers d'autres services.
- Pour deux missions d’orchestration identifiées, aucune décision définitive n’a été prise concernant leur traitement spécifique.
- Un projet en cours concerne la planification de processus (POK) qui ne relève pas encore de l’orchestration automatisée.
- Une idée explorée est de développer un agent capable de générer automatiquement une cartographie de projets (POC minimal) à partir d’un sujet donné, intégrant plusieurs outils de bibliographie et simulation.

### 5. Utilisation de modèles VLM pour l'extraction et la conformité des données dans les documents administratifs

Ce projet vise à automatiser l'analyse de documents scannés (manuscrits ou non) pour extraire des informations structurées, évaluer leur conformité et détecter des anomalies via un modèle visuo-linguistique.

- L'objectif est d'extraire des données comme les salaires nets/bruts et les métiers des documents administratifs scannés.
- Un outil VLM doit estimer le pourcentage de conformité entre ces extraits et des références existantes pour vérifier leur cohérence.
- La phase de travail inclut la finetuning du modèle VLM, le contrôle d’anomalies et le déploiement sur un tableau de bord pour surveiller les performances en production.
- Le projet a été mené initialement hors contexte actuel (Yéley) et nécessite une intervention pour finaliser certaines étapes techniques.
- La qualité des données et la gestion des documents rédigés en arabe ont influencé les choix méthodologiques, notamment le prétraitement.

### 6. Cas d’usage et orientation des travaux autour de l’orchestration et du traitement des données

Les participants échangent sur les pistes concrètes pour exploiter des cas d’usage liés à la synthèse, l’orchestration et le traitement automatisé de données fragmentées ou manuscrites.

- Le sujet principal porte sur l’exploration des cas d’usage NLP (traitement du langage naturel) et MCP (module central de production), notamment pour la gestion de notes manuscrites et la synthèse de sources disparates.
- L’idée centrale est de combiner des outils internes ou externes via un MCP pour orchestrer des simulations, des études et des analyses en amont de rapports, avec une dimension humaine de contrôle.
- Les échanges soulignent l’importance d’une approche modulaire : récupérer des hypothèses, scénarios ou données brutes (ex. consommation/production), puis les relier à des simulateurs ou visualisateurs pour ajuster dynamiquement les études.
- Le projet inclut explicitement la partie ‘orchestration’ comme axe prioritaire, en lien avec une feuille de route existante incluant des PoC (proof of concept) pour des serveurs MCP et des outils de génération de rapports.
- Les travaux actuels ou futurs sur le traitement du texte manuscrit sont mentionnés comme un fil conducteur potentiel, mais restent distincts des priorités immédiates centrées sur la MCP et les interactions avec des outils complexes.

### 7. Échanges sur l’intégration du MCP et priorisation des cas d’usage

Les participants discutent de la nécessité de clarifier les besoins précis pour une intégration future d’un système de gestion de contenu (MCP) ou d’approches liées au NLP, ainsi que de l’avancement des travaux techniques.

- Aucune décision définitive n’a été prise concernant un cas d’usage spécifique pour le MCP après avoir noté qu’aucun besoin clair ne s’est dégagé lors du point précédent.
- L’équipe propose de revenir vers les interlocuteurs si des précisions émergent sur les besoins ou priorités en matière de MCP ou NLP, sans action immédiate.
- Un atelier de réflexion UX est proposé pour prioriser et définir des cas d’usage avec l’équipe GALÉT, en collaboration avec un cabinet spécialisé dans le design (Olivier Maserol).
- Les travaux existants sur les projets internes limitent temporairement la capacité à se concentrer exclusivement sur cette intégration, nécessitant une sollicitation externe si nécessaire.
- L’objectif reste de finaliser l’agenda et l’ordonnancement des activités pour avancer dans les autres projets en parallèle.

## 4. Décisions

_Aucune décision formellement prise._

## 5. Plan d'attaque

| # | Sujet | Action | Responsable | Échéance |
|---|-------|--------|-------------|----------|
| 1 | Présentation des besoins en IA générative pour la génération automatisée de rapports analytiques | Finaliser et lancer le prototype de génération automatisée de rapports d’études sur la rentabilité à partir de fichiers PowerPoint, incluant les ateliers de démonstration et la boucle de correction itérative avec l’équipe RTE | Maya | d’ici fin de semaine |
| 2 | Synthèse et orchestration de données hétérogènes pour la rédaction automatisée | Déployer un système d’orchestration centralisé (via MCP) pour gérer dynamiquement les outils spécialisés dans la rédaction de réponses aux appels d’offres et la synthèse de réunions, en intégrant des fonctionnalités comme la génération de mindmaps ou le traitement de données structurées | — | — |
| 3 | Validation et robustesse d’un outil de génération de rapports par templates multiples | Valider les artefacts intermédiaires (sorties brisées) générés par l’outil de génération de rapports pour améliorer la traçabilité des erreurs (hallucinations, incohérences), et automatiser leur correction via des commentaires par section | — | — |
| 4 | Utilisation de modèles VLM pour l’extraction et la conformité des données dans les documents administratifs | Préparer un finetuning spécifique du modèle VLM pour le traitement des documents administratifs scannés en arabe, incluant les étapes de contrôle d’anomalies et la mise à disposition sur un tableau de bord dédié (avec ajustements techniques si nécessaire) | — | — |
