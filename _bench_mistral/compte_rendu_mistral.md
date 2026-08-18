# Compte rendu de reunion

_Type de reunion_ : **prise de contact**

_Objectif_ : Permettre aux participants de partager leurs expériences et besoins en matière d'IA générative et d'outils associés (MCP, NLP, VLM), tout en identifiant des recoupements potentiels pour des collaborations futures.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthese

Cette réunion a réuni des participants issus de différentes entités pour échanger sur leurs travaux et besoins liés à l'IA générative. Les discussions ont débuté par une présentation des rôles et projets en cours, notamment autour de l'automatisation de la rédaction de rapports, de l'orchestration d'outils, et de l'extraction d'informations à partir de documents. Plusieurs cas d'usage concrets ont été évoqués, comme l'utilisation de VLM pour traiter des documents administratifs ou la planification automatisée de projets. Les échanges ont également porté sur les outils NLP et MCP, avec des retours sur leur intégration dans des processus existants ou futurs, comme la feuille de route Smart Cockpit ou la préparation de simulations. La réunion s'est conclue par des propositions d'ateliers ou de réflexions communes sur des cas d'usage MCP et UX design, sans qu'aucune décision formelle ne soit prise. Les participants ont exprimé des intérêts variés, certains manifestant un besoin immédiat tandis que d'autres préféraient être recontactés en cas de besoin concret.

## 1. Présentations des participants et de leurs projets

La réunion a débuté par un tour de table au cours duquel chaque participant a présenté son rôle ainsi que les projets en cours ou passés liés à l'IA générative et aux outils associés. Ces présentations ont permis de clarifier les expertises et les domaines d'intervention de chacun.

- Jérôme MASSET est expert Data IA et manager de la practice Data IA au sein d'ELEY Consulting. Il travaille sur des projets d'IA générative, notamment avec Maya SAHRAOUI, et collabore avec DELTA côté R&D sur la feuille de route équilibre, gouvernance et régulation, ainsi que sur un projet d'équilibre offre-demande et la rentabilité des moyens de base.
- Maya SAHRAOUI est consultante confirmée chez ELYE. Elle travaille principalement sur des projets d'IA générative, notamment en interne et sur des missions menées chez RTE avec DAINA et Gérald. Elle a réalisé un doctorat en deep learning et traitement automatique des langues.
- Maya SAHRAOUI a évoqué un projet mené au sein de l'équipe équilibre offre et demande de RTE, visant à automatiser la génération d'études EOD sur la rentabilité des moyens de production. Ce projet incluait la transformation de fichiers PPT contenant des graphiques en rapports structurés et exhaustifs, avec une chaîne de traitement basée sur des agents et une boucle de correction.
- Bruno LEMETAYER est à la R&D de RTE et pilote la feuille de route Smart Cockpit interactif, axée sur les assistants pour les opérateurs en salle de conduite.
- Matthieu DUSSARTRE est à la R&D de RTE et travaille depuis plusieurs années sur la thématique des assistants pour les opérateurs. Il s'intéresse également à l'implémentation des réseaux de neurones pour l'écosystème RTE.
- Jérôme PICAULT travaille au sein de la direction intelligence artificielle et innovation. Il se concentre sur des sujets d'IA générative, notamment autour des LLM et MCP.

## 2. Cas d'usage et outils techniques évoqués

Les participants ont partagé plusieurs cas d'usage concrets liés à l'IA générative et aux outils techniques associés, couvrant des besoins variés tels que l'automatisation de tâches, l'extraction d'informations ou l'orchestration d'outils. Ces échanges ont mis en lumière des projets spécifiques, des outils comme les VLM, MCP ou NLP, ainsi que des contraintes techniques particulières.

- Un cas d'usage vise à automatiser la rédaction de synthèses et à proposer des contenus adaptés au contexte, avec une attention portée sur la souveraineté des données et leur cloisonnement selon l'entité utilisatrice (exemple : côté RTE).
- Un projet en cours concerne un agent de planification de PoC, capable de récupérer des bibliographies à partir d'un sujet donné et de proposer une roadmap pour un projet, en s'appuyant sur des outils de simulation.
- L'objectif à terme est d'intégrer un MCP pour permettre à cet agent d'accéder à plusieurs outils et de créer une pipeline automatisée, notamment pour accélérer la réalisation de hackathons ou de démonstrateurs.
- Un projet antérieur a porté sur l'extraction d'informations à partir de documents administratifs scannés, incluant des documents manuscrits, pour en extraire des données comme les salaires, les métiers ou estimer un pourcentage de conformité.
- Ce projet a utilisé un outil VLM pour détecter des anomalies (FdR) et a nécessité un fine-tuning du modèle QuendInfibeVL, ainsi qu'un prétraitement des documents, notamment pour gérer des contenus en arabe.
- Le déploiement du modèle a été réalisé avec VLM et UVCorn, et un dashboard a été mis en place pour monitorer la chaîne de traitement et détecter des dérives de performance.
- Un participant a évoqué des cas d'usage orientés NLP, comme la synthèse de sources de données disparates (blocs d'alarme, messages fragmentés) pour générer des rapports ou des analyses.
- L'orchestration d'outils via MCP a été mentionnée comme une piste pour préparer et lancer des simulations, notamment dans le cadre de la feuille de route Smart Cockpit, avec une intégration possible d'outils de génération de rapports.
- L'idée est d'utiliser un MCP pour préparer des scénarios d'études, les lancer, effectuer des contrôles humains ou automatisés, et générer un pré-rapport pour faciliter la prise de décision (exemple : études de sensibilité ou analyses de robustesse).
- Un participant a souligné l'intérêt de l'orchestration d'études pour naviguer entre des hypothèses, des données d'entrée (consommation, production) et des outils de simulation ou de visualisation, dans un contexte de gestion en temps réel.

## 3. Perspectives de collaboration et prochaines étapes

Les échanges sur les perspectives de collaboration ont porté sur l’identification de synergies autour des outils MCP et des approches UX design, dans l’objectif d’explorer des pistes communes. Plusieurs propositions ont été formulées pour structurer ces réflexions, notamment à travers des ateliers ou des présentations ciblées.

Un participant a suggéré d’organiser un atelier design visant à prioriser des cas d’usage, en s’appuyant sur des échanges avec Olivier Maserol pour intégrer des perspectives UX innovantes. Cette proposition a été accueillie avec intérêt, bien que les contraintes de disponibilité et d’ordonnancement des projets en cours aient été soulignées. Côté MCP, il a été proposé de partager les avancées des travaux pour alimenter une réflexion collective, tout en précisant que les besoins concrets n’étaient pas encore identifiés. Les participants ont exprimé une préférence pour être recontactés en cas de besoins plus précis, afin d’éviter des discussions sans objet défini. La possibilité de solliciter des partenaires externes pour des échanges futurs a également été évoquée, tout en insistant sur la nécessité de concilier ces initiatives avec les priorités opérationnelles en cours.

## 4. Plan d'action

La réunion s'est conclue par des échanges sur les suites à donner, notamment en termes de collaboration autour des cas d'usage MCP et d'ateliers design. Plusieurs engagements et suggestions ont été formulés pour des actions post-réunion.

| # | Action | Responsable | Echeance |
|---|---|---|---|
| 1 | Revenir vers les participants avec des besoins plus précis concernant le MCP ou d'autres cas d'usage si quelque chose se dégage. | — | — |
| 2 | Organiser un atelier purement design pour réfléchir à des cas d'usage et les prioriser. | — | — |

