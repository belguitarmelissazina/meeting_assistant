```markdown
# Compte rendu de réunion – Exploration des cas d’usage en IA générative

## 1. **Executive Summary**
Cette réunion a permis d’échanger sur les expertises, projets et besoins en IA générative entre les équipes d’**IL Consulting**, **IEB**, **RTE** et **YLD**. Les participants ont présenté leurs domaines d’intervention (assistants opérateurs, génération de rapports, détection de fraude, orchestration de simulations) et leurs méthodologies (RAG, fine-tuning, agents spécialisés). Plusieurs cas d’usage ont été évoqués, notamment autour du **MCP** et du **NLP**, sans cadre ni échéance définis. Aucune décision formelle n’a été prise, mais des pistes de collaboration future ont été identifiées, incluant un potentiel atelier design pour prioriser les besoins.

---

## 2. **Contexte & Participants**
- **Type de réunion** : Atelier d’échange sur les expertises et cas d’usage en IA générative.
- **Objectif** : Explorer des pistes de collaboration entre les participants sur des projets liés à l’IA, notamment pour les assistants opérateurs, la génération de rapports et l’intégration d’outils comme le **MCP**.
- **Participants** :
  - **Jérôme Assé** : Expert Data IA Manager, IL Consulting (collaboration avec Maya Saraouli et Deda sur la feuille de route R&D).
  - **Maya Saraouli** : Consultante confirmée chez IEB, spécialisée en IA générative (docteure en deep learning, expérience chez RTE).
  - **Bruno Le Bétillier** : Pilote de la feuille de route *Smart Cockpit Interactive* (R&D RTE).
  - **Mathieu Sartre** : R&D RTE (thématique des assistants pour opérateurs).
  - **Jérôme Picot** : Direction *Intelligence Artificielle et Innovation* (sujets anti-génératifs, LLM, MCP).
  - **Intervenant 5** : Anciennement en exploitation et recherche (collaboration avec R&D sur la gestion des congestions, intérêt pour l’EP et le MCP).
  - **Intervenant 2** : Représentant d’IEB (présentation des projets et méthodologies).
  - **Intervenant 3** (Bourdine) : Expert IA chez IELTS (multimodal, fine-tuning, RAG, déploiement via VLLR/V-Gone/Streamlit).
  - **Intervenant 6** : Travail sur l’IA générative (détails non précisés).
  - **Intervenant 7** : RIDD (implémentation de réseaux de neurones pour des écosystèmes).
  - **Intervenant 4** : Non détaillé.
  - **Intervenant 8** : Non détaillé (mentionné comme Jérôme Picot).

---

## 3. **Sujets abordés**

### 3.1 Présentations des participants
- **Jérôme Assé** : Expertise en IA générative, collaboration avec Maya Saraouli et Deda sur des projets R&D (équilibre offre-demande, rentabilité des moyens de base).
- **Maya Saraouli** : Consultante en IA générative (expérience chez RTE, docteure en deep learning).
- **Bruno Le Bétillier** : Feuille de route *Smart Cockpit Interactive* (assistants pour opérateurs).
- **Mathieu Sartre** : Thématique des assistants opérateurs à la R&D (évolution sur 10 ans).
- **Jérôme Picot** : Direction *Intelligence Artificielle et Innovation* (sujets anti-génératifs, LLM, MCP).
- **Intervenant 5** : Parcours en exploitation et recherche, intérêt pour l’interface opérateurs-outils (EP, MCP).
- **Intervenant 6** et **Intervenant 7** : Travail sur l’IA générative et réseaux de neurones (détails non précisés).

---

### 3.2 Présentation des expertises et besoins en IA générative
- **Intervenant 2** a proposé d’engager une discussion sur les besoins en IA générative pour explorer des pistes de collaboration.
- **Intervenant 5** a introduit le contexte des assistants opérateurs, soulignant que la R&D se concentre sur l’interaction et la mise en application, tandis que Jérôme Picot couvre la partie disciplinée (IA et NLP).
- Échanges sur les outils comme le **MCP** et les interfaces conversationnelles.

---

### 3.3 Présentation des projets IA générative chez IELTS et retour d’expérience RTE
- **Intervenant 3** a présenté un projet chez RTE visant à automatiser la génération de rapports d’études **EOD** (équilibre offre-demande) à partir de fichiers PPT hétérogènes.
  - **Pipeline** : 5 briques (analyse des slides, assignation aux sections, rédaction section par section, relecture, corrections itératives).
  - **Objectif** : Accélérer la production tout en garantissant la rigueur (mode "humain dans la boucle").
  - **POC** réalisé en 25 jours pour démontrer la valeur de l’IA.
- **Intervenant 4** a précisé que le POC servait à valider l’approche avant une généralisation pour la R&D.

---

### 3.4 Méthodologie de rédaction automatisée par sections et intégration
- **Intervenant 2** a détaillé la méthodologie :
  - **Assignation globale des slides** pour une classification cohérente.
  - **Rédaction section par section** (séparation fond/forme pour faciliter les corrections).
  - **Agent de relecture** pour éliminer redondances et incohérences.
  - **Boucle de correction minimale** via des commentaires ciblés.
- **Garanties de robustesse** :
  - Traçabilité des erreurs via l’assignation des slides.
  - Corrections au niveau des sections (pas de correction macro).
- **Limites** : Absence de *fact-checking* chiffré, reconstruction de graphiques, corrections globales.
- **Durée du POC** : 5 semaines (25 jours).

---

### 3.5 Spécialisation des agents et souveraineté des outils pour RTE
- **Intervenant 3** a évoqué :
  - La nécessité d’un **agent spécialisé** pour RTE (synthèses approfondies, propositions adaptées).
  - Un projet d’**agent de planification de POC** (automatisation de bibliographies et *roadmaps*).
  - Objectif : Intégrer des simulateurs pour une *pipeline end-to-end* générant des POC minimales.
- **Intervenant 2** a insisté sur la **souveraineté** de l’outil (cloisonnement au sein de RTE pour éviter son utilisation par IEL).

---

### 3.6 Exploration de l’état de l’art et présentation d’un projet de détection de fraude
- **Intervenant 2** a proposé de s’appuyer sur des sources comme **Archivix** pour suivre les avancées R&D et réaliser des POC rapides.
- **Maya (Intervenant 3)** a présenté un projet de **détection de fraude** :
  - Extraction d’informations à partir de documents administratifs scannés (salaire net, métier, etc.).
  - Utilisation d’un outil **VLLM** pour estimer un **pourcentage de conformité** (comparaison avec des intervalles de confiance).
  - Hébergement en **prême** (détails non précisés).
  - Travail sur le **pré-traitement des documents** (partie exigeante).

---

### 3.7 Fine tuning du modèle Gwen 2.5 VL et cas d’usage associés
- **Intervenant 3** a présenté le *fine tuning* du modèle **Gwen 2.5 VL** :
  - Récupération d’une sortie structurée des informations extraites.
  - Contrôle d’anomalies et déploiement via **VLLM** et **UV-CORN**.
  - *Dashboard* pour monitorer la chaîne de traitement et détecter les *drifts*.
  - Hébergement local du modèle et traitement de documents en arabe/manuscrits.
- **Intervenant 5** a évoqué un intérêt pour la partie **MCP** (actuellement en TNP) et des besoins en synthèse de données disparates (blocs d’alarme, messages).

---

### 3.8 Intégration du MCP et orchestration des simulations
- **Intervenant 5** a partagé des retours sur l’analyse de textes manuscrits et son lien avec le **NLP**, ainsi que la complexité des outils d’études et l’interaction avec les **LLM**.
- **Intervenant 3** a confirmé que l’intégration de serveurs **MCP** pour des simulations faisait partie de leur feuille de route.
  - Objectif : **POC end-to-end** avec un agent générant un plan de travail et un second agent utilisant le **MCP** pour exécuter des simulations.
- **Intervenant 2** a décrit un cas d’usage :
  - Automatisation de la préparation de simulations, orchestration via le **MCP**, génération de pré-rapports (validation humaine en aval).
  - Collaboration avec *Gérald* sur la rentabilité des moyens de production.
- **Intervenant 5** a reconnu des similitudes avec leurs besoins (gestion d’hypothèses et scénarios).

---

### 3.9 Exploration des cas d’usage (MCP, NLP) et proposition d’atelier design
- **Intervenant 2** a évoqué des pistes de cas d’usage (**MCP**, **NLP**) sans identifier de besoin précis.
  - Actions déjà prévues pour explorer le **MCP**, mais sans échéance immédiate.
  - Proposition de revenir vers les participants une fois des éléments concrets définis.
- **Intervenant 3** a mentionné des travaux en **UI/UX Design** avec **Olivier Mazerolle** (control room du futur) et proposé un **atelier design** pour prioriser les cas d’usage.
  - **Intervenant 2** a jugé l’idée intéressante sans s’engager.

---

## 4. **Décisions**
| Décision | Détail | Porteur |
|----------|--------|---------|
| Aucune décision prise | - | - |

---

## 5. **Actions**
| Action | Responsable | Échéance |
|--------|-------------|----------|
| Revenir vers les participants si un besoin précis se dégage (MCP, NLP ou autre) | Intervenant 2 | Non précisée |
| Proposition d’un atelier design (à confirmer) | Intervenant 3 | Non précisée |

---

## 6. **Points d’attention**
- **Risques/limites** :
  - Absence de *fact-checking* chiffré et de reconstruction de graphiques dans le projet de génération de rapports.
  - Corrections globales du rapport non prises en charge dans la méthodologie actuelle.
  - Complexité des outils d’études et intégration des **LLM** (intervenant 5).
  - Disponibilité des opérateurs et ordonnancement des projets (intervenant 2).
- **Prochaines étapes évoquées** :
  - Exploration du **MCP** et des cas d’usage associés (sans échéance définie).
  - Potentiel atelier design pour prioriser les besoins (à confirmer).
  - Collaboration future sur des POC ou projets spécifiques (ex. : orchestration de simulations).
```