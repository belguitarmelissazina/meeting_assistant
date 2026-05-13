# `--cache-reuse N` dans llama.cpp — Analyse technique détaillée

Document de référence sur le fonctionnement exact du mécanisme de réutilisation du KV cache dans llama-server, basé sur le code source.

**Sources principales** :
- [PR #9866 — server : reuse cached context chunks](https://github.com/ggml-org/llama.cpp/pull/9866) (ggerganov, octobre 2024)
- [tools/server/server-context.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-context.cpp)
- [tools/server/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- Issue [#5793](https://github.com/ggml-org/llama.cpp/issues/5793) (proposition originale)

---

## 1. Définition officielle

Extrait du README llama-server :

> `--cache-reuse N` — min chunk size to attempt reusing from the cache via KV shifting, requires prompt caching to be enabled (default: 0)

Donc :
- **N = 0** : feature **désactivée** (défaut)
- **N ≥ 1** : feature activée, longueur minimale d'un match pour être réutilisable
- Requiert `cache_prompt: true` côté requête (qui est le défaut sur `/v1/chat/completions` mais pas sur `/completion`)

Exemple canonique donné par la PR #9866 :

```
cached_prompt: aaaaabbbbbcccccccdddddeeeeeexffggggghhhhhhhxxxxxxxxx
new_prompt:    aaaaaccccccceeeeeeffhhhhhhhyyyyyyyy
```

Avec `--cache-reuse 3`, l'algorithme va réutiliser les runs `aaaaa`, `ccccccc`, `eeeeee`, `ff`, `hhhhhhh` (chacun ≥ 3 tokens) en **shiftant physiquement les positions KV** plutôt qu'en re-prefillant.

---

## 2. Code source exact (algorithme du loop)

Fichier : [`tools/server/server-context.cpp`](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-context.cpp) (~lignes 2433–2483, master)

```cpp
// Initialisation : commence au plus long prefixe commun naturel
size_t head_c = slot.prompt.tokens.get_common_prefix(input_tokens);
size_t head_p = head_c;

while (head_c < slot.prompt.tokens.size() && head_p < input_tokens.size()) {

    // Compte les tokens consecutifs qui matchent à partir de head_c et head_p
    size_t n_match = 0;
    while (head_c + n_match < slot.prompt.tokens.size() &&
           head_p + n_match < input_tokens.size()       &&
           slot.prompt.tokens[head_c + n_match] == input_tokens[head_p + n_match]) {
        n_match++;
    }

    if (n_match >= (size_t) n_cache_reuse) {
        // Match suffisant => KV shift
        const int64_t kv_shift = (int64_t) head_p - (int64_t) head_c;
        llama_memory_seq_rm (llama_get_memory(ctx_tgt), slot.id, head_p, head_c);
        llama_memory_seq_add(llama_get_memory(ctx_tgt), slot.id, head_c, head_c + n_match, kv_shift);
        // ... mise a jour KV ...
        head_c += n_match;
        head_p += n_match;
    } else {
        // Pas de match => seul head_c avance
        head_c += 1;
    }
}
```

---

## 3. Le mécanisme étape par étape

### Comportement de `head_c` et `head_p`

| Cas | `head_c` (cache) | `head_p` (new prompt) |
|---|---|---|
| Match ≥ N tokens trouvé | avance de `n_match` | **avance de `n_match`** |
| Mismatch (n_match < N) | avance de 1 | **reste sur place** |

**Le point critique** : `head_p` ne bouge **JAMAIS** sans un match validé.

### Conséquence : règle pratique

L'algorithme demande implicitement :
> *"Le contenu commençant à `new_prompt[head_p]` doit exister sous forme contiguë (≥ N tokens) quelque part dans le cache."*

Quand `head_p = 0` au début du loop, cela signifie :
> *"Le nouveau prompt DOIT commencer par du contenu qui existe quelque part dans le cache, sur ≥ N tokens consécutifs."*

Sinon, `head_c` finit par walker tout le cache sans rien trouver, le loop se termine, et `head_p` est resté à 0 — **toute la requête doit être re-prefillée**.

---

## 4. Pourquoi `head_p` ne peut pas "sauter" pour aller chercher le chunk plus loin

C'est la question subtile : *"Pourquoi l'algo ne saute pas avec un offset pour matcher le chunk text qui est au milieu du new prompt ?"*

### La réponse technique

Imaginons que le code FAISAIT ça (= si on permettait à `head_p` d'avancer sans match) :

```cpp
// VERSION HYPOTHETIQUE (qui n'existe PAS dans llama.cpp)
while (...) {
    n_match = compte_match();
    if (n_match >= N) {
        head_c += n_match;
        head_p += n_match;
    } else {
        head_c += 1;
        head_p += 1;   // ⚠️ on avance aussi dans le new prompt
    }
}
```

Problème : **on perdrait l'information sur ce qui n'a pas matché**.

Concrètement, si le new prompt est `[A B C ...]` et qu'aucun de A, B, C n'est dans le cache :
- Le KV final aurait des "trous" : les positions 0, 1, 2 du new prompt ne sont nulle part en cache
- Mais on a déjà avancé `head_p` à 3
- Quand on trouve un match à `new_prompt[3..]`, on le shifte à la position 3
- Mais les positions 0-2 sont **vides** dans le KV ! L'attention ne pourra pas regarder en arrière.

L'attention transformer est **causale** : chaque token regarde tous les tokens précédents. Si on autorise des "trous" dans le KV, le modèle calcule une attention sur du KV partiellement vide → output corrompu.

### Donc l'algo a une contrainte fondamentale

Pour qu'un chunk soit réutilisé via `--cache-reuse` :
- Soit il est au **début du new prompt** (head_p part de 0 et matche directement)
- Soit il y a **continuité dans le matching** : tout ce qui est avant le chunk dans le new prompt doit lui aussi exister dans le cache, dans le même ordre

C'est exactement pour ça que `--cache-reuse` est appelé **"reuse via KV shifting"** dans la doc : il ne fait que **décaler** des chunks existants, il ne peut pas remplir des trous.

---

## 5. Cas réel : pourquoi Normal Extraction ne réutilise pas le chunk

### Setup

Après un appel résumé sur chunk_0, le slot contient :
```
KV_cache = [résumé_instructions (~300 tok)] [chunk_0 (~3000 tok)] [response]
```

Maintenant arrive l'appel extraction sur **le même chunk** :
```
new_prompt = [extraction_instructions (~400 tok)] [chunk_0 (~3000 tok)]
```

### Déroulement du loop

`head_c = 0`, `head_p = 0`

**Itération 1** :
- `cache[0]` = "Résume" (1er token de résumé_instructions)
- `new[0]` = "Extrais" (1er token de extraction_instructions)
- Mismatch → `head_c = 1`, `head_p = 0`

**Itération 2** :
- `cache[1]` = "cet"
- `new[0]` = "Extrais" (head_p toujours à 0 !)
- Mismatch → `head_c = 2`, `head_p = 0`

**...itérations 3 à 300** :
- `head_c` scanne tout résumé_instructions, comparant chaque token avec "Extrais"
- Aucun match évidemment → `head_p` reste bloqué à 0

**Itération 301** :
- `head_c` arrive à la zone chunk dans le cache
- `cache[300]` = 1er token du chunk (ex: "Bonjour")
- `new[0]` = "Extrais"
- Mismatch → `head_c = 301`, `head_p = 0`

**Itérations 302 à 3300** :
- `head_c` scanne tout le chunk dans le cache
- Compare chaque token du chunk avec "Extrais"
- Si "Extrais" apparaît par hasard dans le chunk (peu probable), on aurait un match de longueur 1
- Mais il faudrait que les 256 tokens suivants matchent aussi "les décisions de cet extrait..."
- Ces 256 tokens ne sont pas dans le chunk → match rejeté

**Fin du loop** :
- `head_c` arrive à `cache.size()` → loop termine
- `head_p` est toujours à 0
- Conclusion : full prefill des 3400 tokens du new prompt

### Le chunk était pourtant dans le cache !

C'est ça le paradoxe : le chunk_0 est physiquement dans le KV cache (positions 300-3300), mais l'algorithme ne peut pas l'utiliser parce que **pour atteindre le chunk dans le new prompt, il faudrait que head_p sauter par-dessus extraction_instructions, ce qui créerait un trou dans le KV.**

---

## 6. Pourquoi pas augmenter N ?

Augmenter `--cache-reuse N` (ex: N=1000) ne change RIEN au problème ci-dessus. La règle reste la même :
- Si aucun match ≥ N n'est trouvable depuis `head_p=0`, full prefill
- L'augmentation de N ne fait que **rejeter des matches courts** (qui de toute façon ne se produisent pas chez nous)

→ N=256 ou N=1000 ou N=10000 : même résultat sur Normal Extraction (= 0 réutilisation).

---

## 7. Pourquoi pas réduire N ?

Tentation : "N=10 ou N=1, comme ça même un petit fragment fortuit du chunk match avec quelque chose d'extraction_instructions ?"

**Dangereux**. Avec N petit, l'algorithme accepte des matches courts qui peuvent être de pures coïncidences statistiques :

| N | Effet |
|---|---|
| N=256 | Match seulement sur séquences vraiment significatives (~1 phrase) |
| N=10 | Match sur des mots-phrases banals ("dans le cadre de") → coïncidences |
| N=1 | Match sur n'importe quel token isolé → chaos total |

Quand un match fortuit est accepté, l'algorithme effectue un **shift de KV** qui réorganise des positions sans cohérence sémantique. Le modèle voit un KV avec :
- Positions 0-N tokens d'une instruction
- Positions N-M tokens d'un fragment du chunk pris hors-contexte
- etc.

Output → corruption silencieuse. Le modèle peut produire du texte qui SEMBLE correct mais dont les décisions/résumés sont **basés sur un contexte mélangé**.

→ N=256 est volontairement assez grand pour exclure les coïncidences statistiques sur du texte naturel.

---

## 8. Les solutions hors `--cache-reuse`

### Option A — Restructurer les prompts (inversion)

**LA solution pratique dans le cadre llama.cpp.** Mettre le contenu commun (chunk text) au DÉBUT du new prompt garantit que `head_p` matche dès la position 0.

```
Avant (Normal) :
  cache = [résumé_instr | chunk | response]
  new   = [extr_instr | chunk]
  
  head_p reste à 0, full prefill

Après (Inversé) :
  cache = [chunk | résumé_instr | response]
  new   = [chunk | extr_instr]
  
  head_p match le chunk dès position 0, advance massivement
  Seul [extr_instr] doit être prefillé après
```

### Option B — Slot save/restore

Endpoints `/slots/{id}/save` et `/slots/{id}/restore` permettent de sérialiser le KV d'un slot vers/depuis disque. Tu peux pré-calculer le KV du chunk et le restaurer pour chaque appel.

⚠️ Mais cela ne change rien à l'algorithme : la requête HTTP suivante DOIT démarrer par le même contenu que le KV restauré. Donc **revient à structurer son prompt comme l'inversion**.

### Option C — API C directe (`llama_memory_seq_*`)

Si on intègre llama.cpp comme bibliothèque (pas comme serveur), on peut manipuler le KV manuellement avec les primitives `llama_memory_seq_rm`, `seq_add`, `seq_cp`, `seq_keep`. Permet d'implémenter un **content-addressable cache** custom.

Coût : plusieurs semaines de C/C++. C'est ce que font les forks comme [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp).

### Option D — Changer de moteur

- **SGLang** ([arXiv:2312.07104](https://arxiv.org/abs/2312.07104)) : **RadixAttention** — trie radix qui hash chaque préfixe de tokens, lookup content-addressable, réutilisation où qu'elle soit dans n'importe quelle requête, cross-session.
- **vLLM** : **automatic prefix caching** — block-level hash table, principe similaire.

Tous deux GPU-only en pratique (NVIDIA CUDA).

---

## 9. Limitations connues de `--cache-reuse`

Issues GitHub documentant les cas où cache-reuse ne fonctionne pas :

| Cas | Référence |
|---|---|
| Modèles multimodaux (`has_mtmd`) | gate `!has_mtmd` dans le code |
| Gemma SWA (Sliding Window Attention) | [#21468](https://github.com/ggml-org/llama.cpp/issues/21468) |
| Qwen3-Next (architecture hybride) | [#18497](https://github.com/ggml-org/llama.cpp/issues/18497) |
| Régression entre certains commits | [#15082](https://github.com/ggml-org/llama.cpp/issues/15082) |
| Architectures avec recurrent state | en cours |

Pour Ministral 3B / Qwen 2.5 / Llama 3.2 (architectures Transformer standard), cache-reuse fonctionne normalement.

---

## 10. Distinction avec d'autres features

### `--no-context-shift`

Feature **différente** : se déclenche quand la génération dépasse `n_ctx`. Décale les tokens vers la gauche pour libérer de la place en queue. Utilise les mêmes primitives `llama_memory_seq_*` mais dans un but différent.

Référence : Issue [#9390](https://github.com/ggml-org/llama.cpp/issues/9390).

### `--cache-ram` / `-cram` (PR [#16391](https://github.com/ggml-org/llama.cpp/pull/16391))

Cache de prompts en RAM hôte (host memory), partagé entre slots. Sélection par **similarité de préfixe** — donc **soumis à la même contrainte que `--cache-reuse`** : le nouveau prompt doit commencer par contenu connu.

Discussion : [#20574](https://github.com/ggml-org/llama.cpp/discussions/20574).

### `cache_prompt: true` (per-request)

Active la voie de réutilisation du prefixe commun. Sans, `n_past = 0` et tout est re-prefillé. Défaut **vrai** sur `/v1/chat/completions`, défaut **faux** sur `/completion`.

---

## 11. TL;DR — règles pratiques pour ton pipeline

1. **`--cache-reuse N` ne peut pas "retrouver" du KV ailleurs dans le new prompt.** Il a besoin que le new prompt commence par contenu cache.
2. **Augmenter ou diminuer N ne change rien** au problème (et N petit corrompt même le résultat).
3. **La seule façon pratique** dans llama.cpp d'avoir du KV reuse entre `résumé(chunk_X)` et `extraction(chunk_X)` :
   - Structurer les prompts comme `[chunk_text] [instructions_specifiques]`
   - Pas `[instructions_specifiques] [chunk_text]`
4. **Le bénéfice attendu** : ~×2 sur le wall time par chunk (économie du prefill du chunk entre les 2 appels).
5. **Le risque** : qualité dégradée si le modèle n'est pas entraîné pour digérer des instructions en fin de prompt. À valider empiriquement.
6. **Hors llama.cpp** : vLLM/SGLang ont des solutions content-addressable, mais GPU-only.

---

---

## 12. Littérature académique soutenant la structure document-first / instruction-last

L'inversion (chunk text avant instructions) n'est pas un hack ad-hoc — c'est une stratégie **massivement documentée** dans la littérature top-tier 2021-2026, à la fois côté **précision modèle** et côté **efficacité d'inférence**.

### 12.1 — Tableau des papers de référence

| # | Paper | Auteurs | Venue / Année | arXiv | Contribution clé pour notre cas |
|---|---|---|---|---|---|
| 1 | **Lost in the Middle: How Language Models Use Long Contexts** | Liu, Lin, Hewitt, Paranjape, Bevilacqua, Petroni, Liang | **TACL 2024** | [2307.03172](https://arxiv.org/abs/2307.03172) | Précision en U sur la position de l'info-clé : pic au début et à la fin, creux au milieu. Query-aware contextualization (répéter la question après le doc) récupère la perte. **~2000 citations.** |
| 2 | **Found in the Middle: Calibrating Positional Attention Bias** | Hsieh, Chuang, Li, Sun, Krishna, Khurana, Yih, Wang | **ACL Findings 2024** | [2406.16008](https://arxiv.org/abs/2406.16008) | Démontre que le biais U-shape vient d'un biais d'attention intrinsèque ; calibration runtime sans retraining. |
| 3 | **Found in the Middle: Plug-and-Play Positional Encoding (Ms-PoE)** | Zhang, Liu, Jaiswal, Chen, et al. | **NeurIPS 2024** | [2403.04797](https://arxiv.org/abs/2403.04797) | Rescaling RoPE per-head supprime lost-in-the-middle sans fine-tune. |
| 4 | **Make Your LLM Fully Utilize the Context (FILM-7B / IN2)** | An, Ma, Lin, et al. (Microsoft) | **NeurIPS 2024** | [2404.16811](https://arxiv.org/abs/2404.16811) | Training intensif sur l'info au milieu : supprime le middle blind spot. |
| 5 | **Same Task, More Tokens: the Impact of Input Length on Reasoning** | Levy, Jacoby, Goldberg | **ACL 2024** | [2402.14848](https://arxiv.org/abs/2402.14848) | Précision tombe 0.92 → 0.68 BIEN avant la limite de contexte annoncée ; la position du padding compte. |
| 6 | **RULER: What's the Real Context Size of Your Long-Context LMs?** | Hsieh, Sun, Kriman, et al. (NVIDIA) | **COLM 2024** | [2404.06654](https://arxiv.org/abs/2404.06654) | La plupart des "long-context models" s'effondrent bien avant leur fenêtre théorique sur multi-hop / aggregation. |
| 7 | **Fantastically Ordered Prompts and Where to Find Them** | Lu, Bartolo, Moore, Riedel, Stenetorp | **ACL 2022 (Outstanding Paper)** | [2104.08786](https://arxiv.org/abs/2104.08786) | L'ordre des few-shot exemplars peut faire varier la perf de "near-random" à SOTA. ~800+ citations. |
| 8 | **Calibrate Before Use: Improving Few-Shot Performance** | Zhao, Wallace, Feng, Klein, Singh | **ICML 2021** | [2102.09690](https://arxiv.org/abs/2102.09690) | GPT-3 biaisé envers les labels en FIN de prompt — preuve directe de **recency bias**. ~1000+ citations. |
| 9 | **Primacy Effect of ChatGPT** | Wang, Zhu, Saxon, Steyvers, Wang | **EMNLP 2023** | [2310.13206](https://arxiv.org/abs/2310.13206) | ChatGPT biaisé envers la 1ère option en MCQA — preuve directe de **primacy effect** sur les modèles instruction-tuned. |
| 10 | **Eliminating Position Bias of Language Models (PINE)** | Wang, Shen, Zhang, et al. | **ICLR 2025** | [2407.01100](https://arxiv.org/html/2407.01100v2) | Démonstration mécaniste : position bias = causal mask + positional encoding ; PINE rend l'inférence position-invariante. |
| 11 | **StreamingLLM (Attention Sinks)** | Xiao, Tian, Chen, Han, Lewis | **ICLR 2024** | [2309.17453](https://arxiv.org/abs/2309.17453) | Les premiers tokens absorbent une attention disproportionnée ("sinks") — pertinent pour expliquer pourquoi un system prompt en début reste stable. ~800+ citations. |
| 12 | **Efficient Memory Management for LLM Serving with PagedAttention (vLLM)** | Kwon et al. | **SOSP 2023** | [2309.06180](https://arxiv.org/abs/2309.06180) | Paging-based KV cache avec partage de préfixe ; ×2-4 throughput. Motive structurellement le pattern document-first. ~1500+ citations. |
| 13 | **SGLang: Efficient Execution of Structured LM Programs (RadixAttention)** | Zheng, Yin, Xie, Sun, et al. | **NeurIPS 2024 Spotlight** | [2312.07104](https://arxiv.org/abs/2312.07104) | Radix-tree KV cache, réutilisation automatique de tout préfixe ; ×6.4 throughput. Le préfixe commun statique doit précéder la query variable. |
| 14 | **Hydragen: High-Throughput LLM Inference with Shared Prefixes** | Juravsky, Brown, Ehrlich, Fu, Ré, Mirhoseini | arXiv 2024 | [2402.05099](https://arxiv.org/abs/2402.05099) | Décomposition attention sur préfixe partagé vs suffixe variable : **jusqu'à ×32 speedup**. Throughput reste stable même quand le préfixe grandit de 1K à 16K tokens. |
| 15 | **Prompt Cache: Modular Attention Reuse for Low-Latency Inference** | Gim, Chen, Lee, Sarda, Khandelwal, Zhong | **MLSys 2024** | [2311.04934](https://arxiv.org/abs/2311.04934) | Pré-calcul des attention states pour modules réutilisables : TTFT divisé sur QA grounded. Schema assume document/system avant user query. |
| 16 | **On the Emergence of Position Bias in Transformers** | (auteurs) | arXiv 2025 | [2502.01951](https://arxiv.org/abs/2502.01951) | Formalisation théorique via graph-theoretic model : causal masking pousse l'attention vers les positions précoces. |
| 17 | **Attention Sorting Combats Recency Bias** | Peysakhovich & Lerer | arXiv 2023 | [2310.01427](https://arxiv.org/abs/2310.01427) | Re-ordonner les docs retrievés selon l'attention récupère la précision perdue par le recency bias. |

### 12.2 — La citation Anthropic (documentation officielle)

Anthropic donne **explicitement** la recommandation document-first / instruction-last dans sa doc officielle :

> *"Put longform data at the top: place your long documents and inputs (~20K+ tokens) near the top of your prompt, above your query, instructions, and examples. This can significantly improve Claude's performance across all models. **Queries at the end can improve response quality by up to 30%.**"*

Source : [docs.anthropic.com/.../long-context-tips](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips)

C'est l'engagement empirique le plus public d'un fournisseur de LLM sur l'effet quantitatif de la structure document-first.

### 12.3 — Le consensus académique en 4 points

#### 1. L'efficacité d'inférence EXIGE document-first

Tous les systèmes prefix-caching en production réutilisent **uniquement le préfixe commun** d'une requête :
- vLLM (PagedAttention) — papers #12
- SGLang (RadixAttention) — papers #13
- Hydragen — papers #14
- Prompt Cache — papers #15
- Anthropic's own prompt cache (commercial)

→ Mettre du contenu variable (question, instructions spécifiques) AVANT le contenu statique (document, chunk) **détruit les cache hits**. **Instruction-last est essentiellement obligatoire pour bénéficier des optimisations modernes d'inférence.**

#### 2. La précision favorise document-first quand la question est en fin

- **Liu et al. 2023** (papier #1) : courbe en U sur la position de l'info-clé. Query-aware contextualization (répéter la question après le doc) récupère la perte.
- **Anthropic** : empiriquement +30% sur "Claude across all models" quand la query est en fin.
- **Levy et al. 2024** (papier #5) : la position du padding compte dans le reasoning long-context.

#### 3. Le pire cas absolu = info-clé au MILIEU

Documenté de façon convergente par :
- Liu 2023 (#1)
- Hsieh 2024 — Found in the Middle (#2)
- Zhang 2024 — Ms-PoE (#3)
- An 2024 — FILM-7B (#4)
- Levy 2024 (#5)
- Chroma "Context Rot" report (industrie, 2025)

→ Si tu ne peux pas mettre la question en fin, mets-la au début et **répète-la** à la fin (query-aware contextualization).

#### 4. Recency + Primacy bias agissent SIMULTANÉMENT

C'est le point subtil : les LLMs prêtent attention disproportionnellement à :
- Ce qui est **au tout début** du prompt → **primacy effect** (Wang 2023 EMNLP, paper #9)
- Ce qui est **proche du point de génération** → **recency bias** (Zhao 2021 ICML, paper #8)

Implication pratique : la structure idéale combine les deux :
- Mettre le **system prompt cadre** (rôle, règles globales) en TOUT DÉBUT → exploité par primacy
- Mettre la **question / instruction spécifique** EN FIN → exploité par recency
- Mettre le **document/contexte** ENTRE LES DEUX → là où il est mémorisé même si moins "saillant"

### 12.4 — Le pattern canonique selon la littérature

```
[1] System prompt cadre (rôle, règles globales)
       ← exploite le primacy bias

[2] Document / contexte / chunk long
       ← réutilisé via prefix-cache (vLLM, SGLang, llama.cpp --cache-reuse)
       ← position du milieu OK car non-saillante mais mémorisée

[3] Exemplars few-shot (si applicable)
       ← position pré-finale, contribue au contexte de génération

[4] Question / instruction spécifique
       ← exploite le recency bias
       ← +30% empirique selon Anthropic

[5] → la génération commence ici
```

### 12.5 — Application à notre pipeline

Le pipeline `meeting_minutes_pipeline.py` actuel fait l'inverse :

```
[1] System prompt (via _build_system_prompt)  ✓ correct
[2] User message : "Résume cet extrait... [règles] ... Extrait : {chunk}"
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^
                    instructions au DÉBUT du user msg     chunk à la fin
                    → recency bias récupère les instructions
                    MAIS prefix-cache cassé entre résumé/extraction
                    (chunk = même mais pas en début commun)
```

Refactor proposé :

```
[1] System prompt  (inchangé)
[2] User message : "Extrait : {chunk}\n\n---\n\n[règles] ... Résume cet extrait..."
                    ^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    chunk en début     instructions à la fin
                    → primacy bias mémorise le chunk
                    → recency bias récupère les instructions
                    → prefix-cache fire entre résumé/extraction du même chunk
```

**Le refactor est doublement soutenu** :
- Côté **précision** : papers Liu 2023 + Anthropic +30% + Zhao 2021 recency bias
- Côté **efficacité** : papers vLLM + SGLang + Hydragen + Prompt Cache + llama.cpp `--cache-reuse`

### 12.6 — Caveat important

Les papers #8 (Zhao 2021), #9 (Wang 2023), #10 (PINE 2025) montrent que les modèles **plus petits ou moins instruction-tuned** sont plus sensibles aux biais de position. Un modèle 3B-Q4 (Ministral, Qwen 1.5B) peut moins bien gérer "instructions à la fin" qu'un 70B-class.

→ **Validation empirique obligatoire sur ton modèle cible** avant de figer le refactor en prod. C'est exactement ce que le bench `_bench_prompt_order.py` mesure.

---

## Sources complètes

- [llama.cpp PR #9866 — server: reuse cached context chunks](https://github.com/ggml-org/llama.cpp/pull/9866)
- [llama.cpp Issue #5793 — original KV shift proposal](https://github.com/ggml-org/llama.cpp/issues/5793)
- [llama.cpp Issue #9390 — disable context shift](https://github.com/ggml-org/llama.cpp/issues/9390)
- [llama.cpp Issue #15082 — cache-reuse regression](https://github.com/ggml-org/llama.cpp/issues/15082)
- [llama.cpp Issue #21468 — Gemma SWA cache-reuse not supported](https://github.com/ggml-org/llama.cpp/issues/21468)
- [llama.cpp Issue #18497 — qwen3-next cache-reuse not effective](https://github.com/ggml-org/llama.cpp/issues/18497)
- [llama.cpp PR #16391 — host-memory prompt caching](https://github.com/ggml-org/llama.cpp/pull/16391)
- [llama.cpp Discussion #20574 — host-memory prompt caching tutorial](https://github.com/ggml-org/llama.cpp/discussions/20574)
- [llama.cpp Discussion #13606 — KV cache reuse tutorial](https://github.com/ggml-org/llama.cpp/discussions/13606)
- [tools/server/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [tools/server/server-context.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-context.cpp)
- [SGLang paper — RadixAttention (arXiv:2312.07104)](https://arxiv.org/abs/2312.07104)
- [vLLM paper — PagedAttention (arXiv:2309.06180)](https://arxiv.org/abs/2309.06180)
