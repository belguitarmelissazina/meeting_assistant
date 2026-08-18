# Compte rendu de reunion

_Type de reunion_ : **revue projet**

_Objectif_ : Évaluer les besoins métiers liés à la feuille de route Smart Cockpit pour optimiser les interactions opérateur-assistants via l’IA générative (NLP/MCP), tout en priorisant les axes techniques (orchestration, traitement des données fragmentées) et méthodologiques (robustesse des outils, souveraineté des données).

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthese

Cette réunion a porté sur une analyse approfondie des projets existants de RTE autour de l’IA générative, notamment pour automatiser la rédaction de rapports métiers (rentabilité, études techniques) et structurer les interactions opérateur-assistants. Les échanges ont mis en lumière les contraintes actuelles : limites des outils de génération partielle, besoin de robustesse dans le traitement des données fragmentées ou manuscrites, et nécessité d’améliorer l’orchestration des systèmes pour éviter les transferts vers d’autres services. Le MCP a été évoqué comme un enjeu central pour préparer automatiquement des pré-rapports ou gérer des scénarios complexes (simulations, notes d’alarmes), mais sans décision formelle sur son déploiement immédiat. Les participants ont aussi souligné l’importance de clarifier les besoins métiers avant toute action concrète, notamment via une collaboration avec un cabinet UX design externe pour prioriser des cas d’usage. Aucune action définie n’a été retenue aujourd’hui, mais des pistes comme la validation externe des besoins ou le déploiement itératif des solutions identifiées ont été notées pour les prochaines étapes.

## 1. Présentation des participants et objectifs de la réunion sur l’IA générative pour RTE

Lors de cette première phase de tour de table, les participants ont échangé sur leurs rôles respectifs au sein des projets liés à l’IA générative et aux assistants interactifs pour RTE. Nourredine HENKA, expert Data-IA manager chez Élé Consulting, a présenté son expertise en gestion de la pratique Data-IA, incluant des collaborations avec Maya SAHRAOUI sur les sujets d’IA générative ainsi que des missions techniques autour de l’équilibre offre-demande et de la rentabilité des moyens de base. Maya SAHRAOUI, consultante confirmée chez IVB, a quant à elle souligné son parcours académique en traitement automatique des langues et son expérience en projets internes et externes d’IA générative, notamment au sein de RTE avec des équipes spécialisées dans les rapports métiers et l’automatisation des analyses techniques. Jérôme PICAULT, responsable de la feuille de route Smart Cockpit à la direction Intelligence Artificielle et Innovation, a détaillé son rôle central dans l’interaction opérateur-assistants, en insistant sur l’évolution historique des assistants pour la conduite depuis plus d’une décennie. Il a également précisé travailler sur les réseaux de neurons pour l’écosystème RTE et évoqué une expertise croisée avec des collègues sur un modèle spécifique de gestion des congestions. Bruno LEMETAYER, en poste à la direction RD, a souligné son expérience pluriannuelle dans la thématique des assistants interactifs, tout en reconnaissant des lacunes concrètes sur les activités métiers spécifiques du groupe. Matthieu DUSSARTRE, également présent sans présentation explicite de ses missions, a été mentionné comme participant actif à ces échanges initiaux pour clarifier les besoins et attentes liés à l’IA générative. L’accent a été mis sur la nécessité d’explorer concrètement les besoins métiers pour structurer les interactions fluides entre opérateurs et assistants via des outils comme le NLP ou le MCP, sans pour l’instant engager de décisions formelles ni définir d’actions immédiates.

## 2. Besoins métiers et enjeux de la feuille de route Smart Cockpit

Lors de cette discussion, les échanges ont porté sur l’articulation entre les besoins métiers liés à la gestion des études de rentabilité et de simulations énergétiques, en lien avec le rôle spécifique du Modèle Conversational Platform (MCP) pour RTE. Les participants ont exploré comment ce dernier pourrait structurer des interactions complexes entre outils fragmentés ou manuscrits, sans pour autant trancher sur les priorités immédiates.

- Les besoins métiers en cours d’analyse concernent la préparation automatisée de pré-rapports dans le cadre des études techniques liées à la rentabilité des moyens de production énergétique.
- Le MCP serait utilisé pour orchestrer l’exécution de simulations et relier automatiquement les outils internes existants aux directives générées par un premier assistant, afin d’éviter les transferts manuels vers d’autres services.
- L’objectif est aussi de permettre une synthèse dynamique des données disparates, comme les blocs d’alarmes ou les messages fragmentés, pour en extraire des informations exploitables dans des rapports structurés.
- La gestion des documents manuscrits constitue un cas d’usage prioritaire, où le MCP permettrait de dispatcher et d’intégrer ces données brutes avant leur traitement par des outils NLP dédiés.
- Les échanges soulignent l’importance de clarifier les scénarios complexes, notamment ceux impliquant des hypothèses variées ou des ajustements en temps réel sur la programmation des machines et les consommations énergétiques.
- La robustesse de l’orchestration serait cruciale pour éviter les erreurs lors du passage entre outils spécialisés (simulateurs, visualisateurs) et garantir une continuité logique dans le processus d’étude, avant validation humaine finale.

## 3. Avancement des projets d’automatisation et orchestration d’outils génératifs

Lors du projet mené dans l’équipe équilibre offre et demande, l’objectif consistait à automatiser la rédaction de rapports métiers détaillant les études de rentabilité des moyens de production. L’équipe utilisait déjà un outil interne nommé Power pour analyser ces données, mais les résultats étaient stockés sous forme de fichiers PPT contenant principalement des graphiques et peu de texte, rendant leur intégration dans des rapports structurés complexe.

## 4. Rôle du MCP dans l’orchestration et la gestion des données fragmentées

Lors du débat sur les interactions entre traitement des données fragmentées par NLP et rôle du MCP, les échanges ont mis en lumière la complémentarité entre ces deux approches pour structurer des pré-rapports ou orchestrer des études techniques complexes. Les participants ont souligné comment le MCP pourrait servir de passerelle vers des outils internes existants, notamment pour automatiser la préparation de scénarios ou d’études, tout en garantissant une interaction fluide avec les agents génératifs.

- les discussions ont souligné que le traitement NLP permet de synthétiser des données dispersées (blocs d’alarme, messages manuscrits ou fragments textuels) pour alimenter des cas d’usage orientés vers la gestion de notes ou l’analyse de situations fragmentées.
- l’équipe évoque un besoin accru de MCP pour orchestrer des workflows complexes, comme la récupération d’hypothèses ou de données d’entrée (consommation, production, programmation) afin de naviguer entre différents outils internes (simulateurs, visualisateurs), sans dépendre systématiquement d’interventions humaines.
- les échanges ont aussi révélé que le MCP pourrait préparer automatiquement des pré-rapports en tant qu’interface intermédiaire : il structurerait les scénarios générés par un agent, relierait ces données aux outils de simulation existants et permettrait une validation itérative avant finalisation par l’humain.
- la robustesse de cette orchestration repose sur la capacité du MCP à gérer des flux dynamiques (ex. : ajustements en temps réel d’hypothèses ou vérifications de cohérence entre études), tout en conservant un contrôle métier pour les étapes critiques comme le lancement finalisé des simulations.
- les participants ont noté que, bien que le NLP soit déjà utilisé pour extraire du texte manuscrit ou fragmenté, la question du serveur MCP (en tant qu’outil dédié) reste pertinente pour des cas d’usage avancés où l’interaction avec des systèmes internes complexes est nécessaire.

## 5. Pistes pour prioriser les cas d’usage via une approche UX design externe

Lors de ce échange, les participants ont exploré la possibilité d’approfondir une réflexion sur des cas d’usage centrés sur le MCP, en s’appuyant notamment sur l’exemple concret de l’EMCP. Un participant souligne qu’actuellement, aucun besoin métier clair n’est encore identifié pour intégrer ces outils, et propose de revenir vers les équipes concernées dès que des éléments plus précis émergeront, afin d’éviter une discussion sans fondement.

## 6. Plan d'action

Lors de la discussion sur les besoins métiers pour le Smart Cockpit, l’équipe aborde notamment la généralisation d’un outil de génération de rapports existant et explore les pistes liées au MCP (assistant métier).

| # | Action | Responsable | Echeance |
|---|---|---|---|
| 1 | Évaluer les suites pour la généralisation de l’outil de génération de rapports en dehors du contexte RTE, en concertation avec Gérald pour évaluer son intérêt pour d’autres équipes ou filières. | — | — |
| 2 | Tenir informé des besoins précis émergents concernant le MCP ou d’autres cas d’usage liés au NLP afin d’éviter une discussion sans fondement, sous l’égide de Jérôme PICAULT. | Jérôme PICAULT | — |
| 3 | Revoir les travaux sur la partie MCP et partager leur vision pour un éventuel second échange si nécessaire. | — | — |

