# Compte-Rendu de Réunion

## Executive Summary

La réunion s'ouvre avec un tour de table où chaque participant se présente : Bruno LEMETAYER et Maya SAHRAOUI (Yele Consulting) détaillent leurs expertises en IA générative, tandis que Nourredine HENKA, Jérôme PICAULT et Jérôme MASSET (RTE) exposent leurs rôles respectifs, notamment sur la feuille de route Smart Cockpit, les LLM/MCP et l'implémentation de réseaux de neurones. Bruno LEMETAYER propose ensuite d'identifier les besoins en IA générative, avec un focus de RTE sur les assistants interactifs pour les opérateurs via MCP. Maya SAHRAOUI présente les projets de Yele Consulting, dont un POC réussi pour l'équipe Équilibre Offre-Demande de RTE, automatisant la génération de rapports en 25 jours. Les discussions abordent ensuite l'orchestration via MCP pour des cas d'usage comme la synthèse générative ou la planification de POC, ainsi que la souveraineté des données pour éviter toute exposition externe. Nourredine HENKA exprime cependant un manque de besoins clairs immédiats, préférant attendre des propositions plus concrètes. La réunion se conclut sur une proposition de Bruno LEMETAYER d'organiser un atelier design pour prioriser les cas d'usage et repenser l'UX de la salle de contrôle du futur.

---

## Contexte & Participants

**Objectif** : Présenter les compétences de Yele Consulting en IA générative, partager les besoins et cas d'usage de RTE, et explorer des pistes de collaboration autour des assistants interactifs, de l'orchestration via MCP et de la souveraineté des données.

| Nom | Rôle | Côté |
|---|---|---|
| Bruno LEMETAYER | Expert Data IA / Manager de la pratique Data IA chez Yele Consulting | prestataire |
| Matthieu DUSSARTRE | Consultant confirmé chez Yele Consulting, spécialisé en IA générative | prestataire |
| Nourredine HENKA | Pilote de la feuille de route Smart Cockpit (assistants interactifs) chez RTE | client |
| Jérôme PICAULT | Responsable de la direction Intelligence Artificielle et Innovation chez RTE, travaillant sur LLM et MCP | client |
| Maya SAHRAOUI | Consultante confirmée en IA générative, docteure en deep learning | prestataire |
| Jérôme MASSET | Expert en implémentation de réseaux de neurones pour l'écosystème RTE, anciennement en exploitation et marché | client |

---

## Tour de table et présentation des participants

La réunion s’est ouverte sur un tour de table permettant à chaque participant de préciser son rôle et ses expertises, posant ainsi les bases des échanges ultérieurs. Bruno LEMETAYER, manager de la pratique Data IA chez Yele Consulting, a initié les présentations en soulignant son expérience en IA générative, notamment dans le cadre de collaborations passées avec Maya SAHRAOUI et Nourredine HENKA sur des projets liés à l’équilibre offre-demande et à la gouvernance des données. Il a également évoqué son implication dans des analyses métiers et des projets d’IA générative, tant en interne qu’en externe.

Maya SAHRAOUI, consultante confirmée en IA générative chez Yele Consulting, a pris la parole pour détailler son parcours : docteure en deep learning et spécialiste du traitement automatique des langues, elle a notamment mené des missions chez RTE aux côtés de Daina et Gérald. Son expertise couvre à la fois les projets internes et les interventions externes, avec une approche centrée sur l’IA générative et ses applications concrètes.

Côté RTE, Nourredine HENKA a présenté son rôle de pilote de la feuille de route Smart Cockpit, dédiée au développement d’assistants interactifs pour les opérateurs en salle de contrôle. Jérôme PICAULT, travaillant au sein de la direction Intelligence Artificielle et Innovation, a précisé son implication dans les LLM et le protocole MCP, tandis que Jérôme MASSET a partagé son expérience en exploitation, marché et implémentation de réseaux de neurones, tout en mentionnant des échanges antérieurs avec Yele Consulting sur des modèles de gestion des congestions. Ce tour de table a permis de clarifier les attentes et les expertises de chacun, facilitant la suite des discussions.

---

## Identification des besoins et attentes en IA générative

Bruno LEMETAYER a initié cette séquence en proposant d’identifier directement les besoins et attentes des participants en matière d’IA générative, afin d’orienter les échanges vers des pistes de collaboration concrètes. Cette approche a permis de recentrer les discussions sur les priorités opérationnelles de RTE, notamment en matière d’assistance aux opérateurs et d’automatisation des tâches répétitives.

Nourredine HENKA a précisé que l’intérêt de RTE se concentre particulièrement sur les assistants interactifs pour les opérateurs, avec un focus sur les interfaces conversationnelles rendues possibles par le protocole MCP (Model Context Protocol). Il a souligné l’enjeu de fluidifier l’interaction entre les opérateurs et leurs outils techniques, tout en garantissant un cadre maîtrisé et sécurisé. Cette clarification a permis de définir un périmètre opérationnel clair pour les échanges ultérieurs.

Les besoins identifiés par RTE s’articulent autour de deux axes principaux : l’amélioration de l’efficacité opérationnelle des équipes en salle de contrôle et la réduction des tâches manuelles répétitives. Cette section a ainsi permis de poser les bases pour une exploration plus approfondie des cas d’usage concrets, en alignant les propositions de Yele Consulting avec les attentes immédiates de RTE.

---

## Présentation des compétences de Yele Consulting en IA générative

Maya SAHRAOUI a détaillé les compétences techniques et l’expertise opérationnelle de Yele Consulting en IA générative, en s’appuyant sur des projets concrets menés par Bruno LEMETAYER. Le cabinet se positionne sur la transformation de documents complexes et hétérogènes en contenus actionnables, qu’il s’agisse d’extraire des informations stratégiques pour la prise de décision ou de générer des synthèses structurées. Les approches adoptées reposent sur l’industrialisation des solutions, avec une forte emphase sur l’utilisation de modèles multimodaux (notamment Qwen2 et Mistral), hébergés localement et fine-tunés selon les besoins des projets. L’intégration systématique de techniques comme le RAG (Retrieval-Augmented Generation), la vectorisation et l’orchestration d’agents spécialisés permet d’adresser des cas d’usage variés, allant de la rédaction automatisée d’appels d’offres à la génération de résumés interactifs de réunions.


### Approches techniques et outils déployés

Les projets présentés par Maya SAHRAOUI illustrent une méthodologie rigoureuse, combinant prétraitements avancés, orchestration via MCP et déploiement via des outils comme VLHRM ou Vicorne. Bruno LEMETAYER a notamment développé une chaîne de traitement pour automatiser la génération de rapports à partir de fichiers PPT, en s’appuyant sur une structure prédéfinie et des règles métier pour garantir la cohérence des livrables. La pipeline mise en œuvre, composée de cinq briques distinctes (analyse des slides, assignation des sections, rédaction par sections, intégration et boucle de correction), permet une production accélérée sans altération de la rigueur. Par exemple, le POC réalisé pour l’équipe Équilibre Offre-Demande de RTE a permis de générer un rapport complet en 25 jours, incluant une interface dédiée pour itérer sur les corrections via des commentaires ciblés. Cette approche modulaire et scalable offre une flexibilité adaptable à des templates variés, tout en maintenant une traçabilité des artefacts pour faciliter les ajustements ultérieurs.

---

## Retour d'expérience sur le POC de génération automatisée de rapports

Bruno LEMETAYER (Yele Consulting) a détaillé le retour d’expérience du Proof of Concept (POC) mené pour l’équipe Équilibre Offre-Demande de RTE, visant à automatiser la génération de rapports à partir de fichiers PPT. Réalisé en 25 jours, ce projet avait pour objectif principal d’accélérer la production des rapports sans compromettre leur rigueur, en standardisant la structure des documents et en intégrant une boucle de correction itérative via une interface dédiée. L’outil développé a été conçu pour gérer plusieurs templates et générer des sorties multiples, soit par adaptation du template existant, soit via un agent dédié. La robustesse de la solution repose sur une séparation de la rédaction en sections, permettant une meilleure gestion des erreurs et une traçabilité accrue des corrections. Cette approche a également facilité l’intégration de commentaires ciblés par les utilisateurs finaux, renforçant ainsi la qualité et la pertinence des rapports générés.


Maya SAHRAOUI (Yele Consulting) a complété cette présentation en soulignant les limites identifiées lors du POC, notamment l’absence de vérification chiffrée des valeurs extraites des graphiques, la reconstruction de graphiques à partir de données brutes hors scope, et une correction limitée aux sections. Malgré ces contraintes, le projet a démontré la valeur ajoutée de l’IA pour ce type de tâche, en automatisant efficacement la production de rapports tout en maintenant un niveau de qualité acceptable. Les échanges ont également mis en lumière la modularité de l’outil, capable de s’adapter à différentes structures de rapports ou de templates, bien que son déploiement actuel reste centré sur un cadre métier précis. Les participants ont salué la rapidité de réalisation du POC et son potentiel d’évolution, notamment pour généraliser son usage à d’autres équipes ou cas d’usage au sein de RTE.

---

## Discussion sur l'orchestration via MCP et cas d'usage de synthèse générative

Nourredine HENKA (RTE) a sollicité Yele Consulting sur les capacités d'orchestration via le protocole MCP, en particulier pour des cas d'usage de synthèse générative à partir de sources de données hétérogènes. Cette demande s'inscrit dans le cadre des besoins de RTE en matière d'agrégation et de synthèse d'informations issues de rapports d'événements ou de documents techniques. Maya SAHRAOUI (Yele Consulting) a répondu en présentant deux projets internes illustrant des approches concrètes d'orchestration, l'un basé sur N8N et l'autre sur MCP.

Le premier projet, développé avec N8N, concerne un outil de rédaction assistée pour les appels d'offres. Il repose sur une architecture modulaire d'agents spécialisés (CV, références, réponses AO) permettant d'automatiser la génération de documents tout en garantissant une robustesse via des artefacts intermédiaires et une traçabilité des erreurs. Maya SAHRAOUI a souligné l'importance de ces garde-fous pour assurer la qualité des livrables, notamment en intégrant des boucles de correction itérative et une validation humaine à chaque étape. Ce projet, mené entre septembre et janvier, a permis de démontrer la faisabilité d'une automatisation partielle tout en maintenant une supervision humaine.

Le second projet, actuellement en développement, vise la génération de résumés de réunions interactifs via MCP. L'outil en cours de déploiement permet d'orchestrer des outils internes ou des APIs pour agréger des notes de réunion depuis SharePoint et produire des synthèses adaptées au contexte. Maya SAHRAOUI a évoqué l'ajout futur de fonctionnalités comme l'enregistrement vocal des réunions ou la génération de mind maps, afin d'enrichir l'interactivité et la compréhension des échanges. Ces initiatives s'alignent sur les attentes de RTE en matière de souveraineté des données, en garantissant un cloisonnement strict des informations au sein de l'environnement client.

---

## Souveraineté et cloisonnement des données dans les projets d'IA générative

Les enjeux de souveraineté des données et de cloisonnement des outils ont été au cœur des échanges, reflétant une volonté partagée par RTE et Yele Consulting de renforcer le contrôle sur les données sensibles et les processus d'IA générative. Bruno LEMETAYER et Maya SAHRAOUI ont souligné l'importance de limiter la dépendance aux solutions externes en intégrant des agents spécialisés directement sur des données internes ou des sources open data énergie. Cette approche vise non seulement à améliorer la confidentialité, mais aussi à gagner en précision en adaptant les modèles aux spécificités des métiers de RTE. Les discussions ont mis en lumière la nécessité de maîtriser l'ensemble de la chaîne, depuis les données jusqu'à l'environnement d'exécution des outils, afin d'éviter toute exposition à des environnements externes.


### Maîtrise des données et des modèles : un impératif stratégique

La souveraineté des données a été présentée comme un levier clé pour RTE, avec une attention particulière portée sur le cloisonnement des outils au sein de l'infrastructure interne. Maya SAHRAOUI a insisté sur l'objectif de conserver les solutions d'IA générative strictement côté RTE, en évitant toute externalisation vers des environnements tiers comme ceux proposés par certains fournisseurs. Cette démarche s'inscrit dans une logique de réduction des risques liés à la confidentialité et à la conformité, tout en garantissant une meilleure adéquation des modèles aux besoins opérationnels. Les échanges ont également révélé une volonté de repenser l'orchestration des outils, notamment via des pipelines dédiés, pour automatiser des tâches comme la génération de bibliographies ou la planification de POC, tout en maintenant un contrôle total sur les données manipulées.


### Perspectives d'intégration et alignement avec les cas d'usage

Les discussions ont permis de clarifier les attentes de RTE en matière de souveraineté, notamment pour des applications comme la synthèse générative ou la planification de projets. Bruno LEMETAYER a évoqué des pistes concrètes, telles que l'intégration de modèles spécialisés sur des données internes, afin de générer des propositions mieux adaptées au contexte opérationnel de RTE. L'objectif est de créer des agents capables de fonctionner en autonomie, tout en restant alignés avec les contraintes techniques et réglementaires de l'organisation. Ces échanges ont également ouvert la voie à des collaborations futures, notamment pour explorer des solutions d'orchestration via MCP, tout en garantissant un cloisonnement strict des données et des outils.

---

## Présentation d'un projet d'extraction d'informations à partir de documents scannés

Maya SAHRAOUI a partagé un projet antérieur à son arrivée chez Yele Consulting, centré sur l'extraction automatisée d'informations structurées à partir de documents administratifs scannés, incluant des supports manuscrits. L'objectif principal consistait à extraire des données clés telles que les salaires (nets, bruts, totaux) et les métiers des individus, tout en classifiant les documents pour évaluer leur conformité via un outil de Vision Language Model (VLM). Ce projet a mis en lumière la capacité de Yele Consulting à traiter des documents complexes, y compris dans des contextes multilingues, comme en témoignent les documents en arabe traités avec succès.


La méthodologie déployée a combiné plusieurs étapes techniques : un prétraitement des documents pour normaliser les entrées, un fine-tuning du modèle Qwen2VL afin d'adapter ses performances aux spécificités des documents, et un contrôle d'anomalies pour détecter les dérives en production. Le déploiement a été accompagné d'un monitoring des performances via un tableau de bord dédié, permettant d'identifier des écarts de conformité ou des baisses de précision. Maya SAHRAOUI a souligné l'importance du fine-tuning pour ce cas d'usage, notamment pour gérer la diversité des formats et des langues, tout en garantissant une extraction robuste des informations.


Ce projet a également permis de démontrer la capacité de Yele Consulting à déployer des solutions d'IA générative en local, sans dépendre de services externes, renforçant ainsi la souveraineté des données. Les résultats obtenus en production ont confirmé l'efficacité de l'approche, avec une détection proactive des dérives, illustrant la maturité des solutions proposées par le cabinet.

---

## Orchestration via MCP pour la préparation de simulations et rapports

Bruno LEMETAYER et Matthieu DUSSARTRE ont exploré l’opportunité d’utiliser le protocole MCP pour orchestrer des outils internes, notamment des simulateurs, dans le cadre de la préparation de rapports et d’études stratégiques. L’approche proposée vise à automatiser la génération d’un plan de travail via un agent, puis à exécuter des simulations et produire des pré-rapports en récupérant les données nécessaires via MCP. Cette méthodologie permettrait de rationaliser des processus complexes, comme la préparation de scénarios, le lancement d’études et la génération de pré-rapports, avant validation finale par les équipes.


Matthieu DUSSARTRE a souligné l’intérêt de cette orchestration pour la rentabilité des moyens de production, où des matrices d’études doivent être déroulées avec des simulations et des contrôles humains intermédiaires. L’automatisation via MCP offrirait une meilleure traçabilité des hypothèses et des données d’entrée (consommation, production, programmation), tout en permettant de jongler entre différents outils comme des simulateurs, des outils d’études ou de visualisation. Cette approche s’inscrit dans une logique d’accélération de la prise de décision, en réduisant les délais de préparation des études et en libérant du temps pour l’analyse critique.


Les échanges ont également mis en lumière des cas d’usage concrets, tels que la préparation de scénarios, l’exécution d’études et la génération de pré-rapports, avec une attention particulière portée à l’équilibre des données et aux contrôles intermédiaires. Bruno LEMETAYER a évoqué la possibilité de brancher MCP directement sur des outils de simulation internes, tandis que Matthieu DUSSARTRE a confirmé l’adéquation de cette approche avec les besoins opérationnels de RTE. Les deux parties ont convenu de la pertinence de poursuivre ces réflexions, notamment dans le cadre de la feuille de route Smart Cockpit.

---

## Retour sur les besoins MCP et NLP pour RTE et proposition d'atelier design

Nourredine HENKA (RTE) a souligné l'absence de besoins clairs et précis concernant l'intégration de solutions MCP ou NLP dans les projets actuels de RTE. Il a indiqué que, bien que des actions soient prévues pour explorer ces technologies, celles-ci ne sont pas encore suffisamment matures pour justifier un engagement immédiat. Cette position s'appuie sur des contraintes opérationnelles, notamment la disponibilité limitée des opérateurs, qui limite la capacité à mener plusieurs projets en parallèle. Il a également insisté sur l'importance d'attendre que des besoins plus concrets émergent avant d'engager des discussions ciblées, afin d'éviter des échanges sans fondement tangible.


En réponse, Bruno LEMETAYER (Yele Consulting) a proposé d'organiser un atelier design dédié à la réflexion sur des cas d'usage, leur priorisation et leur partage avec RTE. Cette initiative vise à co-construire une vision commune autour de l'UX de la salle de contrôle du futur, en s'appuyant sur l'expertise de Yele Consulting en collaboration avec des cabinets spécialisés, dont Olivier Maserol. Maya SAHRAOUI (Yele Consulting) a validé l'intérêt de cette proposition, tout en précisant qu'une validation définitive nécessitera des détails pratiques supplémentaires. Cette approche permettrait de structurer une feuille de route alignée sur les attentes opérationnelles de RTE, tout en explorant des pistes innovantes pour l'intégration de l'IA générative.

---

## Décisions

_Aucune décision actée en séance._

---

## Actions

| # | Action | Responsable | Échéance | Priorité | Dépendances |
|---|---|---|---|---|---|
| 1 | Évaluer la généralisation du POC de génération automatisée de rapports pour d'autres équipes RTE (notamment RD) | Gérald (RTE) | — | medium | — |
| 2 | Yele Consulting à réfléchir à une vision sur l'intégration de MCP ou NLP et à revenir vers RTE si des besoins plus précis émergent | Yele Consulting (Bruno LEMETAYER, Maya SAHRAOUI) | — | medium | — |
| 3 | Organiser un atelier design pour prioriser les cas d'usage et réfléchir à l'UX/UI de la salle de contrôle du futur | Yele Consulting (Bruno LEMETAYER) | — | medium | — |
