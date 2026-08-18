```markdown
# Compte rendu de réunion : Besoins en IA générative et optimisation des rapports

---

## **Executive Summary**
La réunion a permis un tour de table sur les expertises internes concernant l’IA générative, notamment pour les projets d’automatisation des rapports de rentabilité et d’interaction opérateur-outils. Les échanges ont porté sur :
- La structuration des besoins en IA (orchestration, traitement multimodal, outils comme le MCP).
- L’optimisation des pipelines d’automatisation des rapports via des chaînes de traitement (PPD/VPT/DXT) avec validation itérative.
- Les enjeux techniques de robustesse et traçabilité des artefacts intermédiaires.
- La souveraineté technique et l’exploration de projets transversaux (orchestration, traitement de documents administratifs).
**Aucune décision formelle** n’a été adoptée, mais des pistes d’amélioration méthodologique ont émergé pour les prochaines étapes.

---

## **Contexte & Participants**

### **Type de réunion**
- **Tour de table et présentation des besoins en IA générative** (Section 1).
- **Optimisation des rapports de rentabilité** par filière (Sections 2–3).
- **Robustesse technique et outils d’orchestration** (Sections 4–5).

### **Objectifs**
- Aligner les expertises sur l’utilisation de l’IA générative pour :
  - Automatiser la génération de rapports (PPD/VPT/DXT) avec traçabilité.
  - Développer des règles d’assignation dynamique des slides et valider un POC IA.
  - Explorer des cas d’usage en orchestration (MCP, NLP) et traitement de documents administratifs.

### **Participants et rôles**
| Nom               | Rôle/Expertise mentionnée                                                                 |
|-------------------|------------------------------------------------------------------------------------------|
| **Jérôme Carpentier** | Expert data ("dataille"), gestion de la feuille de route *Smart Cockpit* pour les opérateurs. |
| **Mathieu Sartre**  | RD, pilotage de la feuille de route IA générative.                                         |
| **Sandy**          | Consultant en implémentation et orchestration (longue expérience terrain).                 |
| **Maya**           | Consultante confirmée chez IV, spécialiste deep learning/IA générative (multimodalité).    |
| **Dela**           | RD, analyses métier orientées rentabilité des moyens de base.                              |
| **Bordinat**       | Projets internes (ex : étude EOD pour RTE via *El Power*).                                |
| **Texaster**      | Mentionné dans le contexte des projets internes (sans détail supplémentaire).             |
| **Ger**            | Développement des pipelines d’automatisation des rapports.                                 |
| **Mongial**        | Difficulté à décrire précisément la structure des sections du rapport.                     |
| **Speaker 0–5**     | Participants anonymisés évoquant des retours terrain, validations ou projets transversaux. |

---

## **Sujets abordés**

### **1. Tour de table et besoins en IA générative**
- Présentation des expertises :
  - *Jérôme Carpentier* : Collaboration avec *Sandy* sur l’IA générative (ex : MCP) et gestion du *Smart Cockpit*.
  - *Mathieu Sartre* : Pilotage de la feuille de route IA.
  - *Maya* : Traitement multimodal (documents complexes, synthèse d’informations).
- Projets exploratoires :
  - Interfaces conversationnelles pour appeler/orchestrer des services adaptés.
  - Retour terrain et compétences disponibles (pas de mission claire définie).

### **2. Optimisation des rapports de rentabilité**
- **Pipeline automatisé** (5 étapes) :
  1. Traitement des slides → extraction du texte + classification analytique/descriptive.
  2. Assignation aux sections thématiques (ex : comparaisons internationales).
  3. Versionnage et itération via commentaires automatiques/manuels.
- **Défis** :
  - Structuration des sections (ex : *Speaker Mongial*).
  - Intégration de fichiers *PPT* ou transcriptions vocales (*format DXT*).

### **3. Règles d’assignation et POC IA**
- Logique de catégorisation :
  - Comparaisons internationales → slides non françaises dirigées vers une section dédiée.
  - Description détaillée des hypothèses (normes concises pour éviter l’encombrement).
- **POC** : Évaluation en 25 jours, extension envisagée à un cadre méthodologique strict (template structuré).

### **4. Robustesse et traçabilité**
- **Garde-fous techniques** :
  - Séparation rédaction finale + *gates* intermédiaires pour localiser les erreurs.
  - Artéfacts générés par brique → correction itérative (ex : absence de chiffrement ou reconstruction automatique depuis Excel).
- Projet complémentaire : Outil de génération de résumé de réunion (chatbot + exportabilité).

### **5. Orchestration et souveraineté technique**
- **MCP** :
  - Cloisonnement entre RTE et Yélè pour préserver la souveraineté locale.
  - Cas d’usage en orchestration non déployé (ex : agent de planification de blocs).
- **Traitement de documents administratifs** :
  - Extraction structurée (salaires, métiers) via prétraitement + classification VLM (*Vision-Language Model*).
  - Adaptation pour documents en arabe et détection de *drifts* (anomalies).

### **6. Analyse des notes manuscrites**
- Retour sur les outils comme le *MCP* ou le *NCP*, évoquant un manque de feedback structuré sur ces éléments.

---

## **Décisions**

| **Thème**                          | **Décision prise**                                                                 |
|------------------------------------|-----------------------------------------------------------------------------------|
| Besoins en IA générative            | Aucune décision formelle.                                                     |
| Optimisation des rapports           | Aucune décision.                                                               |
| POC IA                              | Aucune décision.                                                               |
| Robustesse/Traçabilité              | Aucune décision explicitement mentionnée.                                      |
| Orchestration (MCP)                 | Aucune décision.                                                               |
| Projets transversaux                 | Aucune décision.                                                               |

---

## **Actions**

| **Responsable**       | **Action définie**                                                                 | **Échéance**          |
|-----------------------|-----------------------------------------------------------------------------------|-----------------------|
| *Speaker 3* (Section 2) | Création et automatisation des fichiers **VPT**.                                  | Non précisée.         |
| *Speaker 5* (Section 2) | Intégration d’une transcription vocale au format **DXT** (test avec un enregistrement vocal). | Non précisée.         |
| *Speaker 4* (Section 3) | Recherche de validation du POC et évaluation des suites.                          | Non précisée.         |
| *Speaker 0/1* (Section 3) | Adaptation possible des templates pour plusieurs versions (sans action assignée). | Aucune mention d’échéance. |

---

## **Points d’attention**

### **Risques et limites**
- **Manque de clarté** :
  - Absence de mission claire sur l’IA générative (besoins non priorisés).
  - Difficultés techniques persistantes : absence de chiffrement, reconstruction automatique des données brutes.
- **Dépendance aux outils existants** :
  - Limites du *MCP* ou *NCP* (retours terrain non exploités structurément).
  - Gestion manuelle des corrections itératives pour les rapports.
- **Souveraineté technique** :
  - Risque de cloisonnement entre RTE et Yélè sans coordination explicite.

### **Prochaines étapes suggérées**
1. **Validation du POC IA** (Section 3) : Retour sur les règles fonctionnelles et suites possibles.
2. **Amélioration des pipelines** :
   - Clarifier la structure des sections pour *Ger* et *Mongial*.
   - Intégrer des garde-fous techniques (ex : traçabilité des artefacts).
3. **Exploration des cas d’usage transversaux** :
   - Étendre l’orchestration MCP à des projets pilotes (sans décision formelle).
   - Affiner le traitement de documents administratifs (extraction structurée + VLM).

---
```