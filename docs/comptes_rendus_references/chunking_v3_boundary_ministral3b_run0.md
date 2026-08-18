```markdown
# **Compte rendu de réunion – IA Générative et Collaboration entre Partenaires**

---

## **Executive Summary**
La réunion a permis d’échanger sur les besoins en **IA générative**, les compétences techniques disponibles, ainsi que sur des projets concrets comme l’automatisation de rapports (ex : EOD chez RTE) ou la mise en place d’agents spécialisés pour des synthèses et planifications énergétiques. Les discussions ont porté sur :
- La méthodologie d’automatisation structurée des rapports par sections,
- L’exploration du **MCP** (*Modèle Central de Production*) comme outil d’orchestration,
- Des cas d’usage documentaires (fine-tuning VLMs, traitement de manuscrits),
- Les limites techniques et organisationnelles (fact-checking, souveraineté, traçabilité).
Aucune décision formelle n’a été prise, mais des pistes pour des ateliers ou échanges futurs ont émergé.

---

## **Contexte & Participants**

### **Type de réunion**
Réunion technique et collaborative entre :
- **IL Consulting** (Jérôme Assé, Data IA Manager),
- **RTE** (Mathieu Sartre, Bruno Le Bétillier – *Smart Cockpit Interactive*),
- **IEB/YLD** (Maya Saraouli, consultante en IA générative),
- **Autres équipes internes** (ex : R&D EDF, RIDD, équipe Équilibre Offre-Demande).

### **Objectif**
- Explorer les synergies entre compétences en IA générative,
- Valider des méthodologies d’automatisation pour des cas d’usage énergétiques,
- Discuter de l’intégration du **MCP** et des besoins en agents spécialisés.

### **Participants mentionnés (avec rôles implicites)**
| Nom                  | Rôle principal                          |
|----------------------|----------------------------------------|
| Jérôme Assé          | Data IA Manager, coordination projets IA générative. |
| Maya Saraouli         | Consultante en deep learning/IA générative (ex : traitement orthophonique). |
| Mathieu Sartre      | R&D chez RTE (*Smart Cockpit Interactive*). |
| Bruno Le Bétillier    | Pilote *Smart Cockpit* à EDF.           |
| Intervenant 2        | Représentant **RIDD** (travaux sur réseaux de neurones). |
| Intervenant 3        | Responsable **Intelligence Artificielle et Innovation** (cas d’usage MCP, fine-tuning VLMs). |
| Intervenant 5        | Équipe R&D (interactions utilisateur/EP/MCP). |
| Intervenants 6–8     | Autres membres des équipes ÉOD/RTE.      |

---

## **Sujets abordés**

### **1. Tour de table et présentations**
Les participants ont partagé leurs rôles, collaborations actuelles en IA générative (ex : feuille de route, gouvernance-régulation), et parcours techniques :
- **Jérôme Assé** a présenté les projets d’IA chez IL Consulting et son rôle central dans la coordination.
- **Maya Saraouli** a détaillé ses travaux sur le deep learning appliqué au langage et l’intégration chez RTE/Dana.
- **Bruno Le Bétillier** et **Mathieu Sartre** ont évoqué leurs missions en assistance aux opérateurs via des assistants interactifs.

---

### **2. Besoins en IA générative et collaboration**
Les échanges ont mis en lumière :
- Des parcours variés (ex : **Intervenant 6** depuis longtemps impliqué, **Intervenant 7** sur les réseaux de neurones pour écosystèmes complexes).
- Une demande d’exploration collaborative autour des besoins spécifiques (ex : **Intervenant 2** a proposé une discussion structurée).

---

### **3. Projet RTE : Automatisation de rapports EOD**
**Méthodologie détaillée** :
1. Extraction/description des slides via OCR et analyse graphique.
2. Classification par sections prédéfinies (ex : hypothèses, comparaisons France/Europe).
3. Application de règles d’assignation pour éviter les slides annexes inutiles.
4. Génération de fiches descriptives détaillées pour guider l’IA.
5. Intégration d’une boucle de correction itérative via une interface Markdown → DocX.

**Cas particulier** :
- Ajout d’une option : intégration de transcriptions vocales (Speech-to-Text) pour enrichir le contexte des slides.

---
### **4. Processus d’automatisation par sections**
Points clés :
- **Assignation flexible** : pas de template obligatoire, mais orientation par section.
- **Traçabilité** : séparation des étapes (ex : assignation → rédaction → correction).
- **Robustesse** : gestion itérative des erreurs via artefacts intermédiaires (bullet points).

**Limites évoquées** :
- Fact-checking chiffré ou reconstruction de graphiques (hors scope initial).
- Correction macro globale du rapport (seulement par sections actuellement).
- Absence d’orchestration avancée avec MCP (Mediator Control Platform), bien que mentionnée pour un futur projet.

---

### **5. Besoin d’un agent spécialisé en synthèse/planification énergétique**
**Cas d’usage identifiés** :
- Orchestration dans des missions en Yémen (ex : gestion de ressources).
- Génération automatique de roadmaps via web search bibliographique + outils de simulation pour proposer des POC minimalisés.

**Objectifs** :
- Accélérer les démarches comme les *hackathons* via une pipeline end-to-end.
- Assurer la souveraineté technique de l’outil au sein de RTE.

---

### **6. Études de cas et MCP**
**Comparaison MCP vs autres approches** :
- Le MCP (non défini dans le texte) pourrait servir à dispatcher ou orchestrer des études complexes via un serveur centralisé.
- Projet en cours : POC end-to-end avec un agent générant des directives → transmission via MCP → simulations.

**Limites techniques** :
- Absence de besoin clair pour prioriser l’exploration du MCP (recommandation d’attendre une clarification).

---

### **7. Optimisation fine-tuning VLMs et orchestration**
**Étapes clés** :
1. Récupération de sorties structurées pour extraire des informations spécifiques.
2. Contrôle d’anomalies via VLLM/UV-CORN.
3. Déploiement en production avec un *dashboard* pour détecter les *drifts*.

**Cas documentaires** :
- Adaptation de modèles finaux pour traiter l’arabe ou des éléments manuscrits (classification automatique).
- Orchestration d’études fragmentées (ex : blocs d’alarme, messages disparates) vers une synthèse cohérente.

---

### **8. Exploration MCP vs autres approches**
**Points communs avec le traitement de textes manuscrits** :
- Navigation entre outils de simulation et visualisation pour les études énergétiques.
- Gestion des hypothèses (consumption/production/programmation).

**Prochaines étapes suggérées** :
- Atelier dédié au design pour prioriser les cas d’usage MCP.

---

### **9. Évaluation des cas d’usage**
- **Intervenant 3** propose un atelier pour affiner l’exploration du MCP si besoin.
- **Refonte UI/UX de la *control room*** (avec Olivier Mazerolle) en parallèle.

---

## **Décisions**

| **Thème**                     | **Décision prise**                                                                 |
|-------------------------------|------------------------------------------------------------------------------------|
| IA générative / Collaboration | Aucune décision explicite.                                                     |
| Automatisation rapports EOD   | Aucune décision.                                                                  |
| MCP                          | Aucune décision sur son déploiement immédiat.                                    |
| Ateliers/réflexions           | Validation d’un échange futur (ex : atelier design) sans engagement immédiat.     |

---

## **Actions**

| **Responsable**       | **Action définie**                                                                 | **Échéance**               |
|-----------------------|----------------------------------------------------------------------------------|---------------------------|
| Intervenant 3         | Réflexion sur un cas d’usage MCP spécifique si besoin (interlocuteur non nommé).   | À définir par l’interlocuteur. |
| Aucune autre action    | Aucune action définie explicitement dans les extraits fournis.                    | –                         |

---

## **Points d’attention**

### **Risques/Contraintes**
- **Fact-checking** : Limites techniques pour valider des données chiffrées ou reconstruire graphiques à partir de sources brutes.
- **Souveraineté technique** : Nécessité d’éviter la diffusion des outils vers des entités externes (ex : IEL).
- **Orchestration MCP** : Dépendance à un modèle centralisé non encore défini dans le texte, avec une phase *TNP* (Traitement Non Produit) en cours.
- **Rentabilité des moyens** : Matrice d’études à finaliser pour l’orchestration des simulations et leur intégration dans des rapports.

### **Prochaines étapes**
1. **Atelier design MCP** :
   - Priorisation des cas d’usage (proposé par **Intervenant 3**).
   - Partage d’une vision commune entre les équipes.
2. **Études de cas documentaires** :
   - Affiner l’exploration du fine-tuning VLMs et leur orchestration avec MCP.
3. **Clarification des besoins** :
   - Attendre une définition précise du MCP avant d’envisager son développement.

---
```