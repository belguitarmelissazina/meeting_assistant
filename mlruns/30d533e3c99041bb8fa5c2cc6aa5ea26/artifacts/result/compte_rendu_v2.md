# Compte rendu de réunion

_Type de réunion_ : **revue projet et exploration de cas d'usage**

_Objectif_ : Faire un état des lieux des projets en cours en IA générative, identifier des pistes d'amélioration et explorer des cas d'usage concrets pour des applications industrielles et administratives. Valider des orientations techniques et organisationnelles pour des pipelines automatisés.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a débuté par un tour de table où chaque participant a présenté son rôle et ses expertises en IA générative, notamment autour de projets d'automatisation de rédaction de rapports, d'extraction d'informations à partir de documents scannés et d'orchestration de simulations. Les discussions ont porté sur l'adaptabilité des outils à différents templates, l'intégration de boucles de correction et la nécessité de cloisonner les solutions pour préserver la souveraineté des données. Plusieurs projets ont été évoqués, comme un agent de planification automatique (webSir) pour générer des bibliographies et des roadmaps, ainsi qu'un outil utilisant des modèles VLM pour extraire et classifier des informations administratives. Les participants ont également exploré des cas d'usage liés à l'analyse de conformité, à l'orchestration via MCP ou N8N, et à la préparation de pré-rapports automatisés. Une proposition d'atelier design pour affiner les besoins a été suggérée, avec un accord pour revenir avec des précisions avant d'approfondir les discussions.

## Sujets abordés

### 1. Automatisation et orchestration de pipelines pour la génération de rapports et synthèses

Maya (Elya) a présenté un projet d’automatisation de rédaction de rapports pour RTE, visant à transformer des documents complexes et hétérogènes (notamment des fichiers PPT contenant des graphiques et peu de texte) en rapports structurés et actionnables. L’outil développé repose sur une pipeline d’agents multimodaux, intégrant des modèles locaux fine-tunés (dont Mistral) et des mécanismes d’orchestration via N8N ou MCP. La solution permet une adaptabilité aux templates prédéfinis, une assignation automatique des slides aux sections du rapport, et une boucle de correction itérative via une interface dédiée. Les artefacts intermédiaires générés à chaque étape assurent une traçabilité et une robustesse accrues, facilitant les corrections ciblées. Ce projet, réalisé en 25 jours, a démontré la faisabilité d’accélérer la production de rapports sans altérer leur rigueur, tout en explorant des pistes comme l’intégration de transcriptions vocales pour enrichir le contexte.

Par ailleurs, Maya a évoqué d’autres cas d’usage liés à l’orchestration d’agents pour des tâches de synthèse et de génération, notamment un outil interne de rédaction assistée pour les appels d’offres (basé sur N8N) et un projet en cours de génération interactive de synthèses de réunions via MCP. Ces initiatives s’inscrivent dans une démarche de souveraineté technologique, avec un déploiement local des modèles pour préserver la confidentialité des données et une spécialisation progressive des agents sur des domaines métiers (ex : données énergétiques open data). Un agent de planification automatique (webSir) est également en développement pour générer des bibliographies et des roadmaps de projets, avec une future intégration de plusieurs outils de simulation afin de proposer des POC minimaux, notamment dans le cadre de hackathons.

### 2. Extraction et classification d'informations à partir de documents administratifs

Un projet spécifique a été présenté par Maya, portant sur l'extraction d'informations à partir de documents administratifs scannés, incluant des documents manuscrits. L'objectif était d'extraire des données comme les salaires (nets, bruts, totaux) et les métiers des personnes, puis de les classifier pour évaluer un pourcentage de conformité du document. Par exemple, le salaire extrait était comparé à des intervalles de confiance établis à partir de documents précédemment traités, afin de détecter d'éventuelles anomalies ou non-conformités.

Le projet s'appuyait sur des modèles VLM (Vision Language Models), avec une partie dédiée au fine-tuning de ces modèles pour améliorer leur précision. La chaîne de traitement incluait également un prétraitement des documents, une phase de contrôle d'anomalies, et un déploiement en local via des outils comme VLM et UVicorn. Un tableau de bord permettait de monitorer les performances du modèle en production, notamment pour détecter des dérives (drifts) ou des baisses de qualité des résultats. Le projet intégrait aussi une gestion des documents en arabe, nécessitant un fine-tuning adapté.

### 3. Orchestration de simulations et analyse de données via MCP et NLP

Les discussions ont mis en lumière des besoins en orchestration de simulations, notamment dans le domaine énergétique, avec une intégration envisagée de serveurs MCP pour automatiser des workflows. L’objectif serait de préparer des scénarios, orchestrer des études et lancer des simulations en s’appuyant sur des outils internes ou des simulateurs existants. Cette approche permettrait de générer des pré-rapports automatisés, incluant des vérifications d’équilibre des études et des analyses de sensibilité, avant validation humaine.

Un cas d’usage évoqué concerne la synthèse de données disparates, comme des blocs d’alertes, des messages fragmentés ou des notes manuscrites, afin de produire des résumés cohérents. L’intégration de serveurs MCP pourrait faciliter cette orchestration en permettant une interaction fluide entre différents outils, notamment pour naviguer entre des hypothèses variées (consommation, production, programmation, etc.) et générer des stratégies de scénarios adaptés.

### 4. Cas d'usage MCP/NLP et ateliers de conception

Les échanges ont porté sur les explorations de cas d’usage liés à MCP et NLP, sans qu’aucune décision immédiate n’ait été prise. Il a été souligné que les besoins actuels ne sont pas encore suffisamment précis pour engager une réflexion approfondie, et qu’il serait préférable de revenir vers l’équipe avec des éléments concrets avant d’avancer davantage. Une action future consisterait à solliciter un retour une fois des éléments plus ciblés identifiés, afin d’éviter des discussions sans fondement opérationnel.

Par ailleurs, une proposition d’atelier design a été formulée pour réfléchir collectivement à des cas d’usage, en priorisant et structurant les besoins. Cette initiative s’inscrit dans une démarche d’UX design, avec une possible implication d’Olivier Maserol pour encadrer cette approche. L’objectif serait de dégager une vision partagée et de faciliter l’identification de pistes concrètes avant d’engager des travaux supplémentaires.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Présenter les projets restants de Maya lors d'une prochaine réunion pour validation ou approfondissement. | Maya | — |
| 2 | Étudier la faisabilité d'intégrer les projets de Maya (notamment le projet VLM pour documents scannés) dans les initiatives en cours, en tenant compte des contraintes de déploiement local et de qualité des données. | — | — |
| 3 | Noter le point concernant l'atelier design pur pour réfléchir à des cas d'usage et les prioriser. | SPEAKER_02 | — |
| 4 | Tenir informés les partenaires si des besoins plus précis émergent sur MCP ou NLP. | SPEAKER_02 | — |
