```markdown
# **Compte rendu de réunion – IA Générative et Collaboration entre Équipes**

---

## **Executive Summary**
La réunion a permis un échange structuré autour des besoins en **IA générative** au sein des équipes RTE, IELTS/YM/IEB et IL Consulting. Les participants ont présenté leurs expertises respectives (spécialisation en réseaux de neurones, gestion d’assistants techniques, automatisation de rapports métiers) ainsi que des projets concrets comme :
- **Automatisation de la rédaction de rapports EOD** via une pipeline en cinq étapes (OCR, classification, génération itérative).
- **Développement d’agents spécialisés** pour sécuriser les données et accélérer l’orchestration des POC.
- **Exploration du Modèle Centralisé de Production (MCP)** pour la gestion end-to-end des études réseau.

Aucune décision formelle n’a été prise, mais des pistes techniques et organisationnelles ont émergé pour des collaborations futures.

---

## **Contexte & Participants**

### **Type de réunion**
- **Tour de table initial** (Section 1) + échanges techniques sur les besoins en IA générative (Sections 2 à 9).
- Thème central : **Collaboration inter-équipes** (R&D RTE, IELTS/YM/IEB, IL Consulting) pour développer des solutions d’assistants et outils automatisés.

### **Objectifs**
1. Présenter les rôles et expertises des participants.
2. Identifier des synergies entre projets existants (ex : pipeline de rédaction de rapports).
3. Évaluer l’intégration du MCP et des agents spécialisés dans la gestion des études réseau.
4. Préparer une réflexion collective sur les cas d’usage prioritaires (UX/UI NLP MCP).

### **Participants (avec rôles mentionnés)**
| Nom               | Rôle / Organisation                          | Expertise évoquée                                                                 |
|-------------------|---------------------------------------------|----------------------------------------------------------------------------------|
| Jérôme Assé       | Data IA Manager, IL Consulting              | Spécialiste IA générative, collaboration avec Maya/Deda sur projets métiers.     |
| Maya Saraouli      | Consultante confirmée, IEB                  | Expertise en IA générative (projets internes/externes), rejoint YLD depuis septembre. |
| Bruno Le Bétillier  | Pilote *Smart Cockpit Interactive*, R&D    | Développement d’assistants pour opérateurs.                                       |
| Mathieu Sartre   | R&D, RTE                                    | Assistants techniques et orchestration des données.                                |
| Pierre             | Équipe équilibre offre-demande, RTE         | Projet POC : Automatisation de rapports EOD (PowerPoint → Markdown/Word).          |
| Gérald             | RIDD ou équipe similaire                    | Travaux sur implémentation de réseaux de neurones pour écosystèmes.               |
| Intervenant 2      | Direction IA & Innovation (anciennement R&D)| LLM, MCP, orchestration des POC et projets externes (ex : Yémen).                |
| Intervenant 3      | Équipe Yélé ou YM                           | Veille sur les cas d’usage MCP, collaboration avec UI/UX Design.                   |
| Intervenant 5      | Parcours recherche/exploitation              | Interface opérateur-outils (assistant), gestion des congestions, MCP comme outil conversationnel. |

---

## **Sujets abordés**

### **1. Tour de table et présentations**
- **Jérôme Assé** a introduit les participants en soulignant ses collaborations avec Maya sur l’IA générative et Deda sur la feuille de route offre-demande.
- **Maya Saraouli**, **Bruno Le Bétillier**, et **Mathieu Sartre** ont brièvement présenté leurs rôles dans le développement d’assistants pour les opérateurs.

### **2. Besoins en IA générative et collaboration**
- Échanges sur les parcours professionnels et les expertises respectives (réseaux de neurones, LLM, MCP).
- Proposition d’une discussion collaborative sur les besoins métiers (ex : besoin d’un agent spécialisé pour la planification des POC).

### **3. Projet RTE : Automatisation de rapports EOD**
- **Pierre** a détaillé un POC validé en 25 jours :
  - Pipeline en 5 étapes (OCR, classification, génération itérative, interface Markdown/Word, transcription vocale).
  - Objectif : accélérer la production tout en préservant la rigueur via des corrections itératives par les utilisateurs.
- **Gérald** a confirmé la faisabilité de l’intégration d’une transcription vocale.

### **4. Méthodologie d’assignation et correction des slides**
- Approche basée sur :
  - Une **assignment précise** des slides aux sections (ex : éviter les slides hors contexte).
  - Une **redaction section par section**, séparant fond/forme pour faciliter les corrections.
  - Un système de **corrections itératives** via des commentaires ciblés.

### **5. Besoin en agent spécialisé et souveraineté des données**
- **Intervenant 3** a souligné la nécessité d’un agent dédié à :
  - La planification des POC.
  - Une **veille automatisée** (web search) pour synthétiser des bibliothèques thématiques.
- Enjeu : sécuriser l’usage de l’outil au sein de RTE (ex : cloisonnement côté RTE).

### **6. Veille et POC rapide**
- **[Intervenant 2]** a proposé une démarche pour :
  - Réaliser un POC "quick and dirty" via des agents codés rapidement.
  - Compléter avec une phase d’ingénierie logicielle ultérieure.

- **[Intervenant 3]** a évoqué un projet en cours :
  - Extraction de données administratives (ex : salaires) à partir de documents scannés.
  - Détection de fraude via l’analyse croisée des incohérences (ex : salaire vs métier).

### **7. Fine-tuning et orchestration des modèles VL**
- **[Intervenant 3]** a présenté le *fine-tuning* du modèle Gwen 2.5 VL pour :
  - Traiter des documents manuscrits ou en arabe.
  - Déploiement via VLLM/UV-CORN avec un dashboard de monitoring des *drifts*.
- **Intervenant 5** a souligné la nécessité d’une classification préalable des entrées (manuscrits vs non).

### **8. Intégration du MCP pour les études réseau**
- Comparaison entre :
  - Traitement des données manuscrites.
  - Orchestration des études via le MCP (gestion des scénarios, simulateurs, outils internes).
- Objectif : appliquer un plan de travail généré par un agent via les outils internes ou MCP.

### **9. Évaluation des cas d’usage**
- **Intervenant 2** a souligné la diversité des approches (MCP, NLP, UX/UI) sans priorité claire.
- **Intervenant 3** a proposé un **atelier design** pour co-construire une vision commune avec l’équipe UI/UX.

---

## **Décisions**

| **Thème**                     | **Décision prise**                                                                 |
|-------------------------------|------------------------------------------------------------------------------------|
| Projet RTE (rapports EOD)      | Aucune décision formelle.                                                          |
| MCP et orchestration           | Aucune décision prise.                                                             |
| Agent spécialisé               | Aucune décision prise.                                                             |
| Veille et POC rapide           | Aucune décision prise.                                                             |

---

## **Actions**

| **Responsable**       | **Action définie**                                                                 | **Échéance**          |
|-----------------------|----------------------------------------------------------------------------------|-----------------------|
| Intervenant 3         | Organiser une réflexion collective sur un cas d’usage MCP précis (ex : intégration dans un projet externe). | *À confirmer*        |
| Intervenant 2         | Attendre la présentation des travaux sur le MCP pour en discuter.                 | Sans date précise     |

---

## **Points d’attention**

### **Risques et limites**
- **Complexité technique** :
  - Limites du *fine-tuning* pour les documents manuscrits ou multilingues (ex : arabe).
  - Détection des anomalies dans l’extraction de données administratives (fraude potentielle).
- **Souveraineté des données** :
  - Risque d’utilisation transversale entre RTE et IEL (ex : cloisonnement nécessaire pour les données sensibles).
- **Orchestration du MCP** :
  - Nécessité de clarifier la définition du MCP avant toute implémentation.
  - Coordination avec les équipes UI/UX pour prioriser les cas d’usage.

### **Prochaines étapes**
1. **Réflexion collective sur le MCP** :
   - Identifier un cas d’usage concret (ex : intégration dans un projet externe) pour affiner les échanges.
2. **Atelier design** (proposition de l’Intervenant 3) :
   - Co-construire une vision commune avec l’équipe UI/UX pour prioriser les besoins en UX/UI vs NLP.
3. **Veille et POC rapide** :
   - Continuer à explorer des sources comme Archivix pour identifier des tendances en recherche.
4. **Validation du pipeline RTE** :
   - Finaliser les tests itératifs sur l’interface Markdown/Word avant déploiement.

---
```