# Compte rendu de réunion

*Source : `dicte_audio_3.normalized.txt`*

## 2. Executive Summary

La réunion vise à établir une collaboration entre les participants autour de l’IA générative et des assistants interactifs, notamment pour optimiser les interactions opérateurs-outils, sans définir encore de mission précise ou d’action concrète. Les échanges portent sur des besoins techniques en traitement du langage naturel (NLP) et en modèles conversationnels probables (MCP), ainsi que sur l’exploration de solutions pour des interfaces fluides et automatisées, comme la gestion des congestions ou les synthèses de données complexes. Bien que des expertises variées soient mises en avant—comme celles liées à la gouvernance, la régulation ou l’orchestration de systèmes—, aucune décision définitive n’a été prise concernant un projet structuré ou une priorisation immédiate. Le but reste une prise de contact et une clarification des attentes pour identifier ultérieurement des pistes complémentaires entre les parties prenantes. Aucune action formelle ni calendrier n’est évoqué à ce stade.

## 3. Sujets abordés

### 1. Tour de table sur l’IA générative et les assistants pour la gestion des interactions opérateurs

Les participants échangent sur leurs besoins en IA générative, notamment autour des assistants conversationnels et des interfaces interactives pour les systèmes d’assistance aux opérateurs.

- Mathieu présente son rôle d’expert Data-IA au sein de l’Élé Consulting, spécialisé dans la gouvernance, régulation et analyse métier des projets liés à l’IA générative et aux réseaux de neurones.
- Maya, consultante confirmée chez IVB, travaille sur des projets d’IA générative (interne et externes) avec une expertise en deep learning et traitement automatique des langues.
- Bruno et Dinka, à la RD chez RTE, pilotent la feuille de route Smart Cockpit pour les assistants interactifs aux opérateurs dans le domaine des soins de conduite, depuis plusieurs années.
- Jérôme, désormais dans l’intelligence artificielle et innovation, explore les applications du MCP (modèle conversationnel probable) pour développer des interfaces quasi conversationnelles fluides avec les outils d’assistance.
- L’objectif est d’échanger sur leurs besoins spécifiques en matière de NLP et de MCP afin d’évaluer une collaboration potentielle sur ces sujets techniques.

### 2. Présentation préliminaire des besoins et échanges sur les sujets techniques

Les participants explorent les éléments nécessaires pour définir une mission future en s’appuyant sur les travaux et connaissances de l’interlocuteur concerné.

- Le besoin actuel n’est pas encore clairement défini ni formalisé à ce stade.
- L’objectif initial est d’échanger sur des calculs, études et réseaux pour identifier des pistes complémentaires.
- La rencontre vise à faire connaissance et à recueillir les retours ou actions réalisées par l’interlocuteur sur ces sujets.
- Le retour de la réunion se limite à une prise de contact et à un besoin vague nécessitant une clarification ultérieure.
- Mike a été sollicité pour son expertise dans ce domaine lors d’un précédent contexte de travail.

### 3. Positionnement et compétences en traitement de projets génératifs multimodaux

Présentation des méthodes appliquées pour transformer des contenus complexes en formats actionnables, incluant aspects techniques et industriels.

- Le positionnement adopté consiste à transformer des documents hétérogènes en multimodal (textuel, extraits pertinents) pour faciliter la prise de décision ou créer des synthèses.
- L’intervention inclut une phase de prétraitement important, notamment pour des modèles hébergés localement et finetuning spécifique sur des outils comme QNTubinefiel.
- Utilisation de plateformes d’IA comme Mistral et intégration de techniques comme le RAG (ranking + vectorisation) pour optimiser les gains d’usage.
- Déploiement de solutions comme VLHRM ou Vicorne pour livrer des modèles pré-entraînés, incluant des outils de streaming pour la production en temps réel.
- L’accent est mis sur une approche combinant industrialisation et monitoring, sans préciser les projets spécifiques cités précédemment.

### 4. Automatisation de la rédaction de rapports à partir de fichiers PPT

L’équipe a développé un outil pour générer des études de rentabilité des moyens de production en structurant et automatisant la création de rapports à partir de présentations (fichiers PPT).

- Le projet utilise les fichiers PPT comme entrée principale, analysant chaque slide via une chaîne de traitement avec cinq étapes distinctes.
- L’objectif est d’accélérer la production des rapports tout en préservant leur rigueur grâce à l’intégration directe des affirmations dans les slides correspondantes (textes et graphiques).
- Les fichiers PPT, riches en données hétérogènes (graphiques, peu de texte), sont classés par sections prédéfinies selon une structure de rapport validée a priori avec des règles métier spécifiques.
- L’outil permet une boucle de correction itérative via une interface dédiée : les membres de l’équipe peuvent commenter et corriger les sections générées avant validation finale.
- Une option complémentaire inclut la transcription vocale (fichier TXT) pour enrichir le contexte des slides, testée avec un outil comme Spitch.

### 5. Validation et robustesse de l’outil de génération de rapports par templates multiples

Discussion sur la faisabilité d’un système automatisé utilisant plusieurs modèles pour produire des chapitres distincts, avec mise en avant des approches techniques et limites rencontrées.

- L’hypothèse d’utiliser un agent avec différents templates permet de générer plusieurs sorties adaptées ou orientées vers la sélection des chapitres et leur contenu.
- La séparation de la rédaction par sections et l’assignation des slides à ces sections améliorent la gestion des erreurs, offrant une traçabilité pour les corrections rapides.
- L’implantation de garde-fous (artefacts intermédiaires) facilite le suivi des hallucinations ou erreurs, permettant d’identifier précisément la brique concernée par chaque défaut.
- La boucle de correction itérative repose sur des commentaires par section, permettant une régénération du rapport en fonction des retours humains pour un résultat final robuste.
- Les limites mentionnées incluent le manque de vérification chiffrée des données extraites (hors-scopes), la non-réconstruction de graphiques à partir de fichiers bruts et les commentaires limités au niveau des sections plutôt qu’au rapport entier.

### 6. Cas d’usage et orchestration de systèmes pour la synthèse de données et les réunions

Les échanges portent sur l’exploration des besoins en synthèse de données hétérogènes (rapports, événements) et en automatisation de la génération de résumés de réunions via une orchestration modulaire.

- Le projet interne utilise N8N pour orchestrer plusieurs agents spécialisés dans le traitement des CV, références et réponses aux appels d’offres, afin d’assister les collaborateurs en rédaction.
- Un autre projet actuel vise à développer un outil de génération interactive de résumés de réunions, intégrant des outils internes (comme ceux basés sur des notes du SharePoint) ou externes pour automatiser la compréhension des réunions.
- L’objectif est d’étendre cette orchestration avec un système centralisé (MCP), incluant des fonctionnalités comme l’enregistrement vocal ou la génération de mindmaps via une interface LM, pour améliorer la souveraineté et la confidentialité des données internes.

### 7. Amélioration des synthèses et gestion de projets via outils spécialisés

L’objectif est d’améliorer la qualité des synthèses, adapter les propositions aux contextes spécifiques et renforcer la souveraineté des outils en les limitant à des environnements dédiés.

- Il est demandé d’enrichir les synthèses existantes pour les rendre plus complètes.
- Un outil doit être utilisé de manière cloisonnée, par exemple au sein d’une entité spécifique (ex. RTE) sans extension vers d’autres services.
- L’orchestration des deux missions identifiées n’est pas encore finalisée dans ce contexte.
- Une approche automatisée pour générer une roadmap ou un plan opérationnel minimal à partir d’un sujet donné est envisagée, notamment via des bibliothèques et outils de simulation.
- Un projet en cours (hors orchestration) utilise déjà un agent de planification pour les PoC, sans implémentation de MCP actuelle.

### 8. Utilisation de l'état de l’art et VLM pour la détection de conformité dans des documents administratifs

Ce projet consiste à extraire et analyser des données structurées (comme salaires ou métiers) depuis des documents scannés, en vérifiant leur conformité via un modèle visuo-linguistique.

- L’objectif est d’automatiser l’extraction de données spécifiques (salaires nets/bruts, métiers) à partir de documents administratifs scannés pour évaluer leur cohérence interne.
- Une phase préliminaire inclut la classification des entrées en manuscrits ou non-manuscrits avant traitement spécifique.
- Le projet repose sur un modèle visuo-linguistique (VLM) finetuned, avec une chaîne de prétraitement et contrôle d’anomalies pour détecter les drifts de performance.
- Un dashboard est prévu pour monitorer en temps réel la qualité du traitement et identifier des écarts de conformité dans les résultats produits.
- La solution vise à être déployée localement et à s’adapter à des cas complexes, comme des documents rédigés en arabe ou nécessitant un filtrage manuel ciblé.

### 9. Cas d’usage et feuille de route autour des systèmes MCP et NLP

Discussion sur les besoins en orchestration, synthèse de données et gestion de simulations pour des études techniques liées aux moyens de production ou à la rentabilité énergétique.

- Les participants évoquent des cas d’usage centrés sur l’orchestration des outils internes (simulations, MCP) pour gérer des scénarios fragmentés (notes manuscrites, blocs d’alarme, messages).
- Le MCP est identifié comme un enjeu clé pour préparer et relier les simulations, notamment dans le cadre de la génération de rapports ou de pré-rapports à valider par des comités.
- L’idée est de combiner des outils complexes (études de sensibilité, robustesse) avec une interaction humaine pour ajuster les hypothèses avant finalisation du rapport énergétique.
- Le NLP est souligné comme un complément pertinent aux travaux sur le MCP, notamment pour la synthèse automatique de données disparates ou la gestion de textes manuscrits.
- La feuille de route inclut des PoC (proof of concept) pour tester l’intégration directe avec les serveurs MCP et les outils de simulation, prioritairement dans le cadre des études sur les moyens de production.

### 10. Échanges sur l’intégration du MCP et priorisation des cas d’usage

Discussion entre deux parties pour clarifier les besoins en intégration d’un module spécifique (MCP) ou de solutions NLP, ainsi que la mise en avant des avancées techniques.

- SP02 propose de ne pas approfondir un cas d’usage précis sans besoin clair identifié, pour éviter une discussion non productive.
- SP00 suggère un atelier UX design pour prioriser les cas d’usage et partager une vision commune avec les partenaires externes.
- Aucune décision prise concernant la réflexion sur le MCP ou l’organisation d’un second échange spécifique.
- Les travaux en cours sur des projets internes limitent temporairement les ressources pour explorer ces sujets en priorité.
- SP02 mentionne que les avancées techniques (hors MCP) pourraient être présentées pour leur valorisation future dans l’agenda projet.

## 4. Décisions

_Aucune décision formellement prise._

## 5. Plan d'attaque

| # | Sujet | Action | Responsable | Échéance |
|---|-------|--------|-------------|----------|
| 1 | Automatisation de la rédaction de rapports à partir de fichiers PPT | Itérer sur la boucle de correction avec les membres de l’équipe pour valider et ajuster les commentaires intégrés dans le rapport final (basée sur les artefacts générés par l’outil) | Basile ou Gérald | — |
| 2 | Échanges sur l’intégration du MCP et priorisation des cas d’usage | Revenir vers les partenaires externes pour informer sur les besoins précisés (MCP ou NLP) en fonction des avancées observées | — | — |
| 3 | Automatisation de la rédaction de rapports à partir de fichiers PPT | Évaluer la généralisation de l’outil pour d’autres rapports et types de présentations (sans structure de template prédéfinie) | — | — |
| 4 | Amélioration des synthèses et gestion de projets via outils spécialisés | Faire des propositions plus complètes et mieux adapter les synthèses à notre contexte | — | — |
| 5 | Amélioration des synthèses et gestion de projets via outils spécialisés | Cloisonner l’outil pour qu’il reste côté RTE (sans accès depuis Gaillé) et renforcer la souveraineté liée à son environnement d’utilisation | — | — |
| 6 | Échanges sur l’intégration du MCP et priorisation des cas d’usage | Discuter avec Olivier Maserol et les cabinets de UX design pour prioriser et réfléchir à des cas d’usage via un atelier dédié | — | — |
