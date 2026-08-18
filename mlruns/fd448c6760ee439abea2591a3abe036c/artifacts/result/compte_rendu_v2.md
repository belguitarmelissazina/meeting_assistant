# Compte rendu de réunion

_Type de réunion_ : **atelier de travail**

_Objectif_ : Co-construire et prioriser des cas d'usage d'IA générative pour RTE, en alignant les besoins opérationnels avec les solutions techniques proposées.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a débuté par un tour de table où chaque participant a présenté son expertise en IA générative, notamment Maya SAHRAOUI avec un projet d'automatisation de rapports pour RTE utilisant des modèles multimodaux. Les discussions ont ensuite porté sur l'orchestration d'outils, la génération de POCs automatisés et l'extraction d'informations à partir de documents scannés, avec un accent sur la souveraineté des outils internes. Plusieurs projets concrets ont été détaillés, comme la détection de fraude sur des documents administratifs scannés, incluant un modèle VLM local et un monitoring des performances. Les participants ont également exploré des cas d'usage autour de l'orchestration de simulations et de la synthèse de données disparates, en s'appuyant sur des travaux en NLP et MCP. Enfin, un atelier design a été proposé pour prioriser ces cas d'usage, marquant une étape de co-construction active pendant la séance.

## Sujets abordés

### 1. Automatisation des processus opérationnels et interaction conversationnelle

Maya SAHRAOUI a présenté un projet d’automatisation de rédaction de rapports pour RTE, axé sur la transformation de documents complexes et hétérogènes (notamment des fichiers PPT contenant des graphiques et peu de texte) en rapports structurés et actionnables. L’objectif était d’accélérer la production de rapports sans altérer leur rigueur, en s’appuyant sur une chaîne de traitement en cinq briques : analyse des slides, assignation automatique des sections, rédaction par sections, intégration et boucle de correction itérative. L’outil développé permet une traçabilité des erreurs et une correction ciblée, avec une interface dédiée pour les équipes. Ce projet a démontré la faisabilité d’une automatisation rapide (25 jours) et a ouvert des perspectives pour généraliser cette approche à d’autres types de rapports.

Par ailleurs, Maya a évoqué un outil de génération de résumés de réunions en cours de développement, reposant sur une orchestration d’agents via MCP pour interagir avec des sources internes (notes de réunion, outils de simulation) et générer des synthèses interactives. L’objectif est d’automatiser la compréhension et la restitution des réunions, avec une interface de type chatbot pour faciliter l’accès aux outils et aux données. Ce cas d’usage illustre une volonté d’améliorer l’efficacité opérationnelle par l’automatisation des processus de synthèse et d’interaction conversationnelle.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Prendre contact avec Gérald pour évaluer la généralisation du projet de rédaction automatisée de rapports pour RTE. | SPEAKER_00 | — |
| 2 | Étudier l'adaptation de l'outil de Maya (Elya) pour des cas d'usage sans template prédéfini, en intégrant un agent de sélection de structure. | SPEAKER_01 | — |
| 3 | Explorer les possibilités d'orchestration via MCP pour les besoins de RTE en synthèse de données et interaction conversationnelle. | SPEAKER_02 | — |
| 4 | Noter la proposition d'un atelier design pour prioriser des cas d'usage et réfléchir à des solutions UX | SPEAKER_02 | — |
| 5 | Revenir vers SPEAKER_00 si des besoins plus précis (MCP ou NLP) émergent pour concrétiser les échanges | SPEAKER_02 | — |
