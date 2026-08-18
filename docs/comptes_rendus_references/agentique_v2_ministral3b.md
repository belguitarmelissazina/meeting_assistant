# Compte rendu de reunion

_Type de reunion_ : **réunion technique IA et orchestration**

_Sujet_ : Les participants échangent sur les besoins en intelligence artificielle générative, traitement du langage naturel (NLP), modèles conversationnels probables (MCP) et solutions d’automatisation pour la gestion de données hétérogènes, notamment dans le cadre de projets internes liés à l’assistance aux opérateurs, la synthèse de réunions ou la conformité administrative.

## 1. Présentation des participants et de leurs rôles dans le domaine IA/Orchestration

- Mathieu – Expert Data-IA à l’Élé Consulting : spécialisé dans la gouvernance, régulation et analyse métier des projets liés à l’IA générative et aux réseaux de neurones.
- Maya – Consultante chez IVB : experte en IA générative (interne et externe) avec une expertise en deep learning et traitement automatique des langues.
- Bruno & Dinka – Pilotes de la feuille de route Smart Cockpit à la RD chez RTE : responsables de l’accompagnement technique des assistants interactifs pour les opérateurs dans le domaine des soins de conduite.

## 2. Enjeux techniques : besoins en NLP, MCP et automatisation des données hétérogènes

=== Synthèse narrative des échanges techniques === **Enjeux identifiés** :

1. **Besoins en IA générative et NLP pour l’assistance aux opérateurs** :
   - Développement d’interfaces conversationnelles fluides (ex. assistants Smart Cockpit) pour les systèmes de gestion des interactions avec les opérateurs, notamment dans le domaine des soins de conduite.
   - Exploration du MCP (modèle conversationnel probable) comme outil pour créer des interfaces quasi-naturalistes et optimiser la fluidité des échanges avec les outils d’assistance.

2. **Automatisation des données hétérogènes** :
   - Transformation de documents complexes en formats multimodaux (textuels + extraits pertinents) via une phase de prétraitement localisé, finetuning sur des plateformes comme QNTubinefiel ou Mistral.
   - Utilisation de techniques comme le RAG (ranking + vectorisation) pour optimiser l’exploitation de données variées (ex. notes manuscrites, blocs d’alarme).

3. **Cas d’usage spécifiques** :
   - Orchestration des outils internes (simulations, MCP) pour gérer des scénarios fragmentés (notes manuscrites, messages d’alarme), notamment dans le cadre de la préparation de rapports énergétiques ou pré-rapports à valider par des comités.
   - Intégration du NLP pour synthétiser automatiquement des données disparates (ex. gestion de textes manuscrits) et faciliter l’ajustement humain des hypothèses avant finalisation.

4. **Priorités techniques émergentes** :
   - Déploiement de solutions pré-entraînées (ex. VLHRM, Vicorne) avec streaming en temps réel pour les applications critiques.
   - Validation par PoC d’intégrations directes entre MCP et serveurs de simulation, prioritairement pour les études énergétiques ou de production.

5. **Lacunes implicites** :
   - Absence de détails sur l’industrialisation des workflows (ex. pipelines automatisés) ou le monitoring des performances en conditions réelles.
   - Nécessité d’affiner la gouvernance et la régulation des projets IA, notamment pour les applications sensibles (conformité administrative).

=== Attentes implicites === :
- Collaboration technique entre experts Data-IA, deep learning et traitement de données hétérogènes pour affiner les PoC sur MCP/NLP.
- Standardisation des méthodes de prétraitement et finetuning pour uniformiser l’exploitation des modèles locaux.
- Priorisation des cas d’usage énergétiques ou opérationnels pour les tests concrets (ex. gestion des alertes, synthèse de rapports).

=== Aucune décision prise ni action définie concernant :
   - Les modalités précises de collaboration entre participants.
   - Les échéances ou ressources allouées aux PoC ou à l’industrialisation des solutions.
   - La validation formelle des besoins en conformité administrative (hors mention explicite dans les échanges).

=== Table des décisions ===
[rows = []]
=== Table des actions ===
[rows = []]

## 3. Pistes explorées pour l’orchestration et la synthèse de données (N8N, MCP, RAG)

- Utilisation de N8N pour orchestrer plusieurs agents spécialisés dans le traitement des CV, références et réponses aux appels d’offres, afin d’aider les collaborateurs à rédiger.
- Développement d’un outil interactif de génération de résumés de réunions, intégrant des outils internes (notamment ceux basés sur les notes du SharePoint) ou externes pour automatiser la compréhension des échanges.

