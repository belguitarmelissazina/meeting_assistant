# Compte rendu de reunion

_Type de reunion_ : **revue projet IA et automatisation métiers**

_Sujet_ : Les participants échangent sur les besoins techniques et stratégiques en matière d’intelligence artificielle générative, d’assistants interactifs et d’automatisation des processus métiers pour optimiser la rentabilité et l’interaction opérateur-outils.

## Synthese

Cette réunion porte sur une collaboration entre experts de **Élé Consulting** (Matthieu DUSSARTRE) et **IVB** (Maya SAHRAOUI), ainsi que des membres internes (Jérôme MASSET, Jérôme PICAULT, Nourredine HENKA non cité explicitement dans les échanges). L’objectif est d’affiner la feuille de route autour de l’intégration d’assistants IA et de technologies NLP pour les opérateurs de soins ou conduite, tout en explorant des besoins exploratoires en données techniques (calculs, réseaux) et en automatisation de rapports métiers à partir d’études PowerPoint. Les discussions se concentrent sur la structuration des échanges entre offre et demande, notamment via des outils comme le *Smart Cockpit* et des systèmes MCP (gestion de contenu). Aucune décision formelle n’a été prise, mais une phase informelle de prise de contact et d’analyse des attentes est engagée pour prioriser les cas d’usage et organiser éventuellement un atelier UX. Les projets en cours incluent l’industrialisation de workflows génératifs (ex : transformation multimodale), la création d’agents de planification de projets, ou encore l’adaptation d’outils de rédaction automatisée avec des templates dynamiques.

## 1. Présentation des participants et de leurs rôles

Lors de cette première phase du tour de table, Matthieu DUSSART a présenté son rôle au sein d’Élé Consulting comme expert data et manager de la pratique DataIA. Il souligne sa collaboration sur les sujets liés à l’intelligence artificielle générative avec Maya SAHRAOUI, ainsi que des travaux sur l’équilibre entre offre et demande pour optimiser la rentabilité des moyens techniques et métiers.

## 2. Échanges sur les besoins en IA générative, assistants interactifs et automatisations métiers

Les échanges portent sur les besoins spécifiques en IA générative pour les assistants interactifs destinés aux opérateurs de soins ou de conduite, avec une attention particulière portée sur la gestion des données techniques et l’automatisation des rapports métiers à partir d’études PowerPoint. L’objectif est d’affiner la collaboration entre experts de l’équipe Smart Cockpit et Maya SAHRAOUI pour structurer ces besoins en fonction des technologies MCP et NLP mises en œuvre.

- Les participants soulignent que les assistants interactifs doivent s’appuyer sur une interface quasi conversationnelle, intégrant un système MCP pour assurer une interaction fluide entre l’opérateur et ses outils, sans dépendre uniquement de la technologie NLP seule.
- Maya SAHRAOUI présente des projets d’automatisation de rédaction de rapports métiers à partir de PowerPoint, en transformant des contenus multimodaux (graphiques, textes) en fiches actionnables ou synthèses décisionnelles pour faciliter la prise de décision.
- L’objectif initial était de créer une chaîne de traitement automatisée pour accélérer la production de rapports tout en préservant leur rigueur, en ancrant chaque affirmation générée dans des figures ou des textes associés aux fichiers PPT originaux.
- La solution inclut une industrialisation avec un volet de monitoring et une séparation entre le front-end (rédaction structurée par sections) et l’arrière-plan (correction itérative via des commentaires humains), permettant une boucle de validation continue.
- Les étapes clés du pipeline incluent : la description exhaustive des slides via OCR pour extraire texte et analyser graphiques, l’assignation automatique des slides aux sections prédéfinies selon des règles métier (ex : exclusion des données non pertinentes dans certaines parties), et une rédaction section par section avec séparation des bullet points et de la prose.
- La robustesse de cette approche repose sur la traçabilité des artefacts intermédiaires à chaque étape, facilitant ainsi les corrections ciblées et évitant les incohérences entre sections du rapport final.
- Les contraintes techniques mentionnées incluent l’absence d’un contrôle quantitatif des valeurs extraites des graphiques (hors scope de la mission) ou une reconstruction des données brutes depuis Excel, limitant ainsi la précision des analyses génératives à ce stade exploratoire.
- Maya SAHRAOUI évoque également un projet en cours visant à développer un outil interactif de génération de synthèses de réunions via un MCP orchestrant plusieurs agents spécialisés (ex : résumés vocaux, mindmaps), avec une approche modulaire pour intégrer des fonctionnalités supplémentaires comme l’enregistrement vocal ou la gestion de données internes.
- L’objectif final est d’automatiser la compréhension et la synthèse des réunions, tout en garantissant souveraineté technique (accès aux données internes) et confidentialité, sans dépendre d’API externes.

## 3. Pistes exploratoires et suggestions pour la suite de la collaboration

Lors des échanges entre Élé Consulting et IVB, les participants explorent des pistes techniques pour structurer l’intégration d’assistants IA et de systèmes NLP dans des contextes métiers variés, notamment autour de la gestion de données complexes et de l’automatisation de rapports. Les discussions portent sur des besoins exploratoires en matière de calculs techniques, de réseaux et d’orchestration de workflows.

| # | Sujet | Decision |
|---|---|---|
| 1 | Prise de contact informelle pour affiner la feuille de route collaborative entre Élé Consulting et IVB. L’accent est mis sur l’exploration des besoins techniques non formalisés, notamment en calculs d’études ou réseaux, sans cadre mission précis établi à ce stade. | Aucune décision prise |
| 2 | Synthèse et automatisation de rapports métiers via des outils comme le *Smart Cockpit*, avec une attention portée à la souveraineté des données et à leur adaptation au contexte d’utilisation (ex : RTE). L’objectif inclut aussi la création d’agents capables de proposer des pipelines pour générer des PoC (Proof of Concept) rapidement. | Aucune décision prise |
| 3 | Projet exploratoire sur l’extraction structurée d’informations à partir de documents administratifs scannés, incluant manuscrits ou texte non structuré. L’objectif est d’évaluer la conformité des données extraites (ex : salaires et métiers) via un modèle VLM hébergé localement, couplé à un contrôle d’anomalies et à un dashboard de monitoring. | Aucune décision prise |
| 4 | Intégration d’un MCP (gestion de contenu) pour orchestrer des outils internes ou externes (simulation, bibliographie) afin de générer automatiquement des PoC. L’idée est de combiner une phase de recherche rapide (via des agents NLP) avec l’exécution concrète de simulations ou études, en lien avec des workflows existants. | Aucune décision prise |
| 5 | Exploration du potentiel d’orchestration de données fragmentées (ex : blocs d’alarme, messages) pour les synthétiser et les dispatcher vers des outils NLP ou MCP. Les échanges soulignent aussi la pertinence de travailler sur des cas d’usage liés à l’analyse de texte manuscrit, malgré des travaux en cours sur ces sujets. | Aucune décision prise |
| 6 | Priorisation des besoins exploratoires pour les rapports métiers (ex : pré-rapports ou études de sensibilité) avec une attention portée à l’amont (scénarios, vérifications d’équilibre) et au contrôle humain derrière la génération automatisée. L’objectif est d’éviter une dépendance externe tout en optimisant la robustesse des processus. | Aucune décision prise |

## 4. Plan d'action

Les échanges portent sur l’évaluation des besoins autour de la gestion de contenu (MCP) et la proposition d’ateliers UX pour aligner les visions techniques et métiers, en lien avec le *Smart Cockpit* et les systèmes MCP. Bruno LEMETAYER et Matthieu DUSSART explorent des pistes collaboratives pour structurer ces priorités sans engagement immédiat de décisions formelles.

| # | Action | Responsable | Echeance |
|---|---|---|---|
| 1 | Matthieu DUSSART propose d’engager une réflexion collective sur un cas d’usage MCP, en sollicitant la présentation explicite du contexte par les parties prenantes concernées pour affiner leur vision technique. | Matthieu DUSSART | à discuter lors d’un second échange informel |
| 2 | Jérôme MASSET suggère de reporter toute analyse approfondie sur le MCP tant que les besoins métiers ne sont pas précisés, en attendant une clarification des attentes pour éviter un travail sans fondement concret. | Jérôme MASSET | à vérifier après présentation des travaux MCP |
| 3 | Matthieu DUSSART indique que l’équipe travaille déjà avec des partenaires UX (notamment Olivier Maserol) pour concevoir une *contrôle room* future, et propose d’organiser un atelier dédié à la priorisation de cas d’usage en collaboration avec les parties prenantes. | Matthieu DUSSART | à confirmer selon disponibilité des participants |
| 4 | Une phase informelle de prise de contact et d’échange d’informations est engagée pour recueillir les attentes prioritaires, sans engagement immédiat sur un calendrier précis ou une décision formelle. | Jérôme MASSET et Matthieu DUSSART | — |

