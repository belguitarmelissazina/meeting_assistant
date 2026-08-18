# Compte rendu de reunion

_Type de reunion (orchestrateur)_ : **prise de contact et brainstorming technique**

<!-- Raisonnement orchestrateur (debug, non destine au lecteur final) :
Ce type de réunion combine une phase d’échanges initiaux sur les besoins en IA générative (chunk 0) avec des explorations techniques détaillées autour de l’orchestration, du traitement multimodal et des cas d’usage spécifiques (chunks 2, 5, 6, 8). La structure en **contexte** et **pistes émergentes** permet de capturer à la fois les échanges initiaux sur les rôles et compétences (chunk 0), ainsi que les idées techniques précises pour une collaboration future. Les chunks 3–4, bien qu’indirectement liés à l’automatisation des rapports, ne sont pas prioritaires dans ce cadre car ils relèvent d’un
-->

## 1. Présentation des participants et besoins initiaux en IA générative

- Mathieu agit comme expert Data-IA pour la gouvernance, régulation et analyse métier des projets liés à l’IA générative.
- Maya travaille en IA générative (interne et externe) avec une expertise en deep learning et traitement automatique des langues.
- Bruno et Dinka pilotent la feuille de route Smart Cockpit pour les assistants conversationnels aux opérateurs dans le domaine des soins de conduite.
- Jérôme explore les applications du MCP (modèle conversationnel probable) pour des interfaces quasi conversationnelles fluides avec les outils d’assistance.

## 2. Idées émergentes sur l’orchestration, le traitement multimodal et les cas d’usage

- → **Approche multimodale et prétraitement**
- - Transformation de contenus hétérogènes (textuels + extraits pertinents) en formats actionnables via une phase de prétraitement localisé, notamment pour des modèles hébergés.
- - Utilisation combinée de techniques comme le **RAG** (ranking + vectorisation) et de plateformes d’IA comme Mistral pour optimiser les gains d’usage.
- - Déploiement de solutions pré-entraînées (ex. VLHRM, Vicorne) avec intégration de fonctionnalités de streaming pour la production en temps réel.
- → **Orchestration d’outils spécialisés**
- - Orchestration via **N8N** pour traiter des flux comme les CV, références ou réponses aux appels d’offres (ex. assistance à la rédaction collaborative).
- - Développement d’un outil de génération interactive de résumés de réunions (intégration de notes SharePoint/externes) en vue d’automatiser leur compréhension.
- → **Approche MCP (Management of Complex Projects)**
- - Intégration modulaire pour centraliser des fonctionnalités comme l’enregistrement vocal et la génération de mindmaps via une interface LM, avec un accent sur la souveraineté et la confidentialité des données.
- - Utilisation du MCP pour relier des simulations techniques (ex. études de robustesse énergétique) et préparer des rapports ou pré-rapports validés par des comités.
- → **Limites et contraintes techniques identifiées**
- - Nécessité d’une **cloisonnement strict** des outils (ex. environnement dédié à RTE sans accès depuis d’autres services), pour renforcer la souveraineté.
- - Absence de finalisation de l’orchestration des missions critiques (ex. synthèses, roadmaps opérationnelles) dans les échanges actuels.
- - Dépendance aux PoC existants (agents de planification pour PoC) sans implémentation définitive de MCP ou orchestrations centralisées.

## 3. Prise de contact et prochaines étapes

- Besoin non formalisé : clarification immédiate du cadre technique autour des calculs, études et réseaux pour identifier des pistes complémentaires.
- Retour nécessaire de l’interlocuteur concerné sur les actions réalisées ou retours obtenus dans ces domaines (sans décision formelle).
- Suggestion d’un atelier UX design avec Olivier Maserol et les cabinets externes pour prioriser les cas d’usage MCP/NLP et aligner la vision avec les partenaires.
- Aucune suite définie concernant l’approfondissement des cas d’usage spécifiques sans besoin clair identifié (proposition de SP02).
- Proposition de second échange spécifique entre SP02 et SP00 pour discuter du MCP ou des solutions NLP, mais sans engagement formel.
- Aucune action définie sur la valorisation future des avancées techniques hors MCP dans l’agenda projet (mention implicite de leur présentation ultérieure).

## 4. Note complémentaire : Automatisation des rapports (hors focus principal)

- Méthode : Séparation des chapitres par templates multiples via une chaîne d’agents pour générer des sorties orientées vers la structure prédéfiée du rapport.
- Limite : Absence de vérification chiffrée ou métrique automatique des données extraites hors des slides assignées aux sections, risquant des incohérences non détectées en temps réel.
- Méthode : Utilisation d’artefacts intermédiaires (briques logicielles) pour isoler et tracer chaque section générée, facilitant l’identification des erreurs ou hallucinations par les correcteurs.
- Limite : Non-réconstruction automatique des graphiques à partir de fichiers bruts PPT, dépendance exclusive aux éléments visuels déjà intégrés dans les slides.
- Méthode : Boucle itérative de correction par section via une interface dédiée, où les commentaires humains (basés sur les artefacts générés) orientent la régénération du rapport final.
- Limite : Les corrections restent limitées aux sections individuelles plutôt qu’à l’ensemble du document, ce qui peut entraîner des incohérences transversales non résolues.

