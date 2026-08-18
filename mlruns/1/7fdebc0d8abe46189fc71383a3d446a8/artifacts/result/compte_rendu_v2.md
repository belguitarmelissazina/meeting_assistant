# Compte rendu de réunion

_Type de réunion_ : **revue projet et exploration de cas d'usage**

_Objectif_ : Faire un état des lieux des projets en cours autour de l'IA générative et identifier des cas d'usage concrets pour l'orchestration, la synthèse et l'automatisation. Prioriser les besoins et explorer des solutions souveraines et locales.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthèse

La réunion a débuté par un tour de table où chaque participant a présenté son rôle et son expertise en IA générative, notamment Maya SAHRAOUI qui a détaillé un projet RTE d'automatisation de rédaction de rapports à partir de fichiers PPT, avec une architecture en 5 briques et une boucle de correction. Les échanges ont porté sur l'adaptabilité des outils à différents templates et sur des cas d'usage comme la synthèse générative et l'orchestration via des solutions comme N8N ou MCP. Plusieurs projets ont été évoqués, incluant l'extraction d'informations à partir de documents scannés, la génération de plans de travail et l'orchestration de simulations pour des études énergétiques, avec un accent sur la souveraineté et l'intégration locale des outils. Concernant le MCP, SPEAKER_02 a indiqué l'absence de besoins clairs à ce stade, tandis que SPEAKER_00 a proposé un atelier design pour prioriser les cas d'usage, sans engagement immédiat de la part des participants.

## Sujets abordés

### 1. Tour de table et projets en cours

Un tour de table a permis de présenter les rôles et expertises des participants en IA générative. SPEAKER_00, expert DataIA et manager de la pratique DataIA au sein d’Élé Consulting, collabore notamment avec Maya SAHRAOUI sur des projets d’IA générative et intervient sur des sujets d’équilibre offre-demande et de gouvernance. Maya SAHRAOUI, consultante confirmée chez Élé, docteure en traitement automatique des langues, a détaillé un projet mené pour RTE visant à automatiser la rédaction de rapports à partir de fichiers PPT. Ce projet repose sur une architecture en cinq briques : traitement des slides (OCR, classification, description), assignation des slides aux sections du rapport selon une structure prédéfinie, rédaction section par section (d’abord en bullet points, puis en prose), intégration des sections, et boucle de correction itérative. L’objectif était d’accélérer la production des rapports tout en garantissant leur rigueur et leur traçabilité, avec une interface permettant aux utilisateurs de corriger les sections générées.

Les échanges ont porté sur l’adaptabilité de l’outil à différents templates, confirmant sa capacité à fonctionner avec ou sans structure prédéfinie, sous réserve d’ajustements mineurs. SPEAKER_02 a souligné l’absence de besoins clairs concernant le MCP à ce stade, tandis que SPEAKER_00 a proposé un atelier design pour prioriser les cas d’usage, sans engagement immédiat. Maya SAHRAOUI a également évoqué d’autres projets, comme un outil d’assistance à la rédaction d’appels d’offres orchestré via N8N, et un outil en développement de synthèse automatique de réunions, intégrant progressivement des fonctionnalités avancées (enregistrement vocal, génération de mind maps) via une interface MCP pour renforcer la souveraineté et la confidentialité des solutions.

### 2. Exploration des cas d'usage et souveraineté des outils

Plusieurs projets d'outils d'IA ont été présentés, notamment un agent de planification de POC visant à automatiser la génération de bibliographies et l'orchestration de simulations pour des études énergétiques. L'objectif est de proposer une pipeline permettant de créer rapidement un POC minimal sur un sujet donné, en s'appuyant sur des outils internes ou de simulation. Un autre projet concerne l'extraction d'informations à partir de documents scannés, incluant des documents manuscrits, avec une classification automatique et une estimation de conformité des données extraites. Ce projet intègre un modèle hébergé localement, avec un travail de fine-tuning et un déploiement via des solutions comme VLM et UVCorn, ainsi qu'un dashboard de monitoring.

L'accent a été mis sur la souveraineté des outils et leur intégration locale, avec une volonté de cloisonner les solutions au sein de l'organisation pour éviter une dépendance externe. Les échanges ont également porté sur des cas d'usage concrets, tels que la synthèse de données disparates et la gestion de notes manuscrites, tout en explorant des pistes pour l'orchestration via des serveurs MCP.

### 3. Priorisation et ateliers design

Concernant l’avancement des travaux autour du MCP, SPEAKER_02 a indiqué qu’aucun besoin clair n’avait été identifié à ce stade. Il a précisé que des actions étaient déjà prévues pour explorer cette solution, mais qu’il serait prématuré d’engager une réflexion approfondie sans éléments plus concrets. Il a suggéré de revenir vers les participants dès que des pistes plus précises émergeraient, afin d’éviter des échanges sans ancrage opérationnel.

SPEAKER_00 a proposé d’organiser un atelier design pour prioriser les cas d’usage, notamment en lien avec des approches UX. Cette initiative pourrait permettre de clarifier les attentes et d’identifier des pistes d’intégration du MCP ou d’autres outils, sans engagement immédiat de la part des participants. SPEAKER_02 a pris note de cette proposition, tout en soulignant la nécessité d’évaluer sa faisabilité en fonction des priorités et des contraintes des projets en cours.

## Plan d'action

| # | Action | Responsable | Échéance |
|---|---|---|---|
| 1 | Noter le point concernant un éventuel atelier design pour réfléchir à des cas d'usage et les prioriser. | SPEAKER_02 | — |
| 2 | Revenir vers SPEAKER_00 si des besoins plus précis (MCP ou NLP) émergent. | SPEAKER_02 | — |
