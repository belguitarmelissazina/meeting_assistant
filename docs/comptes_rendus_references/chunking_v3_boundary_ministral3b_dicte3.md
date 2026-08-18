```markdown
# Compte rendu de réunion – IA Générative et Assistants Intelligents

---

## **Executive Summary**
La réunion a permis d’échanger sur les besoins en IA générative, les projets existants (automatisation des rapports, synthèse de données, détection de conformité) et les pistes méthodologiques pour l’intégration d’assistants intelligents. Les discussions ont porté sur :
- La structuration des workflows autour de templates pour la génération de rapports,
- L’orchestration via des outils comme *MCP* (Machine Processurielle Centralisée),
- L’évaluation des cas d’usage NLP et leur potentiel en collaboration avec RTE ou Élé Consulting.
Aucune décision opérationnelle majeure n’a été prise, mais plusieurs actions techniques et méthodologiques ont été identifiées pour les prochaines étapes.

---

## **Contexte & Participants**

### **Type de réunion**
- Tour de table initial sur les besoins en IA générative et assistants intelligents (Section 1).
- Échanges méthodologiques autour des projets d’automatisation, synthèse de données et intégration de *MCP* (Sections 2 à 11).

### **Objectif principal**
Identifier les synergies entre les équipes pour :
- Développer des interfaces conversationnelles fluides,
- Optimiser l’orchestration des tâches via des outils centralisés (*MCP*), et
- Standardiser les processus de génération de rapports ou d’analyse.

### **Liste des participants (rôles mentionnés)**
| **Nom**               | **Rôle/Entreprise**                          |
|------------------------|--------------------------------------------|
| Nordine                 | Organisateur, non précisé                  |
| Mathieu                | DataIa Manager chez Élé Consulting          |
| Maya                    | Consultante confirmée chez IVB              |
| Bruno Mélière          | RD à RTE (Responsable Direction)            |
| Dinka                   | Impliquée en implémentation de réseaux de neurones (RTE/Élé Consulting) |
| Jérôme Picot            | Intelligence artificielle et innovation chez Élé Consulting |
| SPEAKER_01             | Responsable projets IA générative chez Elyay |
| SPEAKER_02             | Participant non précisé                     |
| Basile                  | Équipe *équilibre offre/demande* (RTE)     |
| Gérald                  | Équipe *équilibre offre/demande* (RTE)     |
| SPARKER_00/SPARKER_01   | Participants techniques (MCP, orchestration)|
| deRTE                   | Équipe *équilibre offre/demande* (RTE)      |

---

## **Sujets abordés**

### **1. Tour de table sur les besoins en IA générative et assistants intelligents**
- Présentation des rôles et expertises :
  - Mathieu : Gouvernance, régulation, analyse métiers (*équilibre offre/demande*, *analyses décoffert*).
  - Maya : Traitement automatique des langues (IA générative interne/RTE).
  - Bruno Mélière : Pilotage de la feuille de route *Smart Cockpit* et assistants pour opérateurs.
- Priorités :
  - Interfaces conversationnelles fluides,
  - Application des modèles de langage (*LP*) et *MCP*,
  - Intégration d’interactions quasi conversationnelles.

---

### **2. Prise de contact méthodologique**
- Besoin d’identifier les services compétents pour approfondir des études (calculs, réseaux).
- Proposition de mobiliser Mike en raison de ses connaissances présumées.
- Échanges sur la présentation des projets existants sans structuration claire.

---

### **3. Positionnement chez Elyay**
- Projets d’industrialisation :
  - Transformation de contenus complexes (documents hétérogènes → formats actionnables : extraits, fiches synthétiques).
  - Utilisation de modèles multimodaux (ex. : QNTubine) et finetuning sur Mistral.
  - Pré-traitements (RAG, ranking vectoriel) et orchestration pour optimiser les gains d’usage.
- Déploiement via des outils comme **VLHRM** ou **Vicorne**, incluant du streaming.

---

### **4. Automatisation des rapports EOD**
- Objectif : Générer automatiquement des rapports sur la rentabilité des moyens de production à partir d’études via *Power*.
- Chaîne de traitement :
  - OCR des slides, classification analytique des graphiques,
  - Structuration automatique en quatre sections prédéfinies (hypothèses, comparaisons internationales, résultats par filière).
  - Boucle collaborative pour corrections via une interface dédiée.
  - Option : Transcription vocale (via *Spitch*).

**Points d’attention méthodologique** :
- Nécessité de préciser la structure fine des sections (ex. : sous-parties comme *"3.5. X"* → nom + description détaillée).
- Règles explicites pour l’assignation des slides (éviter les annexes en introduction).

---

### **5. Catégorisation et assignation des slides**
- Hypothèses :
  - Séparation des tâches : rédaction des *bullet points* par section, puis enrichissement de la prose.
  - Intégration des slides représentatives au début de chaque section pour une vision globale.
- Validation des templates de structure et catégories.
- Évaluation de la flexibilité de l’outil face à des templates multiples ou absents.

---

### **6. Robustesse de l’outil d’automatisation**
- Approches pour adapter un outil existant :
  - Structurer les sections distinctes et assigner chaque slide à un chapitre précis.
  - Intégrer des garde-fous (artefacts intermédiaires) pour isoler les erreurs (hallucinations, incohérences).
- Limites actuelles :
  - Absence de vérification chiffrée sur les données extraites des graphiques,
  - Pas de reconstruction automatique de graphiques depuis Excel,
  - Correction limitée aux sections plutôt qu’au niveau macro global.

---

### **7. Synthèse de données et orchestration via MCP**
- Cas d’usage :
  - Orchestration avec *N8N* pour les réponses aux appels d’offres (CV, références, méthodologie).
  - Génération automatisée de résumés de réunions via un MCP centralisé.
- Objectifs futurs :
  - Extension vers l’enregistrement vocal et la génération de mindmaps via des modèles de langage (*LM*).
  - Intégration du Sherpa (notes de réunion) pour renforcer la souveraineté et la confidentialité.

---

### **8. Amélioration des synthèses et planification**
- Nécessité de cloisonner l’utilisation d’un outil spécifique pour préserver la souveraineté des données.
- Exploration de deux missions :
  - Cas d’usage existants en orchestration,
  - Projet manuel de planification des *POK* (non lié à l’orchestration).
- Idée : Développer un agent de planification pour récupérer une bibliographie et proposer un PoC minimal via des pipelines/workflows.

---

### **9. Détection de conformité via extraction administrative**
- Projet Maya :
  - Extraction structurée de données (salaires nets/bruts, métiers) à partir de documents scannés.
  - Modèle VLM pour la structuration des extraits.
  - Contrôle d’anomalies (*drifts*) et déploiement via un *dashboard*.
- Potentiel : Référence pour d’autres interventions chez Yéley (finetuning multilingue, ex. : arabe).

---

### **10. Cas d’usage NLP + MCP**
- Synthèse de données fragmentées (blocs d’alarme, messages) :
  - Génération de rapports ou analyses structurées.
  - Orchestration des études via le MCP pour la simulation énergétique et les scénarios de rentabilité.
- Limites techniques :
  - Navigation entre hypothèses/données en temps réel,
  - Absence de vérification chiffrée intégrée.

---

### **11. Évaluation des besoins et MCP**
- Pistes explorées :
  - Cas d’usage précis du *MCP* (non défini dans le texte).
  - Collaboration avec SPARKER_00 pour un atelier de priorisation.
- Contraintes opérationnelles :
  - Priorisation des projets existants (temps limité des opérateurs).

---

## **Décisions prises**

| **Thème**                     | **Décision**                                                                 |
|--------------------------------|------------------------------------------------------------------------------|
| **Automatisation rapports EOD** | Aucune décision prise.                                                     |
| **Catégorisation slides**       | Aucune décision prise.                                                     |
| **Robustesse outil**           | Aucune décision prise.                                                      |
| **Orchestration MCP**          | Aucune décision prise.                                                      |
| **Synthèse de données**        | Aucune décision prise.                                                      |

---

## **Actions définies**

| **Responsable**       | **Action**                                                                                     | **Échéance**       |
|-----------------------|-------------------------------------------------------------------------------------------------|-------------------|
| Basile                | Valider et finaliser les hypothèses/règles d’assignement pour les templates de structure/catégories. | Non précisée      |
| Gérald                | Évaluer avec Basile la généralisation de l’outil POC à d’autres rapports non structurés par template (assignation slides). | Non précisée      |
| SPEAKER_01            | Développement progressif de l’outil de résumés de réunions (MCP + intégration outils internes).  | Non précisée      |

---

## **Points d’attention et risques**

### **Risques/limites techniques**
- **Automatisation des rapports** :
  - Absence de vérification chiffrée sur les données extraites des graphiques,
  - Reconstruction limitée des graphiques depuis Excel.
- **Orchestration MCP** :
  - Nécessité d’une vision claire des besoins métiers pour éviter une complexité inutile,
  - Risque de surcharge si le MCP n’est pas suffisamment isolé (souveraineté des données).
- **Détection de conformité** :
  - Gestion manuelle des cas mixtes (documents partiellement manuscrits),
  - Dépendance au modèle VLM pour la structuration.

### **Prochaines étapes**
1. **Finalisation méthodologique** :
   - Basile/Gérald : Affiner les règles d’assignement et évaluer la flexibilité de l’outil POC.
2. **Déploiement progressif** :
   - SPEAKER_01 : Prioriser le développement de l’outil de résumés de réunions (intégration Sherpa).
3. **Évaluation des besoins MCP** :
   - Attendre une information plus précise sur les cas d’usage avant de se pencher davantage.
4. **Collaboration externe** :
   - Solliciter SPARKER_00 pour un atelier de priorisation (partenariat avec Olivier Maserol).

---
```