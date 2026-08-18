# Compte rendu de réunion

*Source : `C:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\dicte_audio_3.normalized.txt`*

## 2. Executive Summary

Cette réunion vise à établir un échange structuré sur les besoins spécifiques en matière d’IA générative pour répondre aux enjeux opérationnels et métiers, notamment autour de la création automatisée de rapports techniques ou d’assistants interactifs pour les opérateurs. Les participants explorent des solutions concrètes pour industrialiser la génération de synthèses à partir de données hétérogènes (fichiers multimodaux, graphiques, textes), en s’appuyant sur des pipelines modulaires et des outils comme NLP ou modèles visuo-linguistiques, tout en garantissant robustesse, traçabilité et conformité aux processus internes.

Les discussions portent aussi sur l’orchestration de systèmes pour traiter des données fragmentées (notes manuscrites, réunions, documents scannés), avec un accent sur la souveraineté technique et l’adaptation à des contextes spécifiques comme celui de RTE. Bien que des projets pilotes aient été menés pour valider des approches comme la génération automatisée de rapports via des templates ou la synthèse d’événements, aucune décision définitive n’a encore émergé concernant les priorités techniques ou l’intégration d’outils comme le MCP, sauf une invitation à échanger avec des partenaires externes pour affiner ces orientations.

L’objectif reste de cibler des solutions pragmatiques, tout en préservant la flexibilité pour ajuster les approches selon les retours terrain et les contraintes opérationnelles. Aucune action ou décision spécifique n’a été formalisée à ce stade, mais une prise de contact et une exploration collaborative sont engagées pour identifier ensemble les leviers d’amélioration.

## 3. Sujets abordés

### 1. Présentation des besoins et compétences en IA générative pour l’automatisation de rapports techniques

Discussion sur les attentes en matière d’IA générative, notamment pour la création automatisée de synthèses ou rapports structurés à partir de données hétérogènes (fichiers PPT, graphiques, textes).

- Mathieu et ses collègues (DataIa Manager) décrivent des missions sur l’équilibre offre-demande et gouvernance, incluant des analyses de rentabilité des moyens de production, nécessitant une automatisation des rapports.
- Maya partage son expérience en traitement automatique des langues (TAL), spécialisée dans la transformation multimodale de documents complexes vers des formats actionnables pour les équipes R&D, avec un focus sur l’industrialisation et le monitoring.
- Le projet RTE consistait à automatiser la rédaction de rapports détaillés à partir de fichiers PPT contenant graphiques et textes hétérogènes, en structurant chaque section selon une grille prédéfinie (hypothèses, comparaisons, etc.).
- La solution impliquait une pipeline en cinq étapes : analyse des slides via OCR, assignation automatique aux sections avec règles métier, rédaction par agents (bullet points puis prose), intégration et boucle de correction itérative.
- L’objectif initial était un PoC validé en 25 jours pour démontrer la valeur ajoutée de l’IA sur la génération de rapports, avec une évaluation ultérieure des suites possibles.

### 2. Validation et robustesse d’un outil de génération de rapports par templates

Discussion sur la faisabilité et les éléments techniques d’une approche multi-templates pour automatiser partiellement la rédaction de rapports, avec mise en avant des garde-fous pour la robustesse et la traçabilité.

- L’outil peut fonctionner avec plusieurs templates distincts pour produire des sorties multiples (adaptées ou orientées par un agent).
- La séparation en sections et l’assignation de slides permettent une meilleure gestion des erreurs et une traçabilité précise des corrections.
- Des artefacts intermédiaires à la sortie des briques facilitent le suivi des erreurs, notamment les hallucinations, pour une validation humaine ciblée.
- Une boucle de correction itérative par commentaires sectionnels permet de régénérer et valider localement chaque partie du rapport.
- Les limites mentionnées concernent l’absence d’extraction chiffrée ou de vérification des données brutes (fichiers Excel), ainsi que la correction limitée aux sections plutôt qu’à un niveau macro global.

### 3. Orchestration de systèmes pour la synthèse et l'automatisation des données hétérogènes

Les échanges portent sur les cas d’usage liés à la gestion de sources de données variées (rapports, réunions) via une orchestration modulaire pour générer des synthèses ou assister dans des processus internes.

- Un projet interne utilise N8N pour orchestrer plusieurs agents spécialisés en CV, références et réponses aux appels d’offres afin de produire des listes de candidats ou rédiger des supports associés.
- Le second projet vise à développer un outil interactif (via chatbot) pour générer automatiquement des résumés de réunions à partir de notes stockées dans SharePoint ou exportables, en intégrant progressivement des fonctionnalités supplémentaires (enregistrement vocal, mindmaps).
- L’objectif est d’améliorer la souveraineté technique et opérationnelle en exploitant des outils internes pour traiter des données confidentielles ou spécialisées, sans dépendre de solutions externes.
- La synthèse des événements ou des données est évoquée comme un besoin partagé dans les deux sens (front-end et back-end), avec une attention particulière à l’orchestration de briques modulaires pour répondre aux besoins métiers spécifiques.

### 4. Amélioration des synthèses et gestion de projets via outils spécialisés

L'objectif est d’optimiser les processus de synthèse, d’adapter les propositions aux contextes spécifiques et de renforcer la souveraineté technique des utilisateurs selon leurs besoins.

- Synthétiser et enrichir les rapports pour les rendre plus complets et mieux adaptés au contexte opérationnel
- Cloisonner l’utilisation de cet outil afin qu’il reste réservé à un environnement spécifique (ex. RTE) sans extension vers d’autres services
- Développer une approche d’orchestration pour deux missions distinctes, en excluant les projets où la planification se fait manuellement
- Créer une agent automatisée de bibliographie et d’omap pour accélérer l’élaboration de propositions de projet (POC) à partir d’un sujet donné
- Intégrer progressivement plusieurs outils de simulation dans un pipeline automatisé pour faciliter la mise en œuvre des scénarios techniques

### 5. Utilisation de modèles VLM pour l'extraction et la conformité des données administratives

Ce projet vise à automatiser l'analyse de documents scannés (administratifs ou manuscrits) via un modèle visuo-linguistique pour détecter des anomalies dans les extraits d'informations comme les salaires et métiers.

- Le travail porte sur le prétraitement, l'apprentissage et la fin-tunage d'un modèle VLM pour structurer des données issues de documents scannés (administratifs ou manuscrits).
- L'objectif est d'évaluer la conformité des informations extraites (ex. : salaire vs métier) par rapport à une référence historique via un outil de détection de drift.
- La solution inclut un contrôle d'anomalies, le déploiement local du modèle et un tableau de bord pour surveiller les performances en production.
- Le projet a été initialement développé hors de l'organisation actuelle, avec des spécificités liées à la langue arabe et aux documents manuscrits nécessitant une classification préalable.

### 6. Cas d’usage et orientation des travaux autour de l’orchestration et du traitement des données fragmentées

Les participants discutent des pistes concrètes pour exploiter les cas d’usage liés à la synthèse de données, aux notes manuscrites et à l’orchestration des études via un système centralisé (MCP).

- Le sujet porte sur des cas d’usage centrés sur la gestion de blocs d’alarme, messages ou données disparates pour leur synthèse automatisée.
- L’orientation inclut des travaux en traitement du langage naturel (NLP) pour traiter les notes manuscrites et extraire des informations structurées.
- Le MCP est évoqué comme outil clé pour orchestrer des simulations internes, récupérer des outils de génération de rapports ou d’études existants via une interface dédiée.
- L’objectif inclut la préparation automatisée de pré-rapports (scénarios, études) avec un contrôle humain final sur leur équilibre et pertinence avant validation par les comités.
- Les échanges soulignent aussi des besoins en gestion dynamique d’hypothèses et de données en temps réel pour ajuster stratégies ou scénarios via différents outils spécialisés.

### 7. Échanges sur l’intégration du MCP et priorisation des cas d’usage

Discussion entre deux parties pour clarifier les besoins en intégration d’un module spécifique (MCP) ou de solutions NLP, ainsi que pour organiser une collaboration future autour de projets techniques et design.

- Le participant 2 propose de ne pas approfondir un cas d’usage précis sur le MCP sans éléments supplémentaires clairs avant un retour ultérieur.
- Aucune décision définitive n’a été prise concernant l’intégration du MCP ou la priorisation des travaux, mais il est évoqué une attente pour des informations plus précises.
- Le participant 0 suggère un atelier de réflexion sur les cas d’usage avec des partenaires externes (UX design) pour partager leur vision et prioriser les besoins.
- Des actions internes sont déjà prévues pour explorer le MCP, sans prévoir de priorité immédiate par rapport à d’autres projets en cours.
- L’intégration potentielle du MCP pourrait s’inscrire dans l’agenda des projets existants, avec une nécessité de coordination entre équipes et opérateurs limitant les ressources disponibles.

## 4. Décisions

_Aucune décision formellement prise._

## 5. Plan d'attaque

| # | Sujet | Action | Responsable | Échéance |
|---|-------|--------|-------------|----------|
| 1 | Présentation des besoins et compétences en IA générative pour l’automatisation de rapports techniques | présenter les projets sur lesquels j’ai travaillé chez RTE (études EOD rentabilité des moyens de production) et chez Ely | Maya | — |
| 2 | Présentation des besoins et compétences en IA générative pour l’automatisation de rapports techniques | explorer la possibilité d’adapter l’outil pour une utilisation sans template structuré, en rédigeant une seule section avec directives de temps/contenu | Maya (à vérifier selon les règles métier) | — |
| 3 | Présentation des besoins et compétences en IA générative pour l’automatisation de rapports techniques | développer un PoC sur la gestion des congestions avec le modèle existant chez RTE | Jérôme/Picot (ou — si non précisé dans ce passage) | — |
| 4 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | travailler sur le *fin-tuning* du VLM (Vision-Language Model) en récupérant la sortie structurée des informations extraites | — | — |
| 5 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | intervenir sur le contrôle d’anomalies dans le traitement des documents scannés | — | — |
| 6 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | déployer le modèle avec VLM et UVCorne (UVCorne non explicitement nommé, supposons une erreur de transcription pour UVCorn) | — | — |
| 7 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | créer un *dashboard* pour monitorer la chaîne de traitement et détecter les drifts en performance (ex. : détection des anomalies dans les résultats en production) | — | — |
| 8 | Échanges sur l’intégration du MCP et priorisation des cas d’usage | tenir informé si jamais il y a quelque chose de plus précis qui se dégage (MCP ou NLP) | — | — |
| 9 | Échanges sur l’intégration du MCP et priorisation des cas d’usage | noter le point sur les avancées des travaux MCP et proposer un second échange si nécessaire | SPEAKER_02 | — |
| 10 | Validation et robustesse d’un outil de génération de rapports par templates | Documenter les artefacts intermédiaires (sorties par brique) pour faciliter la traçabilité des erreurs et leur correction itérative | — | — |
| 11 | Validation et robustesse d’un outil de génération de rapports par templates | Valider l'implémentation des garde-fous de robustesse (structure finale, séparation par sections, assignation des slides) dans un test en conditions réelles avec des données représentatives | — | — |
| 12 | Orchestration de systèmes pour la synthèse et l'automatisation des données hétérogènes | Identifier et documenter les outils internes développés (N8N, agents spécialisés CV/références/réponses AO) pour faciliter leur réutilisation dans d’autres projets ou synthèses génératives. | — | — |
| 13 | Orchestration de systèmes pour la synthèse et l'automatisation des données hétérogènes | Étudier l’intégration des fonctionnalités de capture vocale et génération de mindmaps via une interface LM (Language Model) pour enrichir les outils de synthèse de réunions en interne. | — | — |
| 14 | Amélioration des synthèses et gestion de projets via outils spécialisés | Établir une liste priorisée des outils de simulation accessibles et valider leur intégration dans la pipeline pour les projets de bibliographie et planification | — | — |
| 15 | Amélioration des synthèses et gestion de projets via outils spécialisés | Documenter les cas d’usage actuels d’orchestration (RTE) afin de clarifier les limites et besoins en souveraineté technique pour éviter les transferts involontaires vers d’autres environnements | — | — |
| 16 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | Valider et documenter les critères de conformité des extraits salariaux/métiers pour le projet VLM (ex : intervalle de confiance) afin d’unifier la logique de détection de drift entre les documents scannés. | — | — |
| 17 | Utilisation de modèles VLM pour l'extraction et la conformité des données administratives | Identifier et standardiser les pré-traitements spécifiques aux documents manuscrits ou rédigés en arabe dans l’outil de filtrage pour éviter des erreurs de classification ultérieure. | — | — |
