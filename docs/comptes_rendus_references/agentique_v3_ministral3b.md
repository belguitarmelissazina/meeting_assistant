# Compte rendu de reunion

_Type de reunion_ : **réunion technique IA et orchestration**

_Sujet_ : Les participants échangent sur les besoins en intelligence artificielle générative, traitement des données multimodales (textuelles, visuelles), automatisation de synthèses (rapports, réunions) et intégration de systèmes comme le MCP pour améliorer l’efficacité opérationnelle dans divers contextes industriels ou administratifs.

## 1. Contexte technique : IA générative et réseaux multimodaux

Lors d’un échange technique, **Mathieu** présente les projets en intelligence artificielle générative qu’il a menés chez Ely et dans des missions antérieures. Il met l’accent sur son approche globale adoptée depuis son intégration à l’entreprise : transformer des contenus complexes et hétérogènes en formats multimodaux actionnables (extraction de réponses pertinentes, création de fiches synthétiques). Ses compétences incluent notamment la **multimodalité**, avec une expertise dans le traitement local de modèles génératifs comme Mistral. Il souligne également l’importance du prétraitement, du RAG (*Retrieval-Augmented Generation*), et des outils d’orchestration pour optimiser les processus. Parmi ses expériences, il mentionne des projets où il a déployé des systèmes comme **VLHRM** ou Vicorne, ainsi que des solutions de livraison en temps réel (streaming). L’industrialisation et le monitoring sont des éléments centraux dans sa méthodologie pour garantir la robustesse des applications développées.

## 2. Automatisation des synthèses et rapports (PPT, réunions)

- Automatisation de la génération de rapports à partir des fichiers PowerPoint (PPT) pour les études de rentabilité des moyens de production, en collaboration avec l’équipe équilibreoffre et demande.
- Objectif principal : accélérer la production des rapports sans altérer leur rigueur, tout en ancrant chaque affirmation générée dans le rapport aux figures ou textes associés dans les slides originales.
- Structure du rapport prédéfinie en quatre sections distinctes (ex. hypothèses de coût, comparaison France/Europe), avec une classification des slides pour éviter leur inclusion inappropriée dans certaines parties.
- Pipeline composée de cinq briques principales pour traiter chaque fichier PPT et générer le rapport final :
- - **Analyse légère par slide** : Extraction exhaustive du contenu textuel (via OCR) et analyse des graphiques, avec classification des slides en types analytiques ou descriptifs.
- - **Assignement des slides aux sections** : Détermination automatique de l’appartenance d’une slide à une section spécifique grâce à des règles métier (ex. exclusion des résultats France/Europe dans les hypothèses de coût).
- - **Rédaction par section** : Production initiale en bullet points, puis transformation en texte structuré pour chaque section, séparant ainsi le fond de la forme.
- - **Intégration des sections** : Fusion des parties rédigées et suppression des redondances ou incohérences entre les sections.
- Entrées principales : fichiers PPT originaux et optionnel, une transcription vocale en fichier TXT (testé avec un modèle de reconnaissance vocale comme Spitch).
- Sortie principale : rapport final exportable au format DOCX, incluant une boucle de correction itérative via des commentaires sur les sections.
- Optionnalité d’ajout d’un template pour adapter l’outil à d’autres structures de rapports, sans nécessiter de réinventer la chaîne complète (ex. un seul rapport avec directives temporelles et contenus spécifiques).
- Robustesse garantie par :
- - Séparation des étapes de traitement pour faciliter les corrections locales (ex. correction d’une slide affectée à une section).
- - Artefacts intermédiaires stockés après chaque brique, permettant la révision ou modification directe avant l’intégration suivante.
- - Validation humaine itérative sur chaque niveau de production (bullet points par section, intégration finale).
- Limites mentionnées mais hors-scopes de cette première itération : vérification chiffrée des données extraites des graphiques et reconstruction de ces derniers à partir de fichiers Excel.
- Boucle de correction limitée aux commentaires sur les sections, sans possibilité d’appliquer des corrections globales au rapport entier (à implémenter ultérieurement).
- Durée du projet : 25 jours incluant ateliers, validé par un retour de l’équipe et une boucle de feedback avec Gérald.

## 3. Orchestration MCP, NLP et cas d’usage industriels

Les échanges portent sur l’intégration des systèmes d’IA générative et multimodale pour améliorer l’efficacité opérationnelle, en particulier dans les contextes industriels ou administratifs. Voici les points clés identifiés lors de ces discussions techniques :

**1. Recherche d’état de l’art et démonstration technique** :
- Les participants soulignent la nécessité d’explorer rapidement les avancées récentes (état de l’art) pour résoudre des problématiques spécifiques, notamment via des sources comme le **DRKEVX** ou d’autres ressources.
- L’objectif est de produire une démonstration rapide (**Quick and Dirty**) en codant des agents capables d’appliquer ces connaissances, avant de passer à une phase plus approfondie d’ingénierie logicielle.

**2. Projet spécifique sur la détection de conformité documentaire** (Maya) :
- **Objectif** : Extraire et structurer des informations critiques (ex. salaires nets/bruts, métiers) à partir de documents administratifs scannés (manuscrits ou non).
- **Approche technique** : Utilisation d’un modèle **VLM** (visuo-linguistique) pour évaluer la conformité des données extraites par rapport à un intervalle de confiance défini.
- **Étapes détaillées** :
  - Prétraitement des documents (classification manuelle/non manuscrite, puis typologie documentaire).
  - Définition fine du modèle VLM pour optimiser la sortie structurée des extractions d’informations.
  - Contrôle d’anomalies et déploiement sur un **dashboard** pour monitorer les drifts de performance (ex. détection de dégradations dans les résultats en production).
- **Particularités** : Le projet est hébergé localement, avec une approche de *fine-tuning* adapté aux contraintes spécifiques des données (ex. documents rédigés en arabe).

**3. Cas d’usage et orchestration MCP/NLP** :
- **Focus sur l’automatisation des synthèses fragmentées** :
  - Synthétiser des blocs d’alarme, messages ou notes manuscrites dispersées pour faciliter leur analyse collective.
  - Exemple concret : Réorganisation des données manuscrites en vue de leur traitement par des agents NLP (ex. classification métiers/salaire).
- **Orchestration des simulations énergétiques** :
  - Intégration d’un **serveur MCP** pour orchestrer des études techniques (simulations, analyses) et préparer des pré-rapports.
  - Scénario type :
    1. Génération de directives par un premier agent (ex. hypothèses ou scénarios).
    2. Récupération via le MCP d’outils internes (simulateurs, visualisateurs) pour exécuter ces études avec les données proposées.
    3. Contrôle humain final sur l’équilibre des scénarios et validation avant rendu (BP énergétique).
- **Interopérabilité** : Navigation en temps réel entre hypothèses, données d’entrée (consommation/production), outils de simulation et visualisation pour ajuster dynamiquement les stratégies.

**4. Pistes explorées** :
- La souveraineté des systèmes repose sur l’hébergement local du modèle VLM et la gestion fine des *fine-tuning* adaptés aux contextes spécifiques (ex. langues régionales).
- L’interopérabilité est assurée par une architecture modulable, combinant MCP pour l’orchestration et NLP pour le traitement des données.

**Enjeux communs** :
- **Automatisation** : Automatiser la détection de conformité documentaire ou la synthèse de fragments techniques sans sacrifier la qualité humaine (ex. contrôle des drifts).
- **Souveraineté** : Éviter les dépendances externes via des solutions locales et personnalisables.
- **Interopérabilité** : Faciliter l’intégration entre outils métiers (simulateurs, visualisateurs) et systèmes d’assistance aux opérateurs.

*Aucune décision ni action définie explicitement sur ces points lors de cette réunion technique.*

## 4. Autres suggestions et échanges secondaires

- Les participants expriment un **besoin de clarification des attentes** concernant les projets d’IA générative et les besoins spécifiques en traitement multimodal (textuel, visuel) pour améliorer l’efficacité opérationnelle.
- Une **prise de contact informelle** est initiée pour échanger sur les cas d’usage potentiels liés à la mise en œuvre du système MCP (Modèle de Communication Professionnel). Aucun besoin précis n’est encore formalisé.
- L’idée d’un **atelier collaboratif dédié au design des cas d’usage** est évoquée, notamment pour prioriser et structurer les besoins en lien avec l’UX/UI design. Ce projet serait proposé par le côté « galet » (mentionné sans précision supplémentaire).
- Aucune décision prise concernant la validation ou l’organisation de cet atelier.
- Aucune action définie pour approfondir les échanges sur les besoins en MCP ou NLP à ce stade.

