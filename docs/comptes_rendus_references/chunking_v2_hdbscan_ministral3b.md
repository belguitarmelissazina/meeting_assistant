```markdown
# **Compte rendu – Réunion sur les projets IA et MCP**

---

## **Executive Summary**
La réunion a exploré plusieurs axes clés liés à l’intelligence artificielle, notamment :
- La validation des **descriptions techniques pour les modèles d’IA** (agents, groupes hypothétiques) et la mise en œuvre de l’outil **MCP** (Moyens de Production), incluant une matrice pré-rapport pour orchestrer les simulations et études de rentabilité.
- L’évaluation des **cas d’usage spécifiques** (ex. : Marketplace Client Provider, synthèse de réunions) et la collaboration avec des experts externes (ILEI) pour affiner ces applications.
- La présentation des **compétences en IA générative** chez IELI et leur adéquation avec les besoins R&D (RTE), notamment via des projets comme l’orchestration d’appels d’offres ou la génération de rapports analytiques.
- Les discussions sur les **méthodes hybrides** (automatisation + intervention humaine) pour corriger les erreurs dans la rédaction de rapports, avec une attention particulière à la traçabilité et aux garde-fous techniques.

Aucune décision formelle n’a été prise, mais des pistes d’action ont émergé pour prioriser certains projets en fonction des besoins métiers et des contraintes ressources.

---

## **Contexte & Participants**

### **Type de réunion**
Réunion technique interne entre :
- **R&D (RTE et autres entités)** : Bruno Le Bétillier (pilote *Smart Cockpit Interactive*), Mathieu Sartre, expert en réseaux de neurones.
- **Équipe Data/IA** : Jérôme Assé (expert Data), consultante confirmée chez IELI (Maya Saraouli).
- **Collaborateurs externes** : Olivier Mazerolle (UX/UI), Gérald (référence interne pour généralisation des rapports).

### **Objectifs**
1. Valider les **descriptions techniques** pour guider les modèles d’IA et explorer l’outil MCP.
2. Prioriser les cas d’usage en IA générative et synthèse de données (ex. : rapports, orchestration).
3. Aligner les avancées IELI avec les feuilles de route R&D (Smart Cockpit Interactive, POC end-to-end).

### **Participants mentionnés**
| Nom                  | Rôle / Réseau d’appartenance                          |
|----------------------|-----------------------------------------------------|
| Jérôme Assé          | Expert Data (IL Consulting)                           |
| Maya Saraouli         | Consultante confirmée chez IELI                       |
| Bruno Le Bétillier    | Pilote *Smart Cockpit Interactive* (R&D)             |
| Mathieu Sartre       | R&D d’RTE                                            |
| Olivier Mazerolle     | Expert UX/UI (non précisé dans les échanges)          |
| Gérald               | Service interne pour généralisation des rapports      |

---

## **Sujets abordés**

### 1. Préparation des descriptions techniques et validation du cadre MCP
- **Objectif** : Structurer les fiches descriptives pour les agents/groupes hypothétiques (composition, sections métiers) et discuter de l’outil MCP.
- **Points clés** :
  - Le MCP vise une matrice pré-rapport pour orchestrer simulations et études de rentabilité, avec contrôle humain ou automatisé via des agents.
  - Collaboration avec Gérald pour généraliser ces rapports au département R&D.
  - Priorisation du MCP sans urgence immédiate : les ressources existantes suffisent pour explorer cette piste (pas de conflit avec le NLP).
  - Nécessité de coordonner avec le patronat et l’ordonnancement des projets en raison des contraintes d’intervention des opérateurs.

### 2. Refonte de la feuille de route IA et cas d’usage MCP
- **Objectif** : Affiner les orientations pour un projet MCP, en collaboration avec IELI.
- **Points clés** :
  - Réflexion collective sur un cas d’usage précis (ex. : Marketplace Client Provider) ou lien avec le NLP.
  - Proposition d’un atelier UX/UI pour prioriser et co-construire les cas d’usage, en partenariat avec Olivier Mazerolle.

### 3. Présentation des expertises en IA générative chez IELI
- **Objectif** : Valider l’adéquation des compétences IELI (IA générative, deep learning) avec les besoins R&D.
- **Cas d’usage présentés** :
  - Génération d’études d’équilibre offre-demande (RTE).
  - Orchestration d’appels d’offres via N8N (pas MCP).
  - Synthèse de réunions (chatbot + SharePoint), intégration possible de mind maps via MCP.
  - Agent de planification POC (bibliographie automatisée, roadmap end-to-end).

### 4. Retour sur les projets R&D et compétences en IA générative
- **Objectif** : Comparer les approches IELI avec les feuilles de route internes (ex. : Smart Cockpit Interactive).
- **Points clés** :
  - Les solutions IELI reposent davantage sur le NLP que sur le MCP pour certains cas.
  - Orchestration entre systèmes pour les opérateurs, sans besoin précis formulé.

### 5. Collaboration R&D/ILE sur assistants intelligents et synthèse générative
- **Objectif** : Explorer les synergies autour d’assistants conversationnels et de la gestion des congestions.
- **Points clés** :
  - Intérêt commun pour l’orchestration et la synthèse d’informations fragmentées (ex. : notes manuscrites, données réseau).
  - Pistes sur le fine-tuning (qualité des données) et la navigation entre hypothèses techniques.

### 6. Optimisation des processus de génération/assignation de rapports
- **Objectif** : Structurer l’automatisation des rapports via IA multimodale.
- **Points clés** :
  - Nécessité d’un template structuré pour éviter une rédaction générique, avec directives dynamiques ou agents de sélection.
  - Flexibilité pour adapter l’outil à plusieurs templates ou approches hybrides (simulations + intervention humaine).
  - POC validé en 25 jours avec corrections itératives en cinq semaines.

### 7. Validation de l’opération "Redine"
- **Objectif** : Clarifier le statut d’un processus nommé "Redine".
- **Points clés** :
  - Désactivé par défaut, confusion sur son origine (recommandation ou erreur).
  - Délai initial de "7 ans" corrigé en 25 jours (décembre), limité entre septembre et un moment récent.

### 8. Automatisation des rapports analytiques et outils multimodaux
- **Objectif** : Présenter l’outil L-Power et la génération de fichiers BPT.
- **Points clés** :
  - Automatisation de la rédaction finale des rapports via une structure prédéfinie (PPPT/BPT).
  - Fine-tuning de modèles multimodaux sur données locales (ex. : documents en arabe).
  - Renforcement de la souveraineté interne (ILE) vs API externes.

### 9. Amélioration de la génération/correction à partir d’analyses visuelles
- **Objectif** : Décrire un pipeline agentique pour rapports structurés (PPT + transcription vocale).
- **Points clés** :
  - Cinq étapes : OCR → assignation par sections → rédaction sectionnelle → intégration finale → boucle de correction itérative.
  - Utilisation d’artefacts intermédiaires et traçabilité des slides.

### 10. Robustesse et traçabilité dans la génération automatisée
- **Objectif** : Garantir la fiabilité des rapports générés.
- **Points clés** :
  - Garde-fous techniques (séparation par sections, traçabilité, artefacts intermédiaires).
  - Approche "human in the loop" pour éviter les hallucinations.

---

## **Décisions**

| **Thème**               | **Décision prise**                                                                 |
|--------------------------|-----------------------------------------------------------------------------------|
| Descriptions techniques/MCP | Aucune décision prise.                                                       |
| Cas d’usage MCP/IELI      | Aucune décision prise.                                                       |
| Expertises IA générative  | Aucune décision prise.                                                       |
| Collaboration R&D/ILE     | Aucune décision prise.                                                       |
| Génération de rapports    | Aucune décision prise.                                                       |
| Opération "Redine"        | Aucune décision prise.                                                       |
| Automatisation L-Power/BPT | Aucune décision prise.                                                       |

---

## **Actions**

| **Responsable**       | **Action définie**                                                                                     | **Échéance**          |
|-----------------------|------------------------------------------------------------------------------------------------------|-----------------------|
| Maya Saraouli           | Proposer un atelier de réflexion sur les cas d’usage (priorisation, design UX/UI) en collaboration avec Olivier Mazerolle. | À valider par l’expert Data pour confirmation pratique. |

---

## **Points d’attention**

### **Risques et limites**
- **Contraintes ressources** :
  - Temps limité des opérateurs pour les interventions (ex. : MCP, orchestration).
  - Priorisation entre MCP et NLP non définie clairement.
- **Complexité technique** :
  - Nécessité de descriptions métiers précises pour guider les modèles IA (risque d’imprécision si hypothèses floues).
  - Limites des POC existants (ex. : fact-checking chiffré hors scope initial).
- **Alignement métiers** :
  - Confusion sur l’origine du processus "Redine" et ses dates de validité.
  - Risque d’incohérences structurelles dans les rapports si templates non adaptés.

### **Prochaines étapes**
1. **Priorisation des cas d’usage** :
   - Affiner un besoin précis avant de lancer des projets MCP ou NLP (ex. : atelier proposé par Maya Saraouli).
2. **Coordination avec les équipes R&D et patronat** :
   - Respecter les contraintes d’intervention des opérateurs et l’ordonnancement des projets.
3. **Validation des POC** :
   - Exploiter les retours des POC (ex. : génération de rapports en 25 jours) pour affiner les approches hybrides (automatisation + correction humaine).
4. **Collaboration externe** :
   - Explorer la généralisation des rapports avec Gérald et valider l’adéquation des compétences IELI avec les feuilles de route R&D.
```