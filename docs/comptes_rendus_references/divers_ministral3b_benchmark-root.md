```markdown
# **Compte rendu - Réunion sur l'IA générative et transformation des documents**

## **Executive Summary**
La réunion a permis d’aborder les besoins en IA générative pour divers cas d’usage métiers, notamment la gestion de données administratives (extraction automatique), l’assistance aux opérateurs via un *Smart Cockpit interactif*, ou encore la production automatisée de rapports structurés à partir de présentations multimodales. Les échanges ont porté sur des projets pilotes comme celui de RTE pour l’analyse d’études équilibre offre-demande, ainsi que sur les méthodologies de classification et versionnage des contenus générés. Aucune décision formelle n’a été prise concernant les actions concrètes, mais plusieurs pistes techniques (orchestration multimodale, intégration API) ont été explorées.

---

## **Contexte & Participants**

**Type de réunion :**
Réunion technique interne pour discuter des applications pratiques de l’IA générative, de la transformation multimodale de documents et de l’intégration d’outils automatisés (ex : rapports à partir de PowerPoint).

**Objectifs principaux :**
- Explorer les cas d’usage métiers en IA générative.
- Analyser les solutions existantes ou en développement pour des projets comme *Smart Cockpit* ou RTE.
- Structurer méthodologiquement la transformation et classification des documents complexes.

**Participants (avec rôles mentionnés) :**
| **Nom**               | **Rôle/Répartition**                                                                 |
|------------------------|------------------------------------------------------------------------------------|
| Expert Dataille        | Gestion des données, cas d’usage IA générative (extraction administrative), conformité. |
| Maya (IV)              | Consultante confirmée, spécialiste en modèles LLM et interaction opérateur-outils.      |
| Mathieu Sartre ("voilà je") | Rôle dans la feuille de route du *Smart Cockpit interactif*.                          |
| BrunibTlier             | Responsable Développement (RD).                                                     |
| Consultante confirmée   | Projets en IA générative, transformation de contenus complexes (ex : rapports RTE).  |
| Général                | Participation aux tests avec transcription vocale via Spitch.                         |
| T                       | Méthodologie de classification des slides pour les rapports.                          |

---

## **Sujets abordés**

### **1. Besoins et cas d’usage en IA générative**
- Présentation des profils professionnels et thématiques :
  - **Expert Dataille** : Extraction automatique de données administratives (salaire, métier) à partir de documents scannés via prétraitement, apprentissage fin et monitoring avec un tableau de bord. Projet passé sur la conformité des données extraites.
  - **Maya** : Intérêt pour les interfaces conversationnelles orchestrant des services ou synthétisant des informations fragmentées (ex : blocs d’alarmes, rapports).
  - **Mathieu Sartre & BrunibTlier** : Focus sur l’assistance aux opérateurs via le *Smart Cockpit interactif* (IA générative + outils multimodaux).

- Points clés :
  - Complementarité entre NLP traditionnel et MCP (*Multi-Purpose Chatbot*).
  - Pistes pour des démonstrations rapides (*POC*) combinant agents logiciels et conversationnels, sans décision formelle.

---

### **2. Positionnement stratégique des solutions d’IA générative**
- Exploration de services spécialisés (ex : *Texaster*), sans mission claire définie.
- Projet chez **RTE** :
  - Analyse de la rentabilité des études équilibre offre-demande (*EOD*).
  - Besoin en versionning et référentiel clair pour industrialiser les processus analytiques.

---

### **3. Transformation multimodale de documents complexes**
- **Projet pilote RTE (Équilibre Offre-Demande)** :
  - Objectif : Automatiser la transformation de fichiers PPT/PPD en fiches synthétiques ou rapports détaillés, incluant une analyse de rentabilité.
  - Étapes clés :
    - Prétraitement : Extraction et catégorisation des slides via *El Power*.
    - Orchestration multimodale : Agents structurant le contenu par sections (rentabilité, scénarios) avec versionnage itératif.
    - Validation humaine : Correction par tranches avant intégration finale.
  - Limites :
    - Absence de chiffrement des données extraites (hors scope).
    - Corrections limitées aux sections plutôt qu’au niveau macro du rapport.
  - Résultat : Accélération de la production en 25 jours sans altérer la qualité, mais nécessitant des améliorations pour généralisation.

---

### **4. Outil génératif pour rapports à partir de présentations**
- Conception d’un outil automatisé :
  - Entrée : Fichiers PowerPoint (PPT) + transcription vocale via Spitch (format DXT).
  - Sortie : Rapports structurés en Markdown, avec boucle de correction itérative.
  - Pipeline en **5 étapes** gérées par des agents pour artefacts intermédiaires.
- Intégrations possibles :
  - Outils internes ou externes (APIs, exportations Microsoft).
  - Système centralisé (*LM*) pour accéder globalement aux outils développés.

---

### **5. Classification et assignation des slides**
- Méthodologie :
  - Description détaillée de chaque slide pour identifier son rôle analytique/descriptif.
  - Assignment systématique à **4 sections prédéfinies** du rapport (critères métiers clarifiés).
  - Préparation de la rédaction finale par section, avec répartition entre agents.

---

### **6. Sélection et adaptation des templates**
- Adaptation des modèles pour rapports automatisés :
  - Robustesse requise pour éviter les erreurs structurelles.
  - Distinction entre rapports d’événements (analyse frontale) et orchestration multi-agents (*MCP*).
  - Renforcement de la souveraineté technique (confidentialité, accès sécurisé).
  - Projet en cours : Agent de planification de blocs avec roadmap automatisée pour projets énergétiques.

---

## **Décisions**
*Aucune décision prise explicitement lors des échanges.*

---

## **Actions définies**

| **Action**                                                                 | **Responsable**       | **Échéance**          |
|-----------------------------------------------------------------------------|-----------------------|-----------------------|
| Développement et intégration de l’outil génératif (rapports à partir de PPT). | Non précisée         | À définir             |
| Test avec transcription vocale via Spitch (exemple sur rapports basés sur PPT). | Général              | À confirmer           |
| Mise en place d’une pipeline en 5 étapes avec gestion des artefacts intermédiaires. | Équipe projet RTE    | À déterminer          |
| Exploration des intégrations API/outils externes (confidentialité, souveraineté). | Expert Dataille       | Prochaine étape      |

---

## **Points d’attention**
- **Risques et limites** :
  - Absence de chiffrement pour les données extraites dans le projet RTE.
  - Corrections limitées aux sections plutôt qu’au niveau macro des rapports.
  - Nécessité de clarifier les critères métiers pour la classification des slides.

- **Prochaines étapes suggérées (non décisionnelles)** :
  - Finaliser la répartition des tâches pour le développement de l’outil génératif.
  - Valider les intégrations techniques avec APIs ou outils externes.
  - Organiser un point d’avancement sur le projet RTE après tests itératifs.

---
```