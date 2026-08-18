# Compte rendu de réunion

_Type de réunion_ : **atelier de travail**

_Objectif_ : Explorer et prioriser des cas d'usage concrets autour de l'IA générative et du MCP, tout en identifiant des pistes de collaboration future entre ELEY Consulting et RTE.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

Cette série de réunions a permis d'échanger sur les besoins et attentes de RTE en matière d'IA générative, notamment via des assistants conversationnels et des outils de synthèse. Plusieurs projets ont été présentés, comme l'automatisation de rapports, un outil d'orchestration souveraine des données, ou encore l'extraction d'informations à partir de documents administratifs. Les discussions ont également porté sur des applications en NLP, MCP et l'intégration d'outils existants pour automatiser des simulations ou optimiser des études. Un atelier design a été proposé pour prioriser les cas d'usage, tandis que certains participants ont exprimé le besoin d'éléments plus concrets avant de s'engager. Bien qu'aucune décision ferme n'ait été prise, des pistes de collaboration future ont été identifiées, notamment autour de l'UX et de la control room du futur.

## Sujets abordés

### 1. Cas d'usage concrets en IA générative et MCP

Lors de la réunion, plusieurs projets et cas d’usage liés à l’IA générative et au MCP (Middleware for Computational Processes) ont été présentés, illustrant les applications concrètes développées ou envisagées. Parmi les exemples marquants, un outil d’automatisation de la rédaction de rapports a été détaillé, notamment pour l’équipe équilibre offre et demande de RTE. Ce projet visait à transformer des fichiers PPT contenant des graphiques et des résultats d’études en rapports structurés, en s’appuyant sur une chaîne de traitement composée de plusieurs agents spécialisés (analyse des slides, assignation aux sections, rédaction, intégration et correction). L’objectif était d’accélérer la production tout en garantissant la traçabilité des informations et en permettant une boucle de correction itérative. D’autres initiatives ont également été évoquées, comme un outil d’orchestration interne pour RTE, conçu pour assurer la souveraineté des données, ou encore un agent de planification automatisé capable de générer des roadmaps et des POC en s’appuyant sur des simulations et des outils existants.

Un autre cas d’usage notable concernait l’extraction d’informations à partir de documents administratifs scannés, y compris manuscrits, dans le cadre d’un projet de détection d’anomalies ou de fraudes. Ce travail a impliqué un fine-tuning de modèles VLM (Vision-Language Models) pour classifier les documents, extraire des données structurées (comme les salaires ou les métiers) et estimer un pourcentage de conformité. Le déploiement en local, couplé à un système de monitoring, a permis de garantir la robustesse et la confidentialité des traitements. Enfin, les discussions ont porté sur des applications en NLP (Natural Language Processing) et en MCP, notamment pour automatiser des simulations, optimiser des études ou orchestrer des outils via des serveurs dédiés, avec une attention particulière portée à l’intégration fluide entre les interfaces conversationnelles et les services techniques sous-jacents.

### 2. Défis techniques et souveraineté des données

Lors des échanges, plusieurs enjeux techniques liés à l’implémentation d’outils d’IA générative ont été abordés, notamment en matière de souveraineté des données et d’adaptation des modèles. Un projet d’orchestration interne pour RTE a été évoqué, visant à garantir la confidentialité et le contrôle des données en les hébergeant localement, évitant ainsi leur exposition à des solutions externes. Cette approche permet de cloisonner les traitements tout en assurant une précision accrue, par exemple en spécialisant les modèles sur des données sectorielles comme celles du domaine de l’énergie.

Le *fine-tuning* de modèles VLM (*Vision-Language Models*) a également été discuté, notamment dans le cadre d’un projet d’extraction d’informations à partir de documents administratifs scannés, incluant des éléments manuscrits. Ce travail a nécessité un prétraitement rigoureux des données, ainsi qu’un ajustement fin du modèle pour améliorer la détection d’anomalies ou de fraudes, par exemple en estimant un pourcentage de conformité des documents analysés. Le déploiement local de ces modèles, couplé à un système de monitoring via des *dashboards*, permet de suivre les performances en production et de détecter d’éventuels *drifts* ou baisses de qualité.

Enfin, l’accent a été mis sur la robustesse des solutions proposées, avec des mécanismes comme la traçabilité des artefacts intermédiaires, la gestion des erreurs ou encore des boucles de correction itératives. Ces garde-fous, intégrés dès la phase de *proof of concept*, visent à assurer une industrialisation progressive des outils tout en maintenant un niveau de rigueur adapté aux exigences métiers.

### 3. Intégration et perspectives technologiques

Lors des intégration ddes outils existants,notamment en NLP et via les serveurs MCP, a été identifiée comme une piste prometteuse pour automatiser des simulations et générer des rapports. Les échanges ont souligné l’intérêt de synthétiser des sources de données disparates – comme des blocs d’alarmes ou des messages fragmentés – pour en extraire des analyses cohérentes, tout en exploitant les capacités des serveurs MCP pour orchestrer des études complexes. L’objectif serait de préparer des scénarios en amont, de lancer des simulations et d’en vérifier l’équilibre avant de produire un pré-rapport, réduisant ainsi la charge de travail manuelle tout en conservant un contrôle humain pour les ajustements finaux.

Cette approche rejoint des cas d’usage évoqués par les participants, comme la navigation entre différentes hypothèses ou stratégies en temps réel, en s’appuyant sur des outils de simulation, d’études ou de visualisation. Bien que les contextes diffèrent selon les équipes, l’idée d’une orchestration fluide entre les données d’entrée, les scénarios et les outils existants a été jugée pertinente, notamment pour optimiser des processus comme la préparation de bilans prévisionnels ou l’analyse de sensibilité. Ces réflexions s’inscrivent dans une vision plus large d’intégration des outils NLP et MCP pour faciliter les analyses futures.

### 4. Collaboration et prochaines étapes

Lors des échanges sur les perspectives de collaboration, SPEAKER_00 a proposé d’organiser un atelier design visant à identifier et prioriser des cas d’usage, notamment autour du MCP. Cette approche permettrait d’aligner les visions des deux équipes et d’explorer des pistes concrètes. SPEAKER_02 a cependant indiqué ne pas disposer de besoins suffisamment précis pour engager une réflexion immédiate, préférant attendre que des éléments plus concrets émergent de leurs propres travaux en cours. Il a souligné que les équipes de RTE étaient déjà engagées dans des explorations internes sur le MCP et que toute collaboration devrait s’inscrire dans un calendrier compatible avec leurs contraintes opérationnelles, notamment la disponibilité des opérateurs.

Par ailleurs, SPEAKER_00 a mentionné une collaboration en cours avec Olivier Maserol sur l’UX de la *control room* du futur, suggérant que cette thématique pourrait également faire l’objet d’échanges futurs. SPEAKER_02 a accueilli cette information avec intérêt, tout en restant prudent sur les modalités pratiques d’un éventuel atelier. Aucune décision ferme n’a été actée, mais les deux parties se sont accordées pour maintenir le dialogue et revenir vers l’autre en cas de besoins ou d’avancées plus définis.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Revenir vers SPEAKER_00 avec des besoins plus précis sur les cas d'usage (MCP ou autres) si ceux-ci se dégagent. | SPEAKER_02 | — |
| 2 | Organiser un atelier design pour réfléchir et prioriser des cas d'usage (proposition à étudier). | — | — |
