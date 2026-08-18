# Compte rendu de reunion

_Type de reunion_ : **prise de contact**

_Objectif_ : Faire connaissance entre les équipes et identifier des pistes concrètes pour une future collaboration, tout en discutant des projets existants.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthese

La réunion a débuté par un tour de table où chaque participant a présenté ses attentes et compétences en matière d'IA générative et d'assistants interactifs. Les discussions ont ensuite porté sur divers projets, notamment l'automatisation de la rédaction de rapports à partir de fichiers PowerPoint, l'utilisation d'outils pour l'orchestration de systèmes génératifs, et le déploiement d'outils de recherche et développement pour l'extraction d'informations structurées. Bien que des projets existants aient été évoqués, aucune décision formelle ni action définie n'a été prise. Les participants ont exprimé un intérêt pour une collaboration future et ont suggéré la tenue d'un atelier UX avec un cabinet externe.

## 1. Prise de contact : présentation des participants et attentes

Cette prise de contact a permis aux participants de RTE d’échanger sur leurs attentes concernant les assistants interactifs et l’IA générative, en lien avec la feuille de route *Smart Cockpit*. Lors du tour de table, *Bruno LEMETAYER*, expert data et manager de la pratique IA chez Élé Consulting, a présenté son rôle dans des projets transversaux incluant l’équilibre offre-demande et les analyses métiers. Il a souligné son implication sur les assistants pour les opérateurs en conduite, ainsi que sur l’implémentation de réseaux de neurones pour l’écosystème RTE. *Maya SAHRAOUI*, consultante confirmée chez IVB et docteure en traitement automatique des langues, a évoqué ses expériences en IA générative, notamment dans le cadre de projets internes et collaboratifs avec RTE, avant son arrivée au sein de cette organisation en septembre dernier. *Jérôme MASSET*, pilote de la feuille de route *Smart Cockpit* à la R&D RTE, a détaillé les besoins spécifiques liés aux assistants interactifs pour les opérateurs, insistant sur l’intérêt croissant pour les interfaces conversationnelles et les outils basés sur le traitement du langage naturel (NLP) ou le modèle de contrôle des processus (MCP). Les échanges ont mis en lumière une volonté commune d’explorer des synergies autour de ces technologies pour améliorer la fluidité des interactions opérateur-outils, sans préciser de périmètre technique ou opérationnel détaillé.

## 2. Expertises en IA générative et assistants interactifs

Dans ce échange, Jérôme PICAULT partage les compétences techniques et méthodologiques développées dans l’industrialisation de projets d’IA générative chez Ely, en mettant l’accent sur des approches multimodales et des outils spécifiques comme Mistral ou Vicorne.

- Jérôme PICAULT a travaillé à transformer des contenus complexes et hétérogènes en formats actionnables, tels que des extractions de réinformation pour faciliter les décisions ou des fiches synthétiques, en combinant multimodalité et industrialisation.
- Son expertise inclut la gestion d’un équilibre entre prétraitement et monitoring sur des projets d’assistants génératifs, qu’ils soient internes à l’équipe IA ou issus de missions antérieures.
- Il a développé une approche fine sur des modèles hébergés localement, notamment en réalisant du *fine-tuning* sur des architectures génériques comme QNTubine.
- L’utilisation de modèles comme Mistral est centrale chez Ely, avec un besoin marqué pour le RAG (Retrieval-Augmented Generation), incluant le ranking et la vectorisation des données.
- Jérôme PICAULT a contribué à des projets d’orchestration multimodale, couvrant des cas variés allant du déploiement de systèmes NUN jusqu’à l’utilisation de MCP pour structurer les flux de travail.
- Des outils comme VLHRM et Vicorne ont été employés pour déployer des modèles pré-entraînés, notamment en intégrant des mécanismes de *streaming* pour une livraison optimisée de contenus.

## 3. Projet d’automatisation de la rédaction de rapports à partir de PowerPoint

Lors du échange sur le projet d’automatisation de la rédaction de rapports à partir de fichiers PowerPoint, l’équipe a détaillé une approche structurée pour traiter des données hétérogènes issues de présentations. Le processus repose sur cinq étapes clés : une analyse fine des slides via un agent capable d’extraire et classer les informations graphiques ou textuelles, puis leur attribution aux sections prédéfinies du rapport en fonction de règles métiers spécifiques (par exemple, la comparaison France/Europe est systématiquement orientée vers une section dédiée). Une fois l’assignation réalisée, un modèle génère des bullet points par section avant d’enrichir le texte final pour garantir une cohérence et une lisibilité optimales. Enfin, une boucle de correction itérative permet aux utilisateurs de corriger les résultats en temps réel via des commentaires intégrés à l’interface, assurant ainsi la validation manuelle des contenus générés. La solution a été développée dans un cadre PoC en vingt-cinq jours, incluant des ateliers de co-construction avec les équipes concernées.

## 4. Orchestration et gestion des systèmes génératifs (N8N, MCP)

Les échanges autour de l’orchestration des systèmes génératifs ont permis d’explorer les synergies entre traitement du langage naturel et gestion centralisée des outils (MCP), notamment pour des cas d’usage liés à la synthèse de données fragmentées ou aux études de rentabilité des moyens de production.

- les participants ont souligné l’intérêt commun d’intégrer le traitement des notes manuscrites en NLP, afin de les dispatcher vers des usages spécifiques comme la génération de rapports ou les synthèses automatisées.
- la question de la capacité à orchestrer des outils complexes via un serveur MCP a été évoquée pour faciliter l’interaction avec des agents génératifs et des systèmes internes de simulation, dans le cadre d’une feuille de route existante.
- les travaux sur la rentabilité des moyens de production ont mis en lumière une matrice d’études nécessitant une orchestration centralisée (MCP) pour préparer, lancer et contrôler les simulations avant leur intégration dans des pré-rapports ou rapports finaux.
- l’orchestration des études énergétiques a été décrite comme un processus dynamique impliquant la récupération en temps réel de données d’entrée (consommation, production, programmation), l’hypothèse de scénarios et le jonglage entre simulateurs et outils de visualisation.
- les échanges ont confirmé que les cas d’usage liés à la MCP pourraient s’articuler autour des besoins en NLP pour structurer des hypothèses ou des données disparates, bien qu’une priorité soit accordée aux études de rentabilité et aux simulations internes.

## 5. Solutions pour l’analyse de documents administratifs via IA locale

Lors de la discussion sur les solutions locales pour l’analyse de documents administratifs, Maya SAHRAOUI a évoqué un projet spécifique visant à extraire des informations structurées — comme des salaires nets, brut ou totaux et des métiers — à partir de documents scannés. L’objectif initial était d’évaluer la conformité globale entre ces données extraites et les références historiques existantes par intervalle de confiance. Ce projet repose sur un modèle hébergé localement, combinant une chaîne de prétraitement robuste pour gérer des entrées variées (manuscrites ou non), ainsi qu’un système de détection de biais dans les résultats via un visuo-linguistique finetuned et un dashboard de monitoring en temps réel. Elle a également détaillé la phase d’apprentissage du modèle, incluant le filtrage des données et l’ajustement pour les spécificités linguistiques (comme les documents rédigés en arabe), afin de garantir une extraction fiable et adaptée aux contraintes techniques internes.

## 6. Pistes explorées et prochaines étapes (MCP, UX design)

Lors de cette prise de contact, les échanges ont porté sur l’exploration du modèle conversationnel (MCP) et des pistes liées à son intégration dans des cas d’usage spécifiques. Les participants ont également évoqué la possibilité d’un atelier UX pour affiner une vision commune sur les priorités.

- les discussions ont proposé de réfléchir à un cas d’usage centré sur l’intégration du MCP, en partageant d’abord leur propre vision avant un éventuel second échange pour affiner ces pistes.
- l’équipe a souligné la nécessité d’attendre une précision plus concrète des besoins avant d’engager des travaux spécifiques sur le MCP, en raison de contraintes opérationnelles existantes.
- un participant a mentionné que des actions internes sont déjà prévues pour explorer les aspects liés au MCP, sans préjuger d’une priorisation immédiate.
- la collaboration avec un cabinet spécialisé en UX, comme Olivier Maserol, a été évoquée pour organiser un atelier dédié à la réflexion sur les cas d’usage et leur priorisation, afin de co-construire une vision partagée.
- l’idée d’un atelier UX externe a été présentée comme une opportunité pour échanger sur des besoins structurés et identifier des axes communs avant toute décision formelle.

## 7. Plan d'action

Lors de la discussion sur les projets en cours, l’équipe a évoqué des pistes pour étendre l’outil de génération de rapports au-delà du contexte spécifique à RTE et exploré les besoins liés aux systèmes génératifs comme le MCP. Une réflexion collective a également été engagée concernant une collaboration future en matière d’UX design avec un cabinet externe.

| # | Action | Responsable | Echeance |
|---|---|---|---|
| 1 | Évaluer les modalités de généralisation de l’outil de génération de rapports au-delà du contexte RTE et discuter avec les parties prenantes concernées pour identifier des pistes concrètes d’adaptation | — | — |
| 2 | Tenir informé sur les besoins émergents en matière de systèmes génératifs (MCP ou NLP) afin d’éviter des discussions sans fondement et préparer une synthèse des attentes précises si nécessaire | Jérôme PICAULT | — |
| 3 | Revoir les travaux existants sur la partie MCP et partager leur analyse pour envisager un second échange si les besoins ou orientations se clarifient | — | — |

