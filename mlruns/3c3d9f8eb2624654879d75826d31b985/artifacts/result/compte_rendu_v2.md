# Compte rendu de réunion

_Type de réunion_ : **atelier de travail collaboratif**

_Objectif_ : Identifier et prioriser des cas d'usage concrets pour l'IA générative et les outils d'orchestration (MCP, N8N) au sein de RTE, tout en explorant des solutions souveraines et adaptées aux besoins métiers.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a permis aux participants de présenter leurs expertises et projets en cours liés à l'IA générative, avec un focus sur l'automatisation et l'amélioration des processus internes. Maya Sahraoui a détaillé un projet d'automatisation de génération de rapports pour RTE, utilisant des pipelines d'agents et des modèles multimodaux, tout en discutant de son adaptabilité à différents templates. Les échanges ont souligné l'importance de la souveraineté des outils pour garantir le cloisonnement des données, ainsi que l'exploration de cas d'usage variés, comme la synthèse de données, l'orchestration d'outils ou l'extraction d'informations à partir de documents scannés. Un projet d'agent de planification a été évoqué, avec une première application pour la bibliographie et une extension potentielle à des outils de simulation. La gestion de documents manuscrits ou numérisés, notamment en langues spécifiques comme l'arabe, a également été abordée, incluant des aspects comme le prétraitement, le fine-tuning de modèles et le déploiement avec monitoring. Enfin, la réunion a permis d'identifier des pistes pour intégrer des serveurs MCP et des agents IA dans des processus existants, tout en proposant un atelier design pour prioriser les cas d'usage les plus pertinents.

## Sujets abordés

### 1. Cas d'usage et applications métiers de l'IA générative

Lors des échanges, plusieurs cas d’usage concrets pour l’IA générative et les outils d’orchestration ont été identifiés, avec une attention particulière portée à leur adaptabilité aux différents contextes métiers. Maya Sahraoui a présenté un projet d’automatisation de la génération de rapports pour RTE, reposant sur des pipelines d’agents et des modèles multimodaux. L’outil, conçu pour transformer des fichiers PPT en rapports structurés, a démontré sa capacité à s’adapter à des templates prédéfinis tout en permettant une boucle de correction itérative. Les participants ont souligné la flexibilité de cette approche, qui pourrait être étendue à d’autres formats ou à des scénarios sans template fixe, en intégrant par exemple un agent dédié à la sélection des structures de rapport. Ce projet a également mis en lumière l’intérêt d’une orchestration plus large, notamment pour préparer en amont les simulations et les études nécessaires à la génération de rapports, en automatisant la préparation des scénarios et des données d’entrée.

Les discussions ont également porté sur d’autres cas d’usage, comme la synthèse de données hétérogènes ou l’orchestration d’outils via des serveurs MCP. Un projet d’agent de planification a été évoqué, visant à proposer des POC minimaux à partir de sujets donnés, avec une première application centrée sur la bibliographie et une extension potentielle à des outils de simulation. L’objectif serait de créer une pipeline automatisée pour accélérer les processus internes, notamment lors des hackathons. Les participants ont également exploré des pistes pour intégrer des agents IA dans des processus existants, comme la navigation entre des outils de simulation et de visualisation, ou la génération de synthèses à partir de données disparates, tout en garantissant la souveraineté des outils utilisés pour cloisonner les données. Ces échanges ont permis d’identifier des opportunités pour améliorer l’efficacité des processus métiers tout en adaptant les solutions aux spécificités des différents contextes.

### 2. Traitement et extraction d'informations à partir de documents

Un projet dédié à l’extraction d’informations à partir de documents administratifs scannés a été présenté, visant à automatiser la classification et l’extraction de données structurées telles que les salaires (nets, bruts, totaux) ou les métiers mentionnés. L’outil, basé sur des modèles VLM (Vision-Language Models), intègre également une fonction de détection de conformité en comparant les données extraites avec des intervalles de confiance prédéfinis pour chaque métier, permettant ainsi d’identifier des anomalies ou des incohérences. Ce projet a nécessité un travail approfondi sur le prétraitement des documents, souvent hétérogènes, incluant des cas de manuscrits ou de textes numérisés, ainsi qu’un fine-tuning des modèles pour améliorer la précision des extractions.

La chaîne de traitement développée comprend plusieurs étapes clés : l’apprentissage et le fine-tuning des modèles VLM pour obtenir des sorties structurées, un contrôle d’anomalies pour valider la cohérence des données, et un déploiement en production avec des outils comme Uvicorn, accompagné d’un dashboard de monitoring. Ce dernier permet de suivre les performances du modèle en temps réel et de détecter d’éventuels *drifts* ou baisses de qualité. Le projet a également pris en compte des spécificités linguistiques, notamment des documents rédigés en arabe, nécessitant un fine-tuning adapté pour garantir la robustesse des extractions. La gestion des documents manuscrits a été abordée via une classification préalable (manuscrit vs. dactylographié) et l’utilisation de modèles dédiés pour les cas complexes.

### 3. Souveraineté, sécurité et intégration des outils

Les échanges ont mis en avant l’importance cruciale de la souveraineté des outils utilisés au sein de RTE, notamment pour garantir le cloisonnement des données et éviter toute diffusion externe. Cette préoccupation s’inscrit dans une volonté de maîtriser l’environnement technologique, en privilégiant des solutions internes ou souveraines, comme les serveurs MCP ou les outils d’orchestration tels que N8N. L’objectif est de s’assurer que les données sensibles, qu’elles soient métiers ou opérationnelles, restent protégées et ne soient pas exposées à des risques liés à des plateformes externes.

La discussion a également souligné l’adaptation de ces solutions aux besoins spécifiques de RTE, tout en tenant compte des contraintes liées à la protection des données. Par exemple, l’utilisation d’outils comme MCP permet d’envisager des interfaces quasi conversationnelles pour interagir avec des services internes, tout en maintenant un contrôle strict sur les flux d’informations. Cette approche vise à concilier innovation et sécurité, en intégrant des briques technologiques souveraines dans les processus existants, sans compromettre la confidentialité ou l’intégrité des données.

### 4. Méthodologie et priorisation des projets

Les échanges ont porté sur les modalités de collaboration pour affiner les besoins en outils MCP et NLP, sans aboutir à des décisions concrètes. Il a été convenu que les participants reviendraient vers l’autre partie uniquement si des besoins plus précis se dégageaient, afin d’éviter des discussions trop théoriques. La priorisation des projets a également été évoquée, soulignant les contraintes liées à la disponibilité des opérateurs internes et à l’ordonnancement des tâches en cours.

Une proposition d’atelier design a été formulée pour réfléchir à la priorisation des cas d’usage et partager une vision commune. Bien que l’idée ait été jugée intéressante, aucune réponse immédiate n’a pu être apportée, les participants devant d’abord évaluer sa faisabilité pratique. Cette approche pourrait s’inscrire dans une démarche plus large, incluant des réflexions sur l’expérience utilisateur (UX) pour des projets comme la *control room* du futur.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Noter le point concernant la proposition d'un atelier design pour réfléchir à des cas d'usage et les prioriser | SPEAKER_02 | — |
| 2 | Revenir vers l'autre partie si des besoins plus précis en MCP ou NLP émergent | SPEAKER_02 | — |
