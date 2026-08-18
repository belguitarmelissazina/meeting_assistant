# Compte rendu de reunion

_Type de reunion (orchestrateur)_ : **prise_de_contact**

<!-- Raisonnement orchestrateur (debug, non destine au lecteur final) :
Ce type de réunion se caractérise par un échange informel entre participants pour établir une connexion technique et identifier des pistes collaboratives sans engagement formel. Le sommaire montre des échanges sur les besoins, compétences et projets transversaux autour de l’IA générative, du traitement multimodal et des outils d’assistance aux opérateurs. La structure en sections doit refléter cette phase exploratoire : 'Tour de table' pour contextualiser les profils et intérêts, puis 'Sujets explorés' pour synthétiser les échanges techniques sans décisions ni actions définies. Les chunks sont répartis pour couvrir à la fois l’aspect humain (expertise des participants) et technique (méthodes appliquées).
-->

## 1. Présentation des participants et besoins initiaux

- - **Mathieu** : Expert Data-IA chez Élé Consulting, spécialisé en gouvernance, régulation et analyse métier des projets liés à l’IA générative et aux réseaux de neurones.
- - **Maya** : Consultante confirmée chez IVB, experte en IA générative (interne et externe), avec une expertise en deep learning et traitement automatique des langues.
- - **Bruno et Dinka** : Pilote la feuille de route Smart Cockpit pour les assistants interactifs aux opérateurs dans le domaine des soins de conduite depuis plusieurs années.
- - **Jérôme** : Explore les applications du MCP (modèle conversationnel probable) pour développer des interfaces quasi conversationnelles fluides avec les outils d’assistance.
- Besoin commun : Évaluer une collaboration sur les sujets techniques liés au NLP et au MCP.

## 2. Points techniques abordés lors de la réunion

- **Besoins non formalisés**
- - Besoin vague nécessitant une clarification ultérieure (calculs, études, réseaux pour identifier des pistes complémentaires).
- - Échanges préliminaires visant à recueillir les retours ou actions réalisées par l’interlocuteur sur ces sujets.
- - Objectif initial : exploration technique sans définition précise de la mission future.
- - Mike sollicité pour son expertise dans un contexte précédent (non précisé ici).
- **Méthodes et outils techniques appliqués**
- → **Prétraitement des données multimodales**
- - Transformation de contenus complexes en formats actionnables (textuel + extraits pertinents) via une phase préliminaire.
- - Utilisation de RAG (ranking + vectorisation) pour optimiser les gains d’usage avec des modèles hébergés localement et finetuning spécifique (QNTubinefiel).
- - Déploiement de solutions comme VLHRM ou Vicorne pour livrer des modèles pré-entraînés, incluant des outils de streaming en temps réel.
- → **Automatisation de la rédaction de rapports à partir de PPT**
- - Chaîne de 5 étapes : analyse slide → intégration directe dans le rapport (textes et graphiques).
- - Classage des fichiers PPT par sections prédéfinies selon une structure de rapport validée a priori.
- - Boucle de correction itérative via une interface dédiée pour les membres de l’équipe (Basile ou Gérald).
- - Option complémentaire : transcription vocale (fichier TXT) avec un outil comme Spitch.
- → **Orchestration et gestion de systèmes spécialisés**
- - Utilisation d’N8N pour orchestrer plusieurs agents (traitement de CV, références, appels d’offres).
- - Développement d’un outil interactif de résumés de réunions intégrant des outils internes/externes (notes SharePoint, enregistrement vocal).
- - MCP comme système centralisé pour l’enregistrement vocal et la génération de mindmaps via une interface LM.
- - PoC en cours avec un agent de planification pour les PoC (sans implémentation MCP actuelle).
- → **Détection de conformité via VLM**
- - Extraction et analyse de données structurées (salaires, métiers) depuis des documents scannés (manuscrits ou non-manuscrits).
- - Chaîne de prétraitement incluant classification + finetuning d’un modèle visuo-linguistique.
- - Contrôle d’anomalies pour détecter les drifts de performance et un dashboard en temps réel.
- → **Synthèse de données et gestion de projets**
- - Orchestration modulaire via MCP pour relier simulations, rapports ou pré-rapports (scénarios fragmentés : notes manuscrites, blocs d’alarme).
- - NLP utilisé pour la synthèse automatique de données disparates ou la gestion de textes manuscrits.
- - PoC prioritaires sur l’intégration avec les serveurs MCP et outils de simulation (études sur les moyens de production).
- **Projets transversaux identifiés**
- - Étude de rentabilité des moyens de production via automatisation de rapports à partir de PPT (chaîne de 5 étapes + boucle de correction).
- - Développement d’un outil de résumés interactifs de réunions (orchestration N8N + outils internes/externes).
- - Validation et robustesse de l’outil par templates multiples (séparation des sections, garde-fous pour corrections rapides).
- **Limites identifiées**
- - **Automatisation de rapports PPT** : vérification chiffrée des données hors-scopes non implémentée ; reconstruction graphique impossible à partir de fichiers bruts ; commentaires limités aux sections.
- - **Orchestration MCP** : orchestration non finalisée entre missions identifiées (synthèse + gestion de projets).
- - **Conformité via VLM** : adaptation limitée aux documents manuscrits en arabe ou nécessitant un filtrage manuel ciblé.
- - **Synthèses et adaptations contextuelles** : besoin d’enrichir les synthèses sans précisions sur la méthode d’adaptation aux contextes spécifiques (ex. cloisonnement par RTE).

## 3. Suites et prochaines étapes envisagées

Aucune décision définitive n’a été prise concernant l’intégration du module spécifique (MCP) ou la réflexion sur ses besoins associés. Aucune échéance ni responsable désigné pour une clarification formelle de ces sujets.

