# Compte rendu de reunion

_Type de reunion_ : **brainstorm**

_Objectif_ : Explorer les synergies techniques autour de l’IA générative, des outils de traitement automatisé des données (comme la génération de rapports à partir de PPT ou d’études) et des systèmes d’or­chestration (MCP), en priorisant les besoins métiers sans encadrer immédiatement une mission spécifique. L’accent est mis sur l’échange d’expertises pour affiner des projets existants ou futurs, notamment via des ateliers collaboratifs.

_Participants_ : Bruno LEMETAYER, Matthieu DUSSARTRE, Nourredine HENKA, Jérôme PICAULT, Maya SAHRAOUI, Jérôme MASSET

## Synthese

Cette réunion a servi de cadre à un échange technique approfondi entre les participants autour de trois axes principaux : l’IA générative et ses applications métiers (notamment dans la gestion d’assistants pour opérateurs ou la synthèse de données dispersées), les méthodes d’automatisation des processus créatifs (comme la transformation de présentations PowerPoint en rapports structurés) et les systèmes d’or­chestration comme le MCP. Les discussions ont débuté par un tour de table pour clarifier les rôles et expertises, notamment Maya SAHRAOUI sur l’industrialisation des workflows génératifs chez IVB ou Élé Consulting, tandis que Jérôme MASSET a présenté son rôle dans la feuille de route *Smart Cockpit*. Le besoin central était d’aligner les développements techniques (ex : modèles locaux comme Mistral) avec les attentes opérationnelles (gestion des congestions, streaming), sans pour autant trancher sur une priorisation immédiate. Les échanges ont aussi exploré des cas concrets comme la création de POC pour valider l’intégration d’agents génératifs avec des outils internes, ou encore l’atelier UX suggéré par Matthieu DUSSARTRE pour prioriser les usages MCP. Aucune décision formelle n’a été prise, mais une phase informelle de prise de contact et d’exploration des compétences a été engagée, notamment via la proposition de Maya SAHRAOUI de présenter ses projets antérieurs en traitement multimodal ou l’évaluation des besoins autour du MCP. Les travaux sur l’automatisation des rapports (ex : chaîne à cinq étapes pour les PPT) ont aussi été évoqués comme un exemple concret d’application, avec une boucle de correction itérative intégrée.

## 1. Présentation des rôles et expertises autour de l’IA générative et des projets transversaux

Lors du tour de table, les participants ont partagé leurs rôles respectifs et leurs expertises techniques autour des enjeux liés à l’IA générative et aux projets transversaux en cours. Cette phase a permis d’affiner la compréhension des contributions individuelles dans le cadre des discussions sur les synergies technologiques et métiers.

- Matthieu DUSSART présente son rôle de manager de la pratique Data-IA chez Élé Consulting, où il coordonne notamment des projets liés à l’IA générative en collaboration avec Maya SAHRAOUI. Il intervient également sur les aspects d’équilibre entre offre et demande ainsi que sur les analyses métiers orientées régulation et gouvernance.
- Maya SAHRAOUI se définit comme consultante confirmée chez IVB, spécialisée dans l’industrialisation des workflows génératifs. Elle a mené des projets similaires chez RTE avec des partenaires spécifiques et détient un doctorat en traitement automatique des langues, approfondissant les applications du deep learning.
- Son expertise couvre notamment le développement de solutions multimodales pour des besoins opérationnels variés, tout en s’appuyant sur une expérience antérieure dans la gestion de projets techniques et collaboratifs.

## 2. Applications techniques : automatisation des rapports, assistants métiers et orchestration MCP

La discussion a porté sur des applications concrètes d’automatisation des rapports à partir de présentations PowerPoint, en mettant l’accent sur une chaîne de traitement structurée en cinq étapes. Maya SAHRAOUI a détaillé un projet réalisé pour RTE et Élé Consulting, où le but était de générer des études de rentabilité des moyens de production à partir de fichiers PPT riches en graphiques et peu textuels. La méthodologie consistait à extraire des descriptions exhaustives de chaque slide via une analyse multimodale (OCR + analyse visuelle), puis à assigner systématiquement les slides aux sections prédéfinies du rapport, en intégrant des règles métiers pour éviter les erreurs d’orientation.

## 3. Phase exploratoire : besoins en MCP, ateliers UX et prise de contact informelle

Lors de cette phase exploratoire, les échanges ont porté sur la nécessité d’affiner les besoins métiers liés au système d’orchestration MCP sans formaliser de priorités immédiates. Matthieu DUSSART a proposé un atelier UX pour prioriser des cas d’usage futurs, tandis que Jérôme MASSET a souligné l’importance d’une prise de contact informelle entre équipes avant toute action concrète.

- Jérôme MASSET souligne la nécessité de clarifier les besoins techniques autour du MCP sans trancher sur une mission immédiate, en insistant sur le besoin de coordination avec les services concernés pour identifier des briques d’études ou de calcul à explorer.
- Il propose un échange informel pour échanger sur les compétences et les projets antérieurs de Maya SAHRAOUI dans le traitement multimodal, afin de structurer une collaboration future sans engagement formel.
- Matthieu DUSSART suggère un atelier UX pour prioriser des usages du MCP, en s’appuyant sur des retours avec des cabinets spécialisés en design d’interfaces comme Olivier Maserol pour la *Smart Cockpit*, sans préjuger de l’acceptation immédiate.
- L’idée est de recueillir une vision commune des besoins avant de valider un second échange ou une intégration spécifique, en gardant à l’esprit les contraintes opérationnelles liées aux ressources disponibles pour les opérateurs.

## 4. Décisions

Cette discussion porte sur les détails techniques de l’automatisation des rapports à partir de présentations PowerPoint, notamment la validation des structures communes et des boucles de correction itérative. Les échanges ont permis d’affiner une chaîne de traitement en cinq étapes pour garantir la cohérence entre les données générées et les attentes métiers.

| # | Sujet | Decision |
|---|---|---|
| 1 | Structure commune du rapport avec quatre sections prédéfinies | Les descriptions métiers des différentes sections ont été finalisées et intégrées dans le processus d’assignation des slides, sans décision formelle de validation collective pendant la réunion |
| 2 | Règles spécifiques pour l’assignation des slides selon les comparaisons France/Europe | Les règles d’assignement ont été discutées et intégrées dans le pipeline, mais aucune décision explicite sur leur application immédiate n’a été prise pendant la réunion |
| 3 | Boucle de correction itérative via une interface dédiée avec commentaires | La boucle de correction a été validée comme un élément clé du processus, mais son déploiement concret reste à formaliser après cette phase d’échange |
| 4 | Ajout d’une transcription vocale (format TXT) issue d’enregistrements Spitch | L’option a été testée et intégrée comme entrée complémentaire, mais son utilisation systématique n’a pas fait l’objet d’un accord formel pendant la réunion |

## 5. Plan d'action

_Section non rendue (Expecting value: line 1 column 1 (char 0))._

