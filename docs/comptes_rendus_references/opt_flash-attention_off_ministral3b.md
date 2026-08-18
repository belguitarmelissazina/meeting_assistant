# Compte rendu de réunion

*Source : `dicte_audio_3.normalized.txt`*

## 2. Executive Summary

La réunion explore les besoins en **IA générative** pour optimiser l’interaction entre les opérateurs et leurs outils, notamment dans le domaine des assistants techniques et des rapports automatisés. Les échanges mettent en lumière des retours sur des projets comme la génération automatique de rapports d’études de rentabilité ou la synthèse de données dispersées (notes manuscrites, réunions), avec une attention particulière portée à l’orchestration modulaire via des outils internes tels que **N8N**. L’accent est mis sur la validation et l’amélioration des pipelines existants pour garantir leur robustesse tout en préservant la souveraineté technique, sans pour autant définir de priorités ou d’échéances précises. Aucune décision définitive n’a été prise concernant les prochaines étapes, mais une approche collaborative et exploratoire est retenue pour affiner les besoins et explorer des cas d’usage comme l’intégration d’un **module centralisé** (MCP) ou la gestion de données fragmentées. Les discussions restent centrées sur la prise de contact et l’évaluation des attentes avant toute action concrète.

## 3. Sujets abordés

### 1. Présentation des besoins en IA générative et partage de retours sur un projet de génération automatique de rapports

Les participants échangent sur les attentes en matière d’assistants interactifs basés sur l’IA, notamment pour optimiser la gestion des études de rentabilité des moyens de production via une automatisation partielle de la rédaction de rapports techniques.

- Mathieu et ses collègues (DataIa manager) décrivent leurs besoins en IA générative pour développer des interfaces conversationnelles fluides entre opérateurs et outils, incluant des modèles comme le MCP.
- Maya partage son expérience sur un projet RTE visant à automatiser la génération de rapports d’études de rentabilité des moyens de production à partir de fichiers PPT hétérogènes (graphiques/textes), en intégrant une boucle de correction collaborative.
- La méthode mise en œuvre par Maya repose sur une pipeline de cinq étapes : analyse des slides, assignation aux sections prédéfinies, rédaction structurée par section, intégration et validation finale avec feedback humain.
- Le projet initial s’est concentré sur un prototype validé en 25 jours (incluant ateliers), avec une boucle de correction minimale pour itérer sur les bullet points générés, avant évaluation des suites possibles.
- Les participants soulignent la nécessité d’un template structuré pour le rapport, mais évoquent la possibilité d’adapter l’outil à d’autres supports sans modèle fixe, en ajustant les directives de contenu et de temps.

### 2. Validation et robustesse d’un outil de génération multitemplate pour rapports scientifiques

Discussion sur les principes de fonctionnement et les garanties techniques d’un système permettant la production de rapports structurés à partir de multiples modèles.

- L’outil permet d’exécuter plusieurs templates distincts pour générer des sorties variées, soit par adaptations mineures ou via un agent orientant la sélection des chapitres et leur contenu.
- La segmentation en sections et l’attribution des slides à ces sections améliorent la gestion des erreurs et offrent une traçabilité pour identifier rapidement les causes de problèmes dans chaque partie du rapport.
- L’implantation de garde-fous (artefacts intermédiaires) facilite la correction itérative des sections, avec possibilité de validation humaine après chaque étape pour garantir un résultat final fiable.
- La boucle de feedback inclut l’ajout de commentaires aux sections et une régénération du rapport en fonction de ces retours, assurant ainsi une reproductibilité partielle des corrections.
- Les limites mentionnées concernent notamment l’absence d’extraction chiffrée automatisée (hors scope), la non-réconstruction graphique depuis les données brutes, et une correction limitée aux sections plutôt qu’à un niveau global du rapport.

### 3. Cas d’usage de la synthèse et orchestration de données dans des outils internes

Les échanges portent sur les besoins en intégration de sources hétérogènes (rapports, CV, réunions) pour générer des synthèses ou assister à des processus métiers comme la rédaction de réponses aux appels d’offres.

- Le projet interne utilise **N8N** pour orchestrer plusieurs agents spécialisés (CV, références, réponses aux appels d’offres) afin de répondre à des besoins en modulaire et collaboratif.
- Un autre projet en cours vise à développer un outil de génération de résumés de réunions via un système interactif (chatbot), intégrant des outils internes ou externes pour automatiser la synthèse.
- L’objectif est d’améliorer l’autonomie technique interne pour **gagner en souveraineté**, notamment sur les données confidentielles et spécialisées dans les sujets métiers de l’entreprise.

### 4. Amélioration des synthèses et gestion de projets via outils spécialisés

L’objectif est d’affiner les synthèses existantes et d’adapter leurs usages pour renforcer la souveraineté technique dans un environnement spécifique.

- Il faut augmenter la qualité et la exhaustivité des synthèses produites pour les missions d’orchestration, en lien avec leur contexte d’utilisation
- Un cloisonnement est requis pour que l’outil reste intégré à une organisation (ex. RTE) sans dépendre d’un autre environnement externe
- Pour deux projets d’orchestration spécifiques, aucune décision n’est prise sur la continuité des activités actuelles ou les adaptations nécessaires
- En parallèle, un projet de planification automatisée (hors orchestration) utilise déjà un outil web pour générer des plans de travail sans implémentation de mécanisme complémentaire (MCP)
- L’idée est d’étendre l’outil à une bibliographie et à plusieurs outils de simulation pour créer une pipeline automatique proposant un plan minimal sur demande, en vue d’accélérer les travaux sur des sujets techniques

### 5. Utilisation de modèles VLM pour l'extraction et la conformité des données dans les documents administratifs

Ce projet vise à analyser des documents scannés (administratifs ou manuscrits) via un outil d'intelligence artificielle pour extraire des informations structurées (comme salaires et métiers) et évaluer leur conformité.

- Le travail porte sur la prétraitement des documents, incluant une classification initiale entre manuscrits et non-manuscrits.
- Un modèle de vision par langage (VLM) est développé pour extraire des données spécifiques (ex. salaires nets, métiers) à partir des documents scannés.
- La conformité des extraits est vérifiée via un outil VLM en comparant les résultats avec des intervalles de référence établis précédemment.
- Le projet inclut la finetuning du modèle sur des données locales et le déploiement d’un tableau de bord pour surveiller les performances et détecter des déviations (drifts).
- La solution est adaptée aux documents rédigés en arabe ou manuscrits, avec une phase dédiée à leur traitement spécifique.

### 6. Cas d’usage et orientation des travaux autour de l’orchestration et du traitement des données

Les participants discutent des pistes concrètes pour exploiter les cas d’usage liés à la synthèse de données fragmentées (notes manuscrites, blocs d’alarme) et à l’orchestration des études techniques via un système centralisé (MCP).

- Le groupe retient comme prioritaire le développement de travaux centrés sur l’**orchestration** des outils internes pour gérer les scénarios d’études, notamment en matière de rentabilité des moyens de production.
- L’idée est d’utiliser un **MCP** (module centralisé) pour préparer et lancer automatiquement des simulations, puis relier ces résultats aux outils de génération de rapports ou de validation humaine.
- Les échanges soulignent la nécessité d’intégrer des cas d’usage comme la synthèse de données disparates (ex. : notes manuscrites, messages fragmentés), déjà partiellement traitées dans des projets existants.
- La question du **LLM** et des interactions complexes avec les outils internes est identifiée comme un enjeu clé pour le MCP, nécessitant une capacité à sélectionner dynamiquement les bons outils de simulation ou d’analyse.
- L’objectif reste de finaliser des **POC (proofs of concept)** pour valider la faisabilité de ces processus avant leur déploiement opérationnel.

### 7. Échanges sur l’intégration d’un MCP et priorisation des cas d’usage

Discussion entre deux parties pour clarifier les besoins en matière de cas d’usage impliquant un système de gestion de contenu (MCP) ou des approches liées au traitement du langage naturel (NLP).

- Le participant 02 suggère de ne pas approfondir le MCP sans précision supplémentaire sur les besoins identifiés, pour éviter une discussion non productive.
- Le participant 00 propose un atelier de réflexion UX design pour prioriser des cas d’usage et partager une vision commune, en lien avec l’équipe GALÉT et Olivier Maserol.
- Les échanges tournent autour de la nécessité de revenir vers le partenaire externe si des éléments plus concrets émergent sur les besoins ou avancées techniques.
- Aucune décision prise concernant un focus exclusif sur le MCP pour l’instant, mais des actions internes sont déjà prévues pour explorer cette piste.
- L’équipe évoque aussi des contraintes opérationnelles (disponibilité limitée des opérateurs) et la nécessité de prioriser les projets existants avant d’engager de nouvelles collaborations externes.

## 4. Décisions

_Aucune décision formellement prise._

## 5. Plan d'attaque

| # | Sujet | Action | Responsable | Échéance |
|---|-------|--------|-------------|----------|
| 1 | Amélioration des synthèses et gestion de projets via outils spécialisés | Cloisonner l’outil pour qu’il reste côté RTE (éviter une utilisation par d’autres entités comme GAILLE) | — | — |
| 2 | Échanges sur l’intégration d’un MCP et priorisation des cas d’usage | Revenir vers les interlocuteurs pour informer sur l’émergence de besoins plus précis concernant le MCP (ou d’autres cas d’usage) | — | — |
| 3 | Présentation des besoins en IA générative et partage de retours sur un projet de génération automatique de rapports | Évaluer la généralisation du projet de génération de rapports pour RTE, incluant une extension aux autres filières équilibre offre/demande | — | — |
| 4 | Amélioration des synthèses et gestion de projets via outils spécialisés | Faire des synthèses et proposer des propositions plus complètes et mieux adaptées au contexte | — | — |
| 5 | Échanges sur l’intégration d’un MCP et priorisation des cas d’usage | Présenter les travaux sur la partie MCP aux partenaires externes si nécessaire (pour éviter des discussions sans fondement) | — | — |
