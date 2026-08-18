# Compte-Rendu de Réunion

## Executive Summary

La réunion s'ouvre avec un tour de table où Bruno LEMETAYER (Yele Consulting) et Maya SAHRAOUI (Yele Consulting) présentent leurs rôles et expériences en IA générative, tandis que Nourredine HENKA, Jérôme PICAULT et Jérôme MASSET (RTE) détaillent leurs responsabilités respectives, notamment sur les assistants pour opérateurs et l'IA générative. Maya SAHRAOUI expose ensuite plusieurs projets menés pour RTE, dont un POC de génération automatisée de rapports pour l'équipe Équilibre Offre-Demande, réalisé en 25 jours et démontrant la valeur de l'IA pour accélérer la production sans dégrader la rigueur. Elle présente également des outils internes comme un agent de planification de POC et un système de synthèse de réunions via MCP. Les échanges explorent ensuite les potentialités du MCP pour orchestrer des outils de simulation et des workflows complexes, avec des cas d'usage concrets évoqués par Jérôme PICAULT. Bruno LEMETAYER propose un atelier design pour prioriser les cas d'usage, mais RTE souligne l'absence de besoins clairs immédiats sur le MCP et la nécessité de concrétiser les discussions. La réunion se conclut sur une note exploratoire, avec des pistes pour des collaborations futures, notamment autour de la souveraineté des outils et de l'intégration dans l'environnement RTE.

---

## Contexte & Participants

**Objectif** : Présenter les expertises et projets d'IA générative de Yele Consulting à RTE, explorer des cas d'usage concrets pour l'automatisation et l'orchestration d'outils, et initier des collaborations futures autour des assistants conversationnels et de l'innovation.

| Nom | Rôle | Côté |
|---|---|---|
| Bruno LEMETAYER | Expert Data IA Manager, Yele Consulting | prestataire |
| Matthieu DUSSARTRE | Consultant confirmé, Yele Consulting | prestataire |
| Nourredine HENKA | Pilote de la feuille de route Smart Cockpit, RTE | client |
| Jérôme PICAULT | Responsable IA générative (LLM, MCP) et innovation, RTE | client |
| Maya SAHRAOUI | Consultante confirmée en IA générative, Yele Consulting | prestataire |
| Jérôme MASSET | Collaborateur RTE sur l'IA générative | client |

---

## Tour de table et présentation des participants

La réunion s’ouvre sur un tour de table permettant à chaque participant de se présenter et de préciser son rôle dans le cadre des échanges sur l’IA générative. Bruno LEMETAYER, expert Data IA Manager chez Yele Consulting, ouvre le tour de table en introduisant son rôle de manager de la pratique Data IA au sein du cabinet. Il précise ses collaborations avec Maya SAHRAOUI sur les sujets d’IA générative, ainsi que ses interactions avec les équipes R&D et Développement de RTE, notamment sur des projets liés à l’équilibre offre-demande et à la gouvernance des moyens de production.


Maya SAHRAOUI, consultante confirmée chez Yele Consulting, prend ensuite la parole pour détailler son expertise en IA générative, avec une spécialisation en multimodèle et fine-tuning. Docteure en deep learning, elle met en avant son expérience sur des projets menés pour RTE, notamment avec les équipes de Daina et Gérald. Du côté de RTE, Nourredine HENKA, pilote de la feuille de route Smart Cockpit, explique son rôle dans l’assistance aux opérateurs en salle de conduite, tandis que Jérôme PICAULT, responsable IA générative et innovation, détaille ses travaux sur les LLM et le MCP. Jérôme MASSET complète les présentations en évoquant ses liens avec les équipes de RTE, notamment sur des projets antérieurs comme la gestion des congestions. L’échange, marqué par une ambiance collaborative, permet de poser les bases des discussions ultérieures en alignant les expertises de chacun sur les enjeux de l’IA générative.

---

## Présentation des projets d'IA générative de Yele Consulting

Maya SAHRAOUI a exposé les expertises et projets d'IA générative développés par Yele Consulting, en mettant l'accent sur une approche centrée sur la transformation de documents complexes et hétérogènes en contenus actionnables. Ses interventions ont permis de démontrer la capacité à extraire des informations pertinentes pour la prise de décision, créer des fiches de synthèse, ou encore générer des rapports structurés à partir de données multimodales. Ses compétences couvrent notamment le multimodèle, le fine-tuning, le RAG (Retrieval-Augmented Generation), la vectorisation, l'orchestration d'outils, ainsi que le déploiement de solutions comme VLHRM ou Vicorne. L'utilisation de modèles locaux, tels que Mistral, a été soulignée pour répondre aux enjeux de souveraineté et de confidentialité, avec des gains d'usage nécessitant des mécanismes de RAG pour améliorer la précision des réponses générées.


### Projets phares et cas d'usage concrets

Plusieurs projets internes ont été présentés, illustrant l'application concrète de ces expertises. Parmi eux, un outil de rédaction d'appels d'offres, basé sur N8N, a été développé avec plusieurs agents spécialisés (CV, références, réponses aux appels d'offres) pour assister les collaborateurs dans la production de documents. Un autre projet, en cours de déploiement, vise à automatiser la synthèse de réunions via MCP, en intégrant des outils internes et externes pour générer des résumés interactifs et exportables. Enfin, un agent de planification de POC a été évoqué, permettant de proposer des roadmaps pour des projets innovants, avec une perspective d'intégration future de MCP pour orchestrer des outils de simulation et de bibliographie. Ces initiatives visent à accélérer les processus tout en garantissant rigueur, traçabilité et souveraineté des données, en alignement avec les besoins métiers des clients.

---

## Retour d'expérience sur le POC de génération automatisée de rapports pour RTE

Maya SAHRAOUI a présenté un Proof of Concept (POC) de génération automatisée de rapports pour l’équipe Équilibre Offre-Demande de RTE, réalisé en 25 jours. Ce projet visait à accélérer la production des rapports tout en garantissant leur rigueur, en ancrant chaque affirmation générée dans des sources identifiées (figures ou textes extraits des fichiers PPT). L’outil développé repose sur une architecture modulaire en cinq briques distinctes, permettant une gestion fine des erreurs et une traçabilité optimale grâce à la production d’artefacts intermédiaires à chaque étape. Cette approche a notamment facilité l’identification rapide des sources d’erreurs et leur correction ciblée, renforçant ainsi la robustesse du système.


L’outil intègre une boucle de correction itérative, permettant aux membres de l’équipe RTE de commenter directement les sections générées et de relancer une régénération ciblée. La structure du rapport a été standardisée en quatre sections prédéfinies, avec des règles d’assignation automatisées des slides aux sections appropriées, évitant ainsi les incohérences dans la mise en forme. Bien que le POC ait démontré la faisabilité de l’automatisation, certaines limites ont été identifiées, comme l’absence de vérification chiffrée des valeurs extraites des graphiques ou la reconstruction de données brutes à partir des fichiers Excel, ces aspects étant hors scope de la mission initiale. Ces pistes d’amélioration ont été documentées pour des itérations futures, notamment via l’intégration d’agents spécialisés dans la validation des données ou la génération de graphiques à partir de sources brutes.

---

## Exploration des cas d'usage MCP et orchestration d'outils

Les échanges ont permis d’explorer les potentialités du **Model Context Protocol (MCP)** pour orchestrer des outils internes et automatiser des workflows complexes, notamment dans le cadre de simulations énergétiques. **Bruno LEMETAYER** (Yele Consulting) a souligné l’alignement entre cette approche et la feuille de route de Yele Consulting, évoquant un cas d’usage concret où un agent pourrait générer un plan de travail, puis interagir via MCP avec des outils de simulation internes pour exécuter les scénarios proposés. **Jérôme PICAULT** (RTE) a confirmé l’intérêt de cette orchestration pour des études énergétiques, décrivant un processus où le MCP permettrait de préparer des scénarios, lancer des simulations et générer des pré-rapports, réduisant ainsi la charge manuelle en amont des comités de validation.

**Maya SAHRAOUI** (Yele Consulting) a relevé des similitudes entre les propositions de Yele Consulting et des projets internes en cours chez RTE, notamment autour de l’intégration de sources de données disparates (blocs d’alarme, messages, etc.) pour en extraire des synthèses automatisées. Cependant, **Nourredine HENKA** (RTE) a rappelé l’absence de besoins clairs et immédiats sur le MCP, insistant sur la nécessité de concrétiser les discussions avant d’engager des actions. Il a également mentionné des contraintes opérationnelles liées à la disponibilité des opérateurs et à l’ordonnancement des projets, limitant la capacité à absorber de nouvelles initiatives sans priorisation préalable.

Les participants ont convenu de maintenir un dialogue exploratoire, avec une proposition de **Bruno LEMETAYER** pour organiser un atelier design visant à prioriser les cas d’usage potentiels. **Jérôme PICAULT** a suggéré de revenir vers Yele Consulting dès que des besoins plus précis émergeraient, tout en confirmant que des travaux exploratoires sur le MCP étaient déjà prévus en interne. La réunion s’est conclue sur une note ouverte, avec une volonté partagée d’approfondir les échanges une fois des pistes plus tangibles identifiées.

---

## Souveraineté des outils IA et ateliers design

Les échanges ont mis en lumière l’importance stratégique de la souveraineté des outils et des données pour RTE, un critère déterminant pour les collaborations futures. **Maya SAHRAOUI** a souligné que l’objectif était de garantir que les solutions déployées restent strictement internes à l’environnement RTE, évitant ainsi toute externalisation non maîtrisée. Cette approche vise à préserver la maîtrise technique et sécuritaire des outils, notamment dans le cadre de l’orchestration d’IA générative et de workflows complexes. Les participants ont reconnu que cette contrainte était un pilier pour les projets à venir, bien que son implémentation pratique reste à évaluer.

**Bruno LEMETAYER** a proposé un atelier design dédié à la priorisation des cas d’usage, en s’appuyant sur des expertises en UX design et en collaboration avec des partenaires comme Olivier Maserol pour repenser l’expérience utilisateur de la Control Room du futur. Cette initiative a été accueillie favorablement par **Nourredine HENKA**, qui a cependant insisté sur la nécessité d’évaluer la faisabilité opérationnelle avant toute mise en œuvre. Les discussions ont révélé l’absence de besoins immédiats clairement identifiés autour du MCP, ce qui a conduit RTE à privilégier une approche progressive et ciblée.

Les échanges sont restés exploratoires, sans aboutir à des décisions formelles. RTE a exprimé sa volonté de maintenir un dialogue ouvert avec Yele Consulting, tout en soulignant la nécessité de concrétiser les discussions par des actions tangibles. La réunion s’est conclue sur une note constructive, avec une ouverture pour des collaborations futures, notamment autour de l’intégration des outils dans l’écosystème RTE et de l’innovation en matière de souveraineté technologique.

---

## Décisions

_Aucune décision actée en séance._

---

## Actions

| # | Action | Responsable | Échéance | Priorité | Dépendances |
|---|---|---|---|---|---|
| 1 | Présenter les projets d'IA générative de Maya SAHRAOUI à l'équipe de Gérald pour évaluer les suites possibles. | Bruno LEMETAYER | — | medium | — |
| 2 | Évaluer la faisabilité pratique d'un atelier design pour prioriser les cas d'usage. | Nourredine HENKA | — | medium | — |
