# Compte rendu de réunion

_Type de réunion_ : **prise de contact et revue de projets**

_Objectif_ : Présenter les participants et leurs projets respectifs autour de l'IA générative, notamment pour identifier des synergies et des besoins communs en automatisation et outils d'IA.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a permis une prise de contact entre les participants, incluant des représentants de RTE et d'Ely Consulting, autour de projets d'IA générative. Maya SAHRAOUI (Ely Consulting) a présenté un projet d'automatisation de rédaction de rapports pour RTE via une chaîne de traitement IA, tandis que Bruno LEMETAYER et Jérôme PICAULT (RTE) ont exprimé des besoins en synthèse de données et interfaces conversationnelles. Les discussions ont porté sur des outils d'IA pour l'orchestration, la synthèse de données et l'analyse de documents, avec une emphase sur la souveraineté et l'intégration locale. Plusieurs cas d'usage ont été évoqués, comme la planification, la génération de rapports et l'analyse de conformité, avec une priorité donnée aux serveurs MCP pour interconnecter des outils internes. Aucune décision concrète n'a été actée, mais une proposition d'atelier design pour prioriser les cas d'usage a été évoquée. Les participants ont convenu de revenir vers l'autre partie en cas d'émergence de besoins plus précis.

## Sujets abordés

### 1. Présentation des participants et de leurs projets en IA générative

La réunion a débuté par un tour de table permettant aux participants de se présenter. Maya SAHRAOUI, experte en IA générative et consultante confirmée chez Ely Consulting, a détaillé son parcours en deep learning et son expérience sur des projets d'IA générative, notamment avec RTE. Bruno LEMETAYER, pilote de la feuille de route Smart Cockpit chez RTE, a évoqué son travail sur les assistants interactifs pour les opérateurs, tandis que Jérôme PICAULT, travaillant sur des sujets d'IA générative et de modèles de langage (LLM), a souligné son intérêt pour les interfaces conversationnelles via les serveurs MCP.

Maya SAHRAOUI a ensuite présenté un projet d'automatisation de rédaction de rapports pour RTE, réalisé en 25 jours. Ce projet visait à transformer des fichiers PPT contenant des données hétérogènes (graphiques, textes) en rapports structurés et actionnables. La chaîne de traitement développée incluait des étapes d'OCR, de classification des slides, d'assignation automatique des sections, de rédaction par sections, et d'intégration finale avec une boucle de correction. L'outil permettait également d'ajouter des transcriptions vocales en entrée pour enrichir le contexte. Ce projet a démontré la faisabilité de l'automatisation tout en maintenant une traçabilité et une robustesse via des artefacts intermédiaires et des règles métier.

### 2. Orientations stratégiques et priorités pour les outils d'IA

Les échanges ont mis en lumière une orientation stratégique centrée sur la souveraineté des outils d'IA et leur intégration locale, avec une priorité accordée aux serveurs MCP pour interconnecter des outils internes. Plusieurs cas d'usage ont été évoqués, notamment l'orchestration de processus, la synthèse de données disparates (blocs d'alarmes, messages fragmentés), l'analyse de documents (scannés ou manuscrits), ainsi que la planification et la génération de rapports. L'analyse de conformité, illustrée par un projet d'extraction d'informations et de détection d'anomalies sur des documents administratifs, a également été soulignée comme un domaine d'intérêt.

La discussion a souligné l'importance de cloisonner les outils pour garantir leur utilisation exclusive au sein de RTE, évitant ainsi une dépendance externe. Les serveurs MCP ont été identifiés comme une solution clé pour orchestrer des outils complexes, notamment dans le cadre de simulations et de préparation de rapports, en permettant une interaction fluide entre différents systèmes internes. Les participants ont également évoqué la nécessité de prioriser les cas d'usage, avec une proposition d'atelier design pour affiner cette sélection.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Prendre contact avec Maya (Ely Consulting) pour échanger sur les suites possibles du projet RTE (automatisation de rapports) | Bruno (RTE) | À définir |
| 2 | Étudier l'adaptation de l'outil de Maya pour des templates multiples ou une sélection automatique de structure de rapport | Maya (Ely Consulting) | À définir |
| 3 | Explorer les cas d'usage MCP pour les assistants opérateurs (interfaces conversationnelles, orchestration de briques) | Jérôme (RTE) | À définir |
| 4 | Étudier la faisabilité d'un serveur MCP pour interconnecter des outils internes de simulation et de génération de rapports | SPEAKER_00 | non définie |
| 5 | Évaluer l'intégration des outils de synthèse automatique pour les rapports et les données disparates (ex : blocs d'alarmes, messages fragmentés) | SPEAKER_02 | non définie |
| 6 | Analyser les besoins pour un outil de traitement de documents manuscrits et scannés, incluant classification et extraction d'informations structurées | SPEAKER_01 | non définie |
| 7 | Noter le point concernant une éventuelle proposition d'atelier design pour réfléchir à des cas d'usage et les prioriser. | SPEAKER_02 | — |
| 8 | Tenir informé l'autre partie si des besoins plus précis (MCP ou NLP) émergent. | — | — |
