# Compte rendu de réunion

_Type de réunion_ : **revue projet et ateliers de priorisation**

_Objectif_ : Échanger sur les projets en cours en IA générative, identifier des cas d'usage concrets pour RTE, et esquisser des pistes de collaboration future autour des outils MCP et NLP.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a débuté par un tour de table où chaque participant a présenté son rôle et ses expertises en IA générative, avec un focus sur des projets comme l'automatisation de rapports pour RTE et des assistants conversationnels. Les échanges ont souligné l'importance de l'adaptabilité des solutions aux templates de rapports et la souveraineté des outils au sein de RTE. Plusieurs projets ont été évoqués, notamment un agent de planification, un outil de génération de bibliographie et de roadmaps, ainsi qu'un démonstrateur basé sur l'état de l'art pour résoudre des problématiques via R&D. Un projet de détection de fraude sur documents administratifs a également été détaillé, avec des défis liés à la qualité des données et à la gestion de documents en arabe. Les discussions ont convergé vers l'intérêt d'un MCP pour orchestrer des études et préparer des scénarios, avec une proposition d'atelier design pour prioriser les cas d'usage. Aucune décision concrète n'a été actée, mais des pistes de réflexion et de collaboration futures ont été esquissées.

## Sujets abordés

### 1. Tour de table et présentation des projets en cours

Le tour de table a permis de présenter les rôles et expertises des participants en IA générative. [SPEAKER_00], expert data et manager de la pratique DataIa au sein d'Élé Consulting, a évoqué son travail sur des projets d'IA générative, notamment avec Maya sur l'automatisation de rapports pour RTE et des analyses orientées métiers. Maya, consultante confirmée chez IVB, a détaillé son parcours en deep learning et traitement automatique des langues, ainsi que son expérience sur des projets d'IA générative, dont un mené chez RTE. [SPEAKER_02], méthodologiste à la R&D, a présenté son implication dans la feuille de route Smart Cockpit, axée sur les assistants conversationnels pour les opérateurs, avec une expertise en implémentation de réseaux de neurones. [SPEAKER_03], travaillant sur des sujets liés aux LLM et MCP au sein de la direction Intelligence Artificielle et Innovation, a partagé son expérience sur des modèles conversationnels et son implication dans des échanges sur des outils développés pour la gestion des congestions.

Les échanges ont mis en lumière des besoins en automatisation de rapports et en assistants conversationnels, avec un accent sur l'adaptabilité des solutions aux templates de rapports. Maya a détaillé un projet réalisé pour RTE, visant à automatiser la génération de rapports à partir de fichiers PPT, en structurant le contenu selon des sections prédéfinies et en intégrant une boucle de correction pour itérer sur les sections générées. L'outil développé, basé sur une pipeline de cinq briques (traitement des slides, assignation des sections, rédaction par section, intégration et correction), permet de transformer des documents hétérogènes en rapports actionnables, avec une traçabilité des artefacts intermédiaires pour faciliter les corrections. Les discussions ont également abordé la possibilité d'adapter l'outil à différents templates, bien que le cadre initial ait nécessité une structure précise pour répondre aux besoins métiers.

### 2. Projets techniques et défis opérationnels

Un projet de détection de fraude sur documents administratifs scannés a été présenté, reposant sur un outil de type VLM (Vision Language Model). L’objectif était d’extraire des informations structurées (salaire net, brut, métier, etc.) à partir de documents scannés, puis d’évaluer leur conformité en comparant les données extraites avec des intervalles de confiance prédéfinis. Le projet intégrait un prétraitement des documents, incluant une classification en manuscrit ou non manuscrit, ainsi qu’un fine-tuning du modèle VLM pour optimiser l’extraction des données.

La chaîne de traitement comprenait également un contrôle d’anomalies, un déploiement du modèle avec des outils comme VLM et UVCorn, et un dashboard de monitoring pour suivre les performances en production. Des alertes étaient générées en cas de dérive (*drift*) des résultats. Le projet a souligné les défis liés à la qualité des données d’entrée, notamment la présence de documents en arabe, nécessitant un fine-tuning adapté. Certains documents manuscrits ont également requis des modèles spécialisés ou des approches hybrides.

### 3. Cas d'usage et orchestration avec MCP/NLP

Les échanges ont porté sur les cas d’usage potentiels pour les outils d'orchestration (MCP) et de synthèse (NLP), notamment dans le cadre de l'automatisation des simulations et de la préparation de rapports. Un participant a évoqué l'intérêt d'un MCP pour orchestrer des études complexes, en permettant de préparer des scénarios, de lancer des simulations via des outils internes, et de générer des pré-rapports. Cette approche vise à faciliter le travail en amont, avec une validation humaine avant finalisation, afin d'optimiser le processus de décision.

Un atelier design a été proposé pour prioriser les cas d’usage, en s’appuyant sur des méthodes d’UX design. Cette initiative pourrait permettre d’identifier des besoins concrets et de concrétiser des pistes de collaboration futures, notamment en intégrant des outils internes et en améliorant l’interaction entre les différents systèmes. Aucune décision n’a été actée, mais les pistes esquissées ont été jugées pertinentes par les participants.

### 4. Souveraineté des outils et pipelines rapides

Les échanges ont porté sur l’amélioration des synthèses produites par les outils d’IA générative, avec un accent sur leur adaptation au contexte spécifique de RTE. L’objectif est de proposer des synthèses plus complètes et mieux alignées sur les besoins opérationnels. Par ailleurs, la question de la souveraineté des outils a été abordée, avec une volonté de cloisonner leur utilisation au sein de l’environnement RTE pour éviter toute externalisation non maîtrisée.

Un projet d’agent de planification a été évoqué, visant à automatiser la récupération de bibliographie et la génération de roadmaps pour des projets donnés. À terme, l’intégration d’un agent capable d’interfacer plusieurs outils, dont des simulateurs, est envisagée pour accélérer la mise en place de preuves de concept (POC). Cette approche s’inscrit dans une logique de pipelines rapides, notamment pour répondre aux besoins des hackathons internes.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Prendre contact avec Maya pour échanger sur les détails techniques du projet RTE et évaluer une possible collaboration ou adaptation pour d'autres besoins. | SPEAKER_00 | — |
| 2 | Documenter les cas d'usage identifiés par Bruno (synthèse de rapports, assistants conversationnels) pour une analyse ultérieure par l'équipe Ely Consulting. | SPEAKER_00 | — |
| 3 | Étudier la faisabilité d'intégrer un agent de sélection de templates dans la solution existante pour répondre à des besoins sans structure de rapport prédéfinie. | Maya | — |
| 4 | Prendre contact avec les interlocuteurs pour informer d'éventuels besoins précis liés au MCP ou au NLP | SPEAKER_02 | non définie |
| 5 | Évaluer la faisabilité et l'intérêt d'un atelier design pour prioriser des cas d'usage | SPEAKER_00 | non définie |
