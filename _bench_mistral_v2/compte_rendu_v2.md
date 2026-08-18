# Compte rendu de réunion

_Type de réunion_ : **atelier de travail**

_Objectif_ : Identifier et prioriser des cas d'usage en IA générative pour RTE, en s'appuyant sur des retours d'expérience et des démonstrations de solutions existantes.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

_Entreprises_ : Yele Consulting, RTE

## Synthèse

La réunion a réuni des experts en IA générative de Yele Consulting et RTE pour échanger sur des projets concrets, notamment l'automatisation de rapports structurés et l'intégration de serveurs MCP. Maya SAHRAOUI a présenté plusieurs POC réalisés pour RTE, incluant des pipelines d'agents IA et des orchestrations multi-agents, tandis que Bruno LEMETAYER et Matthieu DUSSARTRE ont partagé des besoins et des pistes d'amélioration. Les participants ont discuté de l'adaptation d'outils flexibles, de la souveraineté des données et de l'orchestration d'études énergétiques. Matthieu DUSSARTRE a proposé un atelier design pour prioriser des cas d'usage, mais aucune décision immédiate n'a été prise.

## Sujets abordés

### 1. Contexte et acteurs de l'atelier

Matthieu DUSSARTRE, expert Data & IA Manager au sein de Yele Consulting, a ouvert la réunion en proposant un tour de table pour présenter les participants. Il a détaillé son expertise en IA générative, en équilibre offre-demande et en rentabilité des moyens de base, tout en collaborant avec Maya SAHRAOUI sur ces sujets. Maya SAHRAOUI, consultante confirmée chez Yele Consulting et docteure en traitement automatique des langues, a également pris la parole pour préciser son parcours, notamment ses missions en interne et chez RTE, ainsi que son focus sur l’IA générative.

Bruno LEMETAYER, pilote de la feuille de route Smart Cockpit à RTE, a ensuite présenté son rôle et ses attentes. Il a évoqué son expérience de plus de dix ans sur les assistants interactifs pour les opérateurs, ainsi que son implication dans l’intégration de modèles d’IA générative (LLM, MCP) pour développer des interfaces conversationnelles fluides. Matthieu DUSSARTRE a précisé que l’objectif de cette réunion était d’identifier les besoins et attentes de RTE en matière d’IA générative, afin d’envisager une collaboration future.

### 2. Automatisation de la génération de rapports et pipelines d'agents IA

Maya SAHRAOUI a présenté un projet réalisé pour RTE visant à automatiser la génération de rapports structurés à partir de fichiers PPT. L’objectif était de transformer des documents complexes, majoritairement composés de graphiques et de données hétérogènes, en un rapport complet et exhaustif. Une chaîne de traitement en cinq briques a été développée : analyse des slides (extraction de texte via OCR, classification des figures et description détaillée), assignation automatique des slides aux sections prédéfinies du rapport (avec règles métier pour éviter les erreurs de placement), rédaction section par section (d’abord en points clés, puis en prose structurée), intégration des sections (élimination des redondances et incohérences), et enfin une boucle de correction itérative permettant aux utilisateurs d’ajouter des commentaires et de régénérer les sections concernées. Le projet, réalisé en 25 jours, a intégré des garde-fous pour assurer robustesse et traçabilité, notamment via des artefacts intermédiaires stockés à chaque étape, facilitant ainsi l’identification et la correction des erreurs. L’outil a également permis d’enrichir le rapport avec des transcriptions vocales des présentations, transformées en texte pour ajouter un contexte supplémentaire.

L’adaptation de l’outil a été discutée pour fonctionner sans template prédéfini, en orientant la sélection des chapitres et le contenu via des directives de temps et de structure. Matthieu DUSSARTRE a souligné que l’architecture actuelle, conçue autour d’un template, pouvait être adaptée soit par une simple modification, soit par l’ajout d’un agent dédié à la sélection et à l’assignation des sections. Maya SAHRAOUI a insisté sur les garde-fous implémentés pour garantir la qualité des rapports générés, comme la séparation de la rédaction en sections pour limiter les erreurs et la traçabilité des artefacts, permettant une correction ciblée. Les limites du POC ont été identifiées, notamment l’absence de vérification chiffrée des valeurs extraites des graphiques ou de reconstruction des données brutes, mais ces aspects sont considérés comme des pistes d’amélioration pour des itérations futures.

### 3. Orchestration d'agents IA et intégration de serveurs MCP

Maya SAHRAOUI a présenté plusieurs projets d’agents IA spécialisés développés pour RTE, notamment un agent dédié à l’orchestration de données open data énergie. Cet agent vise à générer des synthèses adaptées au contexte de RTE tout en renforçant la confidentialité et la précision des résultats. Matthieu DUSSARTRE a souligné l’importance du cloisonnement des outils pour garantir une souveraineté des données au sein de RTE, évitant ainsi une exposition externe non maîtrisée. Un autre projet évoqué concerne un agent de planification de POC, conçu pour automatiser la collecte de bibliographie et l’accès à des outils de simulation internes via des serveurs MCP. L’objectif est de proposer un pipeline permettant de générer rapidement un POC minimal sur un sujet donné, facilitant ainsi des initiatives comme les hackathons internes.

Un projet antérieur de détection de fraude sur des documents administratifs scannés a également été mentionné. Maya SAHRAOUI a détaillé le processus, incluant un modèle VLM hébergé en local, un prétraitement des documents manuscrits ou non, et un dashboard de monitoring pour détecter des dérives de performance. Ce projet illustre l’adaptation des outils d’IA générative à des cas d’usage spécifiques, avec une attention particulière portée à la qualité des données d’entrée et à la gestion de documents multilingues. Matthieu DUSSARTRE a relevé l’intérêt de ces travaux pour des applications internes chez Yele Consulting, notamment en matière de fine-tuning et d’intégration de modèles spécialisés.

### 4. Priorisation des cas d'usage et perspectives de collaboration

Matthieu DUSSARTRE a proposé d’engager une réflexion commune sur un cas d’usage spécifique, notamment autour de l’intégration de serveurs MCP, afin d’identifier des pistes de collaboration concrètes. Bruno LEMETAYER a indiqué que RTE ne disposait pas encore de besoins clairement définis sur ce sujet, ni sur d’autres axes comme le NLP, et a suggéré de revenir vers Yele Consulting une fois des éléments plus précis identifiés. Il a également mentionné que des actions étaient déjà prévues en interne pour explorer ces pistes, sans pour autant s’engager immédiatement sur un projet commun.

Matthieu DUSSARTRE a ensuite proposé l’organisation d’un atelier design dédié à la priorisation et à la réflexion sur des cas d’usage, en s’appuyant sur des méthodes d’UX design. Bruno LEMETAYER a reconnu l’intérêt de cette initiative, tout en précisant qu’il ne pouvait pas s’engager immédiatement, compte tenu des contraintes opérationnelles et de la nécessité d’avancer sur d’autres projets en cours. Il a également salué l’initiative de travailler avec Olivier Maserol sur des aspects d’UX design, tout en notant que cette piste pourrait être explorée ultérieurement.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Évaluer la généralisation du POC pour la génération de rapports chez RTE avec Gérald | Matthieu DUSSARTRE | — |
| 2 | Partager le REX du projet avec l'équipe pour analyse des suites possibles | Maya SAHRAOUI | — |
| 3 | Partager un plan de travail détaillé sur l’intégration des serveurs MCP pour l’orchestration d’études et la simulation, incluant les directives générées par un premier agent et leur application via les outils internes | Maya SAHRAOUI | — |
| 4 | Étudier la faisabilité d’un outil de synthèse automatique de données disparates (blocs d’alarme, messages, rapports) pour générer des pré-rapports, en collaboration avec Yele Consulting | Bruno LEMETAYER | — |
| 5 | Explorer les cas d’usage spécifiques liés au traitement de documents manuscrits pour une intégration dans les workflows existants | Bruno LEMETAYER | — |
| 6 | Revenir vers Yele Consulting ou RTE si un besoin précis émerge (MCP ou NLP) | Bruno LEMETAYER | — |
| 7 | Évaluer la faisabilité d'un atelier design pour prioriser des cas d'usage | Matthieu DUSSARTRE | — |
