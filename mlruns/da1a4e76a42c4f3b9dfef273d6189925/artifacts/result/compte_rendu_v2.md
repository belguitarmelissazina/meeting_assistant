# Compte rendu de réunion

_Type de réunion_ : **atelier de travail**

_Objectif_ : Co-construire et affiner des solutions techniques autour de l'IA générative pour répondre aux besoins spécifiques de RTE, en explorant des cas d'usage concrets et des pipelines innovantes.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

Les participants, issus de différents horizons techniques, ont présenté leurs expertises et projets en IA générative, notamment des outils de rédaction automatisée, d'extraction de données ou de planification. Les échanges ont porté sur l'adaptabilité des solutions, leur robustesse et leurs limites, avec une attention particulière à la souveraineté des données et à la confidentialité. Plusieurs pistes ont été explorées, comme l'orchestration d'agents (MCP, N8N), l'utilisation de modèles VLM pour l'analyse de documents, ou encore la création de pipelines automatisées pour accélérer des processus internes. Des discussions ont également abordé des cas d'usage spécifiques, tels que la génération de synthèses ou la planification de roadmaps, tout en soulignant l'importance de cloisonner les outils au sein de RTE. Bien que des propositions comme un atelier design aient émergé, aucune décision formelle n'a été actée, reflétant une dynamique de co-construction et d'exploration collective.

## Sujets abordés

### 1. Cadrage stratégique et enjeux organisationnels

Un tour de table a été organisé en début de réunion pour permettre à chaque participant de présenter son rôle et ses expertises en IA générative et assistants conversationnels. SPEAKER_00, expert data IA manager, a évoqué ses collaborations avec Maya sur des projets d'IA générative et avec d'autres équipes sur des sujets liés à la gouvernance et à l'analyse métier. Maya, consultante confirmée, a partagé son expérience en IA générative, notamment sur des projets menés chez RTE, et son expertise en traitement automatique des langues. SPEAKER_02, pilote de la feuille de route Smart Cockpit, a détaillé son implication dans les assistants interactifs pour les opérateurs, tandis que SPEAKER_03 a abordé ses travaux sur les réseaux de neurones et les assistants conversationnels. SPEAKER_04 a complété en mentionnant son expérience dans le développement de modèles comme MCP et son interaction avec les équipes de RTE sur des sujets connexes.

Les échanges ont ensuite porté sur les besoins et attentes en matière d'IA générative, avec un accent particulier sur les assistants interactifs et les modèles MCP et LLM pour améliorer l'interface utilisateur. SPEAKER_02 a souligné l'intérêt pour des interfaces quasi conversationnelles, permettant une interaction fluide entre les opérateurs et leurs outils. Les participants ont également discuté des collaborations potentielles entre les équipes, tout en reconnaissant l'absence de besoins clairs et précis à ce stade. SPEAKER_02 a proposé de revenir vers les équipes uniquement en cas de besoins identifiés, afin d'éviter des discussions sans concrétisation.

Enfin, SPEAKER_00 a proposé l'organisation d'un atelier design, en collaboration avec des experts en UX, pour prioriser des cas d'usage et réfléchir à une nouvelle approche utilisateur pour la salle de contrôle du futur. Cette proposition a été notée avec intérêt par SPEAKER_02, qui a reconnu l'utilité potentielle d'un tel atelier, tout en indiquant qu'une réponse formelle serait donnée ultérieurement. Aucune décision n'a été actée à l'issue de ces échanges, reflétant une dynamique d'exploration collective.

### 2. Automatisation de la rédaction et pipelines génératives

L’outil de rédaction automatisée présenté par SPEAKER_01 repose sur une pipeline structurée en cinq briques pour générer des rapports à partir de fichiers PPT, avec pour objectif d’accélérer leur production tout en garantissant la rigueur et la traçabilité des informations. La première étape consiste à analyser chaque slide des fichiers PPT (extraction de texte via OCR, description des graphiques, classification des contenus) afin de produire des artefacts détaillés. Ces artefacts alimentent ensuite une phase d’assignation des slides aux sections prédéfinies du rapport, en appliquant des règles métier pour éviter les incohérences (ex : exclusion des graphiques comparatifs hors de France dans la section « hypothèses de coût »). La rédaction s’effectue ensuite section par section, d’abord sous forme de *bullet points* pour structurer le fond, puis en prose pour enrichir la forme. Une intégration finale regroupe les sections et élimine les redondances, avant de permettre une boucle de correction interactive où les utilisateurs peuvent commenter des sections spécifiques pour régénérer le contenu.

Pour renforcer la robustesse, chaque étape de la pipeline génère des artefacts intermédiaires stockés et versionnés, offrant une traçabilité des erreurs et une possibilité de correction ciblée. Cette approche permet de limiter les hallucinations et de faciliter les itérations, bien que certaines limites aient été identifiées : l’outil ne vérifie pas les données chiffrées extraites des graphiques, ne reconstruit pas ces graphiques à partir de données brutes, et ne permet pas encore de commentaires globaux sur l’ensemble du rapport. La correction itérative, bien que limitée aux sections, offre déjà une base pour des améliorations futures, comme une validation humaine à chaque étape ou une adaptation à des templates variés, comme évoqué lors des échanges.

### 3. Souveraineté des données et agents spécialisés

Les échanges ont mis en lumière des projets visant à renforcer la souveraineté et la confidentialité des données énergétiques, notamment par l’intégration du LNM directement sur des données open data. L’objectif est de développer un agent spécialisé capable de générer des données précises et adaptées aux besoins spécifiques de l’association, en s’appuyant sur des modèles internes pour éviter toute externalisation. Cette démarche s’inscrit dans une logique de maîtrise des outils et des environnements, comme illustré par la comparaison avec des solutions existantes, afin de garantir une confidentialité renforcée et une meilleure précision des résultats.

Par ailleurs, un projet en cours porte sur la création d’un agent de planification pour automatiser la bibliographie et élaborer des roadmaps. L’outil, actuellement en développement, permettrait de récupérer automatiquement des références à partir d’un sujet donné et de proposer une roadmap pour la mise en place d’un projet. À terme, l’intégration de plusieurs outils, dont des simulateurs, est envisagée pour enrichir les fonctionnalités. L’objectif est de proposer une pipeline minimaliste générant un POC (Proof of Concept) sur un sujet donné, afin d’accélérer les hackathons internes et de fluidifier les processus de planification.

### 4. Extraction d'informations et vision par ordinateur

Un projet présenté par Maya a porté sur l'extraction d'informations à partir de documents scannés, notamment administratifs, en utilisant des modèles de vision par ordinateur (VLM). L'objectif était d'extraire des données structurées, comme les salaires nets, les métiers ou d'autres métadonnées, puis d'évaluer la conformité des documents en comparant ces informations avec des intervalles de confiance prédéfinis. Le projet incluait un prétraitement des documents, un apprentissage et un fine-tuning des modèles VLM, ainsi qu'un déploiement avec un tableau de bord de monitoring pour détecter des dérives de performance en production.

Le pipeline développé intégrait également une étape de contrôle d'anomalies et une classification préalable des documents en manuscrits ou non manuscrits, suivie d'une classification par type de document. Certains cas spécifiques nécessitaient des modèles dédiés, tandis que d'autres s'appuyaient sur des approches plus générales. Enfin, le projet a souligné l'importance de la qualité des données d'entrée, notamment lorsque les documents étaient rédigés en arabe, justifiant ainsi un fine-tuning adapté.

### 5. Orchestration de simulations et analyse de données

Les échanges ont porté sur des cas d’usage liés à l’orchestration de simulations et à l’analyse de données disparates, notamment via des outils MCP et des modèles de langage. L’accent a été mis sur la synthèse de sources variées, la gestion d’hypothèses et la préparation de rapports pré-études. SPEAKER_00 a évoqué l’intérêt d’un serveur MCP pour automatiser des tâches complexes, comme la préparation de scénarios, le lancement d’études et la vérification de leur équilibre avant validation humaine. L’objectif serait de générer un pré-rapport intégrant les résultats des simulations, les analyses de sensibilité et les premières conclusions, afin de faciliter la prise de décision pour les comités.

SPEAKER_02 a souligné la pertinence de ces approches pour naviguer entre des hypothèses multiples, notamment en temps réel, en récupérant et en croisant des données d’entrée (consommation, production, programmation, etc.). L’idée serait de définir des stratégies de scénarios, de jongler entre simulateurs, outils d’études et de visualisation, et de structurer une pipeline automatisée pour accélérer ces processus. Les deux intervenants ont convergé sur l’intérêt d’un tel système, bien que SPEAKER_02 ait également mentionné des travaux en cours sur le NLP, notamment pour l’analyse de textes manuscrits, comme piste complémentaire.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Identifier et prioriser les cas d’usage concrets pour l’orchestration de simulations via MCP (ex : gestion d’hypothèses, préparation de rapports pré-études) | Équipe technique / Gérald | À définir |
| 2 | Étudier la faisabilité technique d’un serveur MCP capable de se brancher sur des outils de simulation internes et de générer des directives pour des agents | Équipe technique | À définir |
| 3 | Explorer les potentialités du NLP pour la synthèse de données fragmentées (ex : blocs d’alarme, messages, notes manuscrites) en complément des travaux existants | Équipe NLP | À définir |
