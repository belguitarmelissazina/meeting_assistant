# Compte rendu de réunion

_Type de réunion_ : **atelier de travail**

_Objectif_ : Identifier et affiner des cas d'usage pour l'intégration de solutions d'IA générative dans les processus internes de RTE, en explorant des pistes techniques et organisationnelles.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a débuté par un tour de table où chaque participant a présenté son expertise en IA générative, notamment autour de projets d'automatisation comme la rédaction de rapports pour RTE ou l'extraction d'informations à partir de documents scannés. Les discussions ont ensuite porté sur l'amélioration des synthèses, la souveraineté des outils et leur cloisonnement pour éviter une utilisation externe. Plusieurs projets ont été évoqués, comme un agent de planification pour automatiser la récupération de bibliographie ou un système basé sur des modèles visuo-linguistiques pour extraire des données administratives. Les participants ont également exploré des cas d'usage pour l'orchestration d'outils de simulation et de synthèse de données via des serveurs MCP ou des solutions NLP. Enfin, des travaux en cours sur la synthèse de textes manuscrits et l'utilisation de LLM ont été mentionnés, avec une volonté de proposer des POC rapides, notamment via des hackathons.

## Sujets abordés

### 1. Tour de table et présentation des cas d'usage initiaux

Un tour de table a permis de présenter les rôles et expertises des participants en IA générative. Maya, consultante confirmée chez Ely, a notamment détaillé son expérience en automatisation de rédaction de rapports pour RTE, en s’appuyant sur des modèles multimodaux et des pipelines d’agents. Elle a souligné l’utilisation de modèles locaux (comme Mistral) avec des techniques de fine-tuning, de RAG et d’orchestration, ainsi que des outils de déploiement comme VLHRM ou Vicorne. Ses projets incluent la transformation de documents complexes en contenus actionnables, avec une industrialisation des processus et une approche modulaire adaptable à différents templates.

Les échanges ont également mis en lumière des cas d’usage concrets, tels que l’automatisation de la génération de rapports à partir de fichiers PPT, intégrant des boucles de correction et une adaptation à des structures prédéfinies. Maya a présenté une pipeline en cinq briques, combinant analyse de slides, assignation de sections, rédaction par étapes, intégration et correction itérative. D’autres projets évoqués incluent un outil de rédaction assistée pour appels d’offres, orchestré via N8N, et un système de synthèse de réunions interactif, en développement, utilisant un MCP pour fédérer plusieurs outils internes. L’accent a été mis sur la modularité, la traçabilité et la possibilité d’adapter les solutions à des besoins métiers variés.

### 2. Souveraineté des outils, orchestration et automatisation des processus

Les échanges ont mis en lumière les enjeux de souveraineté et de cloisonnement des outils au sein de RTE, avec une volonté de maintenir les solutions internes pour éviter toute externalisation. L’accent a été mis sur l’adaptation des synthèses et des propositions aux besoins spécifiques du contexte, tout en garantissant que les outils restent maîtrisés et protégés dans l’environnement RTE.

Un projet d’agent de planification a été évoqué, visant à automatiser la récupération de bibliographie et la création de roadmaps pour des projets, avec une extension future vers l’accès à plusieurs outils de simulation. L’objectif est de proposer une preuve de concept minimale rapidement, notamment via des hackathons, afin de valider l’efficacité de ces pipelines avant un déploiement plus large.

L’intégration de serveurs MCP a également été discutée pour orchestrer des outils de simulation et préparer le lancement d’études, avec des contrôles humains et des ajustements automatisés. Les participants ont souligné l’intérêt d’un MCP pour synthétiser des données disparates, générer des pré-rapports et faciliter la préparation des scénarios avant validation finale. Ces travaux s’inscrivent dans une démarche d’amélioration continue, avec une attention particulière portée à l’état de l’art en R&D.

### 3. Extraction et traitement de données à partir de documents

Un projet a été présenté pour l'extraction d'informations à partir de documents scannés administratifs, qu'ils soient manuscrits ou non. L'objectif était d'extraire des données comme les salaires (nets, bruts, totaux) et les métiers des personnes concernées, puis de classifier les documents. Une approche basée sur des modèles visuo-linguistiques (VLM) a été utilisée pour estimer un pourcentage de conformité des documents par rapport à des intervalles de confiance prédéfinis, permettant ainsi une détection de conformité.

Le projet incluait un prétraitement des documents, l'apprentissage et le fine-tuning de modèles VLM, ainsi que le développement d'un contrôle d'anomalies et d'un tableau de bord pour monitorer la chaîne de traitement. Le modèle était hébergé en local, et des travaux de fine-tuning ont été réalisés pour adapter les modèles aux spécificités des documents, notamment lorsqu'ils étaient rédigés en arabe. Des agents ont été mis en place pour classifier les documents en manuscrits ou non, puis pour déterminer leur type, avec des modèles spécialisés pour certains cas.

### 4. Avancement des travaux et besoins identifiés

SPEAKER_00 a proposé d’engager une réflexion sur un cas d’usage orienté MCP ou de présenter les avancées des travaux en cours. SPEAKER_02 a indiqué qu’aucun besoin clair n’était identifié à ce stade, suggérant de revenir vers eux si des éléments plus précis émergent. Il a également mentionné que des actions étaient déjà prévues pour explorer cette piste, sans qu’un focus immédiat ne soit nécessaire.

SPEAKER_02 a souligné la nécessité d’éviter des échanges sans concrétisation et a proposé de les recontacter une fois des éléments plus précis disponibles. Il a également évoqué les contraintes liées à la disponibilité des opérateurs et à l’ordonnancement des projets en cours.

SPEAKER_00 a partagé une information concernant une collaboration en cours avec des cabinets en UX design, notamment avec Olivier Maserol, et a proposé d’organiser un atelier design pour réfléchir à des cas d’usage et les prioriser. SPEAKER_02 a pris note de cette proposition sans s’engager immédiatement.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Identifier et prioriser les cas d'usage concrets pour l'orchestration via MCP (ex : préparation de simulations, synthèse de données, génération de pré-rapports) | Équipe technique | À définir |
| 2 | Étudier la faisabilité technique d'un serveur MCP capable de se brancher sur des outils internes de simulation et de génération de rapports | Équipe technique | À définir |
| 3 | Analyser les besoins spécifiques en NLP pour la synthèse de textes manuscrits et proposer un plan d'action | Équipe NLP | À définir |
| 4 | Noter le point concernant un éventuel atelier design pour réfléchir à des cas d'usage et les prioriser | SPEAKER_02 | — |
