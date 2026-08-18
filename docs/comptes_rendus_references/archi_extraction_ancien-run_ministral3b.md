# Compte rendu de réunion

*Source : `C:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\dicte_audio_3.normalized.txt`*

## 2. Executive Summary

Cette réunion vise à établir un échange structuré entre l’Élé Consulting et RTE pour explorer les besoins spécifiques en **IA générative**, notamment autour de la création automatisée de rapports techniques, de l’orchestration de données hétérogènes et de l’amélioration des outils d’assistance aux opérateurs. Les participants ont partagé leurs expériences sur des projets concrets comme l’automatisation de synthèses de fiches ou d’études énergétiques, en mettant en avant les méthodologies déployées pour garantir robustesse et traçabilité des résultats.

L’objectif initial reste une **prise de contact** pour affiner ces besoins et identifier des pistes collaboratives, sans engagement formel sur des missions précises à ce stade. La discussion porte aussi sur l’évaluation des outils comme le MCP ou les approches NLP pour optimiser ces workflows, avec une suggestion d’atelier UX pour prioriser les cas d’usage avant toute décision technique définitive. Aucune action concrète ni décision claire n’a été adoptée lors de cette phase.

## 3. Sujets abordés

### 1. Prise de contact sur les besoins en IA générative – Présentation des projets RTE et ELE

Les participants échangent sur leurs attentes en matière d’IA générative pour automatiser la création de rapports techniques, notamment dans le cadre du projet équilibre offre-demande chez RTE.

- Mathieu, expert Data-IA au sein de l’Élé Consulting, initie un tour de table pour identifier les besoins en IA générative et propose des échanges sur les projets spécifiques des participants.
- Maya, consultante confirmée chez IVB, présente ses compétences en traitement automatique des langues (TAL) et son expérience dans la gestion de projets d’IA générative, incluant des travaux chez RTE pour automatiser la synthèse de rapports complexes à partir de données hétérogènes (fichiers PPT).
- Le projet RTE consiste à automatiser la rédaction de fiches de synthèse et de rapports détaillés sur l’équilibre offre-demande en exploitant les analyses préexistantes (Power) et des fichiers PowerPoint contenant graphiques et textes, avec une boucle de correction collaborative.
- La méthodologie mise en œuvre par Maya inclut cinq étapes : analyse fine des slides via OCR et classification des contenus ; assignation systématique des slides à des sections prédéfinies du rapport selon des règles métiers (ex. : exclusion des données étrangères hors France).
- L’objectif final est de produire un outil prototype fonctionnel en 25 jours, incluant une interface simple pour itérer sur les corrections des membres de l’équipe, avec validation ultérieure par Gérald.

### 2. Robustesse et gestion des erreurs dans l’automatisation de rédaction par templates

Analyse des mécanismes mis en œuvre pour garantir la fiabilité d’un outil automatisant la génération de rapports à partir de multiples templates.

- L’outil permet d’exécuter plusieurs templates distincts pour produire des sorties variées, nécessitant éventuellement une adaptation minimale.
- La séparation de la rédaction en sections et la structure finale du rapport améliorent la gestion des erreurs et offrent une traçabilité par section.
- Des artefacts intermédiaires à chaque étape (briques) facilitent le diagnostic précis des erreurs ou hallucinations, permettant des corrections ciblées.
- Une boucle de correction itérative basée sur les commentaires ajoutés aux sections permet la régénération du rapport selon ces retours humains.
- Les limites techniques mentionnées concernent notamment l’absence d’implémentation de vérifications chiffrées ou de reconstruction graphique à partir de données brutes, hors-scopes initial de la mission.

### 3. Cas d’usage de synthèse et orchestration de données hétérogènes

Discussion sur les besoins en intégration de systèmes pour traiter des sources variées (rapports, événements) via une approche de synthèse bidirectionnelle.

- La question porte sur l’exploitation du sens inverse d’un outil de traitement de données (MCP), notamment pour orchestrer plusieurs briques spécialisées dans la compréhension et la génération de contenus liés aux réunions ou appels d’offres.
- Un projet interne utilise N8N pour orchestrer des agents spécialisés en rédaction assistée, combinant CV, références et réponses à des appels d’offres via une interface modulaire.
- Le second projet cible la génération automatisée de synthèses de réunions, intégrant actuellement des outils internes (comme ceux développés sur Sherpa) pour extraire ou transformer des notes existantes.
- L’objectif est d’étendre cette infrastructure par un MCP afin d’ajouter des fonctionnalités comme l’enregistrement vocal ou la création de mindmaps via une interface LM, en interne et sans dépendre de solutions externes (IPI).
- Ce travail vise à renforcer la souveraineté des données internes, notamment pour des sujets spécifiques liés à l’énergie et aux données ouvertes, avec un accent sur la confidentialité et la précision des résultats.

### 4. Amélioration des synthèses et gestion des outils pour l’orchestration et la planification

Discussion sur l’évolution des méthodes de synthèse, l’adaptation des outils aux besoins spécifiques et la sécurisation de leur utilisation dans un environnement dédié (RTE).

- L’objectif est d’améliorer les synthèses existantes pour en faire des propositions plus complètes et mieux adaptées aux missions actuelles.
- La cloisonnement des outils vise à garantir une souveraineté locale, notamment au sein de RTE, afin qu’ils ne soient pas accessibles hors de cet environnement.
- Pour l’orchestration, deux cas d’usage sont identifiés : ceux déjà en cours et un autre projet de planification autonome (POK), distinct des missions d’orchestration.
- Une idée explorée est la création d’un agent capable de récupérer une bibliographie à partir d’un sujet donné et de proposer une roadmap pour un projet, sans implémentation actuelle d’une fonctionnalité similaire (MCP).
- L’objectif final est de développer une pipeline automatisée permettant de générer rapidement des propositions concrètes (POC) sur la base d’un sujet, en combinant plusieurs outils de simulation.

### 5. Utilisation du R&D pour démontrer des solutions innovantes via l’analyse de données administratives

Discussion sur la mise en œuvre de méthodes de recherche pour identifier des problématiques résolubles par le développement d’un outil logiciel, avec un focus sur un projet spécifique lié à la détection de conformité dans les documents administratifs scannés.

- L’objectif est d’utiliser l’état de l’art en R&D pour identifier des tendances et proposer une démonstration rapide via des agents codant des solutions basées sur des sources externes (comme DRKEVX ou autres).
- Un projet en cours vise à extraire des informations clés (salaire, métier) depuis des documents administratifs scannés, puis à évaluer leur conformité par rapport à un intervalle de confiance défini.
- La partie prétraitement des documents (classification manuelle et automatisée : manuscrit/non-manuscrit, type de document) a été finalisée pour préparer l’apprentissage d’un modèle visuo-linguistique (VLM).
- Le travail porte sur la finetuning du VLM avec les sorties structurées extraites, ainsi que le contrôle des anomalies et le déploiement sur un dashboard pour surveiller les performances en production.
- Ce projet, initialement externe à l’entreprise, a été intégré car il nécessite une intervention continue (filtoning) pour gérer des variations de qualité des données ou des documents rédigés en arabe

### 6. Cas d’usage NLP et MCP discutés pour l’orchestration des études énergétiques

Échange sur les pistes d’utilisation du traitement automatique du langage naturel (NLP) et de la machine à chaînes de processus (MCP) pour structurer et automatiser des workflows liés aux études de rentabilité des moyens de production énergétique.

- Les participants évoquent des cas d’usage centrés sur la synthèse de données fragmentées, comme les blocs d’alarme ou messages, afin de produire des rapports ou des pré-rapports pour les comités.
- L’orchestration des études énergétiques via le MCP est soulignée pour centraliser l’accès aux outils internes (simulations, visualisation) et harmoniser les hypothèses ou scénarios en temps réel.
- Le MCP serait utilisé pour préparer automatiquement les scénarios d’études, vérifier leur équilibre et permettre un contrôle humain final avant validation des résultats pour les plans de production énergétique.
- Les travaux sur les notes manuscrites sont mentionnés comme une piste complémentaire à explorer davantage dans le cadre du NLP, bien que déjà en cours.
- La question des serveurs MCP dédiés est réaffirmée comme faisant partie intégrante de la feuille de route pour permettre des connexions directes avec des outils de simulation et de génération de rapports.

### 7. Évaluation des pistes MCP et proposition d’atelier UX

Discussion sur la nécessité de clarifier les besoins spécifiques liés à l’intégration d’un module de contrôle ou traitement (MCP) dans un cas d’usage, avec une alternative envisagée pour explorer les avancées en design UX.

- SPEAKER_02 propose de prioriser la réflexion sur le MCP après avoir identifié des besoins précis dans le cadre du projet EMCP ou d’autres cas d’usage similaires.
- Aucune idée claire de besoin spécifique émergeant actuellement pour justifier une intégration immédiate du MCP, suggérant un retour ultérieur en cas de précision supplémentaire.
- SPEAKER_00 propose un atelier dédié au design UX pour prioriser et affiner les cas d’usage, en collaboration avec des cabinets spécialisés (comme ceux contactés par Olivier Maserol).
- L’équipe galet travaille sur la conception de l’espace contrôle pour le futur projet, ce qui pourrait alimenter les discussions sur les besoins en UX.
- Aucune décision prise concernant une action immédiate, mais une sollicitation possible de SPEAKER_02 ou des partenaires externes si des éléments concrets apparaissent.

## 4. Décisions

_Aucune décision formellement prise._

## 5. Plan d'attaque

| # | Sujet | Action | Responsable | Échéance |
|---|-------|--------|-------------|----------|
| 1 | Prise de contact sur les besoins en IA générative – Présentation des projets RTE et ELE | Organiser un tour de table avec Mathieu pour identifier les besoins précis en IA générative et prioriser les projets RTE/ELE (équilibre offre-demande, fiches de synthèse) selon les règles métiers définies (ex. : exclusion des données hors France). | Mathieu | dès la fin du tour de table |
| 2 | Prise de contact sur les besoins en IA générative – Présentation des projets RTE et ELE | Finaliser l’analyse fine des slides (OCR, classification) et préparer les règles métiers pour l’assignation systématique aux sections du rapport selon Maya, en collaboration avec l’équipe RTE. | Maya (ou équipe dédiée à la méthodologie) | avant le déploiement du prototype en 25 jours |
| 3 | Robustesse et gestion des erreurs dans l’automatisation de rédaction par templates | Garantir que l’outil prototype inclut une interface simple pour itérer sur les corrections collaboratives et valider par Gérald, avec traçabilité des artefacts intermédiaires (briques) à chaque étape. | Maya ou équipe technique RTE | avant la validation finale du prototype |
| 4 | Robustesse et gestion des erreurs dans l’automatisation de rédaction par templates | — Suggérer à Maya d’intégrer, dès le prototype, des vérifications chiffrées (ex. : cohérence des données) et une reconstruction graphique partielle pour couvrir les limites techniques actuelles (hors-scopes). | — | — |
| 5 | Cas d’usage NLP et MCP discutés pour l’orchestration des études énergétiques | Identifier les besoins spécifiques pour le MCP (ex. : orchestration des études énergétiques, contrôle des scénarios) et prioriser avec SPEAKER_02 après validation du tour de table sur les projets RTE/ELE. | SPEAKER_02 ou équipe dédiée à la réflexion MCP | après 15 jours (si besoins confirmés) |
| 6 | Cas d’usage NLP et MCP discutés pour l’orchestration des études énergétiques | — Proposer d’enregistrer les retours de l’équipe RTE sur les limites actuelles du prototype (ex. : manque de vérifications chiffrées) pour ajuster la feuille de route technique avant validation finale. | — | — |
| 7 | Évaluation des pistes MCP et proposition d’atelier UX | Organiser un atelier UX avec les cabinets spécialisés (Olivier Maserol) pour prioriser et affiner les cas d’usage MCP/EMCP ou similaires, en collaboration avec l’équipe Galet sur la conception de l’espace contrôle. | SPEAKER_00 (ou Olivier Maserol) | dans les 10 jours suivant la confirmation des besoins |
