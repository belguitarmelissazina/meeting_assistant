# Engineering Ideas — Meeting Assistant

Compilation des optims & features cutting-edge identifiées (recherche web 2025/2026).
Trié par **wow / heure de boulot**.

---

## ✅ Déjà en place (ne pas re-mesurer)

- llama.cpp `--parallel N` slots (chunk-level parallelism)
- KV cache quantization (`--cache-type-k/v`)
- `--batch-size 4096 --ubatch-size 1024`
- Prompt Lookup Decoding via `--draft-max 8 --draft-min 2 --lookup-cache-dynamic`
- `--cache-reuse 256` (prefix reuse across calls)
- `-ngl` GPU layer offload (configurable)
- ThreadPoolExecutor pour parallel chunks
- Live LLM worker pendant l'enregistrement
- Diarisation streaming + clustering online (NMESC-style)

---

# Partie A — Speed du LLM local (priorité haute)

Le LLM est le bottleneck. Les items ci-dessous compoundent — `v1+v2+v3+v4+v5` ≈ **×3 à ×5 end-to-end** sur ton hardware Windows CPU.

## 🥇 Tier 1 — gros gains, flags ou setup rapide

### #1 Host-memory prompt cache (`-cram -1`)
- **Quoi** : Feature Q4 2025 qui spille les préfixes calculés en RAM et les ré-injecte sur slot switch.
- **Gain** : Sur workload avec prompt partagé (system + transcript), **TTFT ÷ 5 à 15** sur les chunks suivants. Élimine ~95% du prompt-processing répété.
- **Effort** : 5 min. Flag `-cram -1` côté server + `cache_prompt:true` côté client HTTP.
- **Caveat** : Coût RAM ; broken sur quelques archi hybrides SWA (Gemma 4, Qwen3-Next) — pas concerné par Ministral.
- **Source** : [PR #16391](https://github.com/ggml-org/llama.cpp/pull/16391), [discussion #20574](https://github.com/ggml-org/llama.cpp/discussions/20574)

### #2 Pin sur P-cores + `--cpu-strict 1`
- **Quoi** : Sur CPU hybride (Intel 12th gen+, Ryzen avec CCD splits), l'OS éparpille les threads → throughput ÷ 2-3.
- **Gain** : **+30-60% TG** sur Win11 24H2.
- **Effort** : 5 min de tuning + tester N = nombre P-cores physiques.
- **Comment** : `--cpu-range 0-N-1 --cpu-strict 1 --threads N` + Power Profile "Best Performance".
- **Source** : [#572](https://github.com/ggml-org/llama.cpp/discussions/572), [#9996](https://github.com/ggml-org/llama.cpp/discussions/9996)

### #3 Exclusions Windows Defender
- **Quoi** : Defender scanne le mmap du `.gguf` à chaque page-fault (fichier de 2 Go → beaucoup de pages).
- **Gain** : **+10-30%** sur warm-up + élimination des stalls IO pendant context shifts.
- **Effort** : 30 sec dans Sécurité Windows. Ajouter le `.gguf` et `llama-server.exe`.
- **Caveat** : Trade-off AV standard.

### #4 Build llama.cpp à jour (Q4_K block-interleaving AVX2)
- **Quoi** : [PR #12332](https://github.com/ggml-org/llama.cpp/pull/12332) a ajouté des kernels block-interleaved pour Q4_K_M sur AVX2.
- **Gain** : **+20-40% PP** sur AVX2 sans AVX-512.
- **Effort** : Re-télécharger le dernier binaire Windows depuis [Releases](https://github.com/ggml-org/llama.cpp/releases).
- **Caveat** : Aucune.

### #5 Backend Vulkan sur iGPU
- **Quoi** : Un 3B Q4_K_M rentre intégralement en mémoire partagée iGPU. Marche sur Intel Xe/Arc, AMD 700+, Lunar Lake.
- **Gain** : **+25-50% TG, ×2 PP** vs CPU pur. AMD reporte +31% sur 1B, +60% avec VGM 16 GB.
- **Effort** : Télécharger binaire `llama-bin-win-vulkan-x64`.
- **Caveat** : KV-quant compat variable selon GPU ; driver récent requis.
- **Source** : [#10879](https://github.com/ggml-org/llama.cpp/discussions/10879)

### #6 Switch vers `ik_llama.cpp` (fork drop-in)
- **Quoi** : Fork d'ikawrakow (contributeur original des quants K/IQ) avec kernels GEMM/GEMV CPU réécrits.
- **Gain** : **+30-100% PP, +20-40% TG**. Stable à 8k+ contexte là où mainline dégrade.
- **Effort** : Re-build, même GGUF compatible.
- **Caveat** : Lag mainline sur archi récentes, quelques endpoints serveur diffèrent.
- **Source** : [github.com/ikawrakow/ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp), [comparison Jan 2025](https://github.com/ikawrakow/ik_llama.cpp/wiki/Jan-2025:-prompt-processing-performance-comparison)

### #7 Re-quantize Ministral avec imatrix calibré sur du français
- **Quoi** : `llama-imatrix` sur Wikipédia-fr + transcripts parlementaires + tes propres minutes → perplexité domaine ↓ 10-30%.
- **Gain** : Peux descendre à **IQ4_XS** (plus petit, +5-10% TG) sans perte qualité.
- **Effort** : ~30 min CPU + construire corpus français.
- **Source** : [#5006](https://github.com/ggml-org/llama.cpp/discussions/5006), [bartowski Ministral GGUF](https://huggingface.co/bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF)

### #8 Flash Attention (`--flash-attn on`)
- **Quoi** : Réécriture algorithmique de l'attention pour exploiter le cache CPU (online softmax + block-by-block). Strictement même output.
- **Gain** : **+10-25% TG**, contexte plus grand sans OOM, prérequis pour KV-quant safe sur certaines archis.
- **Effort** : Un flag.

### #9 Sortir le projet de OneDrive
- **Quoi** : OneDrive ajoute un filter driver sur chaque write/read.
- **Gain** : Variable, parfois ×2-5 sur I/O ; supprime les fsync stalls.
- **Effort** : `mv` vers `C:\dev\meeting_assistant`.
- **Caveat** : Perte du backup cloud des intermédiaires.

## 🥈 Tier 2 — gains solides, effort moyen

### #10 Slot save/restore par contexte de réunion
- **Quoi** : Endpoints `/slots/<id>/save` et `/slots/<id>/restore` de llama-server pour sérialiser le KV cache d'une meeting.
- **Gain** : TTFT **÷ 10** quand l'utilisateur rouvre une réunion pour éditer.
- **Effort** : Medium (small client wrapper).
- **Source** : [#20572](https://github.com/ggml-org/llama.cpp/discussions/20572)

### #11 Speculative draft piloté par grammaire
- **Quoi** : Sur les sections structurées (headings, bullets, action items JSON), générer les draft tokens via GBNF — quasi gratuits.
- **Gain** : **+30-60% TG** sur les chunks structurés, acceptance >90%.
- **Effort** : ½ jour pour écrire la GBNF.
- **Source** : [grammars/README.md](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)

### #12 LLMLingua-2 compression du transcript
- **Quoi** : Petit BERT multilingue (xlm-roberta) compresse le transcript ×2-4 avant LLM.
- **Gain** : End-to-end **×1.7-5.7** sur ton workload `system + transcript + instruction`.
- **Effort** : Medium (ajoute ONNX runtime + modèle ~150 Mo).
- **Caveat** : Perte sur anaphores françaises ; tuner ratio par chunk.
- **Source** : [LLMLingua](https://github.com/microsoft/LLMLingua), [NAACL 2025](https://aclanthology.org/2025.naacl-long.368.pdf)

### #13 TurboQuant pour le KV cache (TQ3/TQ4)
- **Quoi** : Compression Walsh-Hadamard + Lloyd-Max du KV. Paper ICLR 2026, implémenté pour llama.cpp.
- **Gain** : **×4.6-5.2 moins de mémoire KV**, <10% overhead. Peut arrêter de chunker le transcript → wallclock −15 à −30%.
- **Effort** : Medium, fork à pinner (pas upstream).
- **Source** : [discussion #20969](https://github.com/ggml-org/llama.cpp/discussions/20969), [TurboQuant repo](https://github.com/AmesianX/TurboQuant)

### #14 Static n-gram lookup cache pour PLD
- **Quoi** : `llama-lookup` sur corpus de tes anciennes minutes → cache statique.
- **Gain** : Acceptance PLD 10-20% → 30-40% sur boilerplate ("Action item :", "Décision :", etc.) → **+10-25% TG**.
- **Effort** : Medium.
- **Flag** : `--lookup-cache-static fr-minutes.bin`

### #15 Summarisation hiérarchique du transcript
- **Quoi** : Maintenir résumé glissant 100-200 tokens des segments anciens. Seul le récent passe verbatim.
- **Gain** : **×2-4 moins de tokens** par appel, end-to-end ~×2 speedup.
- **Effort** : Medium.
- **Caveat** : Perte détail long-range ; designer le template.
- **Source** : [Selective_Context](https://github.com/liyucheng09/Selective_Context)

## 🥉 Tier 3 — niche / hardware-spécifique

### #16 AMX (Intel Sapphire/Granite Rapids) ou AVX-512 VNNI (Zen 4/5, Tiger Lake+)
- **Gain** : ×4-8 sur INT8 GEMM vs AVX-512 pur. AMX rend Q8_0 ~aussi rapide que Q4.
- **Vérifier** : `Get-CimInstance Win32_Processor | Select Name` puis Intel ARK.
- **Source** : [Intel forum AMX llama.cpp](https://community.intel.com/t5/Intel-Xeon-Processor-and-Server/llama-cpp-How-to-enable-AMX-on-Windows-11-when-using-llama-cpp/m-p/1689824)

### #17 Windows large pages + MMCSS Pro Audio + NtSetTimerResolution
- **Gain** : +3-8% TG mais surtout réduction massive de variance latence tail.
- **Source** : [TimerResolution](https://github.com/valleyofdoom/TimerResolution)

### #18 `llamafile` / `tinyBLAS` (Justine Tunney)
- **Gain** : ×1.3-5 sur certains CPUs (surtout AMD Zen 4).
- **Caveat** : En retard sur archi récentes.
- **Source** : [justine.lol/matmul](https://justine.lol/matmul/)

### #19 OpenVINO EP sur NPU (Core Ultra / Snapdragon X / Ryzen AI)
- **Quoi** : Offload étapes secondaires (classification de chunks, NER) sur NPU pendant que CPU bosse sur LLM principal.
- **Gain** : ×2-4 throughput effectif pipeline multi-étapes.
- **Source** : [OpenVINO GenAI NPU](https://docs.openvino.ai/2025/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html)

### #20 Endpoint `/embedding` pour classification cheap
- **Quoi** : Décider "ce chunk = décision / action item / blabla" via embeddings + tiny logistic, pas un full LLM forward.
- **Gain** : ×50-200 moins cher par classification.
- **Effort** : Medium (besoin labelled dataset).

### #21 Eagle-3 speculative decoding
- **Quoi** : Tête drafter 1 couche distillée du target. [PR #18039](https://github.com/ggml-org/llama.cpp/discussions/15902), Q1 2026.
- **Gain** : ×2-2.5 TG en greedy.
- **Effort** : Large (entraîner la tête).
- **Caveat** : Pas encore mainline ; à watcher.

### #22 Per-head adaptive KV quant
- **Source** : [#21385](https://github.com/ggml-org/llama.cpp/issues/21385). Encore en flight. Lossless q4_0 KV sur modèles hybrides.

---

# Partie B — Speculative decoding : pourquoi Qwen + Ministral NE marche pas

- **Règle dure llama.cpp** : draft et target doivent partager **exactement le même tokenizer**.
- Ministral-3B : tokenizer Tekken (Mistral v3)
- Qwen : tokenizer BPE Qwen-spécifique
- → Incompatibles. Refuse de charger ou produit du gibberish.

**Problème** : pas de candidat 0.5B avec tokenizer Mistral récent (Mistral-7B est sur l'ancien tokenizer ; pas de Ministral-0.5B publié). Donc spec decoding draft-based = **bloqué pour Ministral** aujourd'hui.

**Bonne nouvelle** : ton PLD existant exploite la redondance prompt↔output. Pour des minutes (très redondantes avec le transcript), **PLD est souvent meilleur** que draft-based sur CPU 3B.

**Alternative future** : si tu envisages de changer de modèle principal, **Qwen2.5-3B target + Qwen2.5-0.5B draft** est le couple idéal (même tokenizer, ratio 6×).

---

# Partie C — Idées "wow" features (genius-level)

## 🏆 Le combo "ça me connaît" (~1 semaine)

### #F1 — Mémoire vocale persistante entre réunions
- **Quoi** : Galerie d'embeddings ResNet34 voxceleb par speaker nommé sur disque (JSON). À la nouvelle meeting, cosine match → "Alice — confidence 0.94" auto-rempli.
- **Pourquoi wow** : Aucun outil local ne fait ça. Tu arrives en 1:1 récurrent, l'app sait qui parle.
- **Effort** : ~1 jour. Tu as déjà les embeddings.
- **Lib** : [WeSpeaker](https://github.com/wenet-e2e/wespeaker), [3D-Speaker](https://github.com/modelscope/3D-Speaker) pour les thresholds AHC.
- **Caveat** : Drift sur mois → moyenne incrémentale dans le centroïde, cap taille galerie.

### #F2 — RAG local sur tout l'historique des meetings
- **Quoi** : Embed chaque ancien transcript (BGE-M3 ou multilingual-e5) dans SQLite-VSS. Chat : *"qu'est-ce qu'on a décidé sur le pricing au dernier trimestre ?"*
- **Pourquoi wow** : **Aucun outil local ne le fait offline en 2026**.
- **Effort** : ~2 jours.
- **Lib** : Patterns [obsidian-rag](https://github.com/badvision/obsidian-rag), [ObsidianRAG](https://github.com/Vasallo94/ObsidianRAG).

### #F12 — Clone de style perso via few-shot
- **Quoi** : Stocker `(LLM_a_généré, utilisateur_a_édité)`. Réinjecter 2-5 exemples à chaque génération → LLM imite le style sans fine-tune.
- **Pourquoi wow** : Personnalisation totale sans training.
- **Effort** : ~1 jour (par-dessus #F2).
- **Source** : [ACL 2025 findings](https://aclanthology.org/2025.findings-emnlp.532.pdf) — meeting minutes = domaine sweet spot pour style imitation.

## ⚡ Le combo "vitesse perçue" (~3-4 jours)

### #F10 — Résumé spéculatif pendant que l'utilisateur parle
- **Quoi** : Toutes les N sec, le live worker fait une génération "résumé jusqu'ici" jetable. Le KV cache reste chaud. À la fin, minutes affichées en <2s.
- **Pourquoi wow** : Démo spectaculaire. UI montre minutes **avant** que l'utilisateur clique stop.
- **Effort** : ~1-2 jours. Réutilise prefix caching.
- **Caveat** : Gaspille compute sur réunions de 3h → cap la cadence.

### #F11 — Auto-record déclenché par calendrier + templates
- **Quoi** : Parse `.ics` Outlook. Détecte activité micro pendant créneau réunion → auto-start, pré-remplit participants, Ministral classifie le titre pour choisir template (1:1 / standup / design review).
- **Pourquoi wow** : Tue le bug "j'ai oublié d'enregistrer". Templates spécialisés boostent qualité summary.
- **Effort** : ~2 jours incl. UX tray Windows.

## 🎯 Le combo "qualité structurelle" (~3-5 jours)

### #F5 — Action items typés via GBNF JSON Schema
- **Quoi** : Schéma `{owner, task, due_date, dependencies, confidence}` compilé en GBNF → LLM **forcé** d'émettre JSON valide.
- **Pourquoi wow** : Zéro échec parse, "owner = Alice" devient lien cliquable. Équivalent local des structured outputs OpenAI.
- **Effort** : ½ jour.
- **Bonus** : Coupler avec #F1 → owner contraint aux noms connus.

### #F6 — Boucle agentique Planner → Writer → Critic
- **Quoi** : 3 passes Ministral sur le même KV. Planner = outline, Writer = remplit, Critic = note la fidélité + flagge bullets hallucinés pour régen.
- **Pourquoi wow** : +10-20 pp précision action items via self-consistency. Coût ~1.3× single-pass avec prefix caching.
- **Effort** : ~2 jours.
- **Source** : [Datasciencedojo agentic LLMs 2025](https://datasciencedojo.com/blog/agentic-llm-in-2025/)

### #F9 — Redaction PII on-device via GLiNER
- **Quoi** : GLiNER-multilingual ONNX quantizé (~150 Mo) sur transcript avant LLM. Classes activables au runtime ("emails / IBAN / chiffres salaire / codename interne").
- **Pourquoi wow** : Open-vocab → l'user ajoute "internal codename" à la volée. **80% F1 sur 60 classes PII**.
- **Effort** : ~1 jour.
- **Source** : [Protecto NER comparison](https://www.protecto.ai/blog/best-ner-models-for-pii-identification/)

## 🔬 ML state-of-the-art (1-2 semaines, plus risqué)

### #F2bis — Diarisation conditionnée ASR (SC-SOT / DiCoW)
- **Quoi** : Tokens speaker injectés dans décodeur ASR → output sérialisé `[S1] hello [S2] hi`. Résout le problème #1 du pipeline diar : **overlapped speech**.
- **Pourquoi wow** : Pas besoin de retrain le zipformer ; tête légère style Sortformer en post-fusion.
- **Effort** : ~3-5 jours.
- **Source** : [SC-SOT arXiv:2506.12672](https://arxiv.org/abs/2506.12672), [DiCoW arXiv:2510.03723](https://arxiv.org/abs/2510.03723), [NVIDIA Sortformer](https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1)
- **Caveat** : Domain mismatch FR → fine-tune sur Common Voice + mixes simulés.

### #F4 — NPU offload (Snapdragon X / Lunar Lake) via ONNX Runtime QNN EP
- **Quoi** : Zipformer + ResNet34 sur Hexagon NPU → CPU libéré → peut tourner Ministral en FP16 au lieu de Q4.
- **Pourquoi wow** : **Personne ne fait NPU + streaming ASR français**. Argument marketing "optimisé Copilot+".
- **Effort** : ~2-4 jours incl. quant QNN.
- **Source** : [QNN EP docs](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html), [Snapdragon build guide](https://onnxruntime.ai/docs/genai/howto/build-models-for-snapdragon.html)
- **Caveat** : NPU op coverage gaps sur attention chunked.

## 🎛️ Bonus signal-processing

### #F3 — DeepFilterNet3 avec bypass adaptatif
- **Quoi** : DFN3-LL ONNX (10-20 ms latence) devant sherpa-onnx, **désactivé** quand SNR > seuil.
- **Pourquoi wow** : Le piège classique = denoisers "toujours on" dégradent WER en audio propre. Bypass adaptatif est la clé.
- **Effort** : ~1 jour.
- **Source** : [deepfilter-rt ONNX port](https://github.com/shimondoodkin/deepfilter-rt)

## 🛠️ Honorable mentions

- **Highlight reel audio 60s** des moments saillants ([WACV 2025](https://openaccess.thecvf.com/content/WACV2025/papers/Islam_Unsupervised_Video_Highlight_Detection_by_Learning_from_Audio_and_Visual_WACV_2025_paper.pdf))
- **Mermaid diagram auto** des dépendances décisions/actions ([MermaidSeqBench](https://arxiv.org/html/2511.14967v1))
- **Anonymisation vocale McAdams** pour partage de clips ([VoicePrivacy 2026](https://www.voiceprivacychallenge.org/))
- **LS-EEND streaming diarization** end-to-end ([arXiv:2410.06670](https://arxiv.org/html/2410.06670v1))
- **Quantize ResNet34 ONNX en INT8** (`onnxruntime.quantization.quantize_dynamic`) — ~30% speedup, −75% mémoire

---

# Roadmap suggérée

## Sprint 1 — Speed brut (1 semaine)
Mesurer chaque étape isolément dans `_bench_pipeline.py` :

```
v0_baseline    : actuel (LLM_FAST_FLAGS=1)
v1_cram        : + -cram -1 + cache_prompt:true client
v2_pcore_pin   : + --cpu-strict 1 + --cpu-range P-cores
v3_defender    : + exclusions Defender sur GGUF & exe
v4_build_new   : + dernier build llama.cpp (PR #12332)
v5_vulkan      : + build Vulkan iGPU (si dispo)
v6_ik_llama    : swap binaire vers ik_llama.cpp
v7_imatrix_fr  : re-quantize Ministral IQ4_XS avec imatrix français
```

Cumul attendu : **×3 à ×5 sur TTFT end-to-end**.

## Sprint 2 — Wow features fondations (1-2 semaines)
- #F1 mémoire vocale persistante
- #F2 RAG local historique
- #F5 GBNF JSON pour action items
- #F10 résumé spéculatif live

## Sprint 3 — Qualité + entreprise (1-2 semaines)
- #F6 Planner→Writer→Critic
- #F9 GLiNER PII redaction
- #F12 clone de style
- #F11 calendar trigger + templates

## Sprint 4 — Avancé / différenciant
- #F2bis SC-SOT diarisation conditionnée
- #F4 NPU offload Copilot+
- #F3 DeepFilterNet3 adaptatif

---

# Choses à NE PAS faire pour l'instant

- **CUDA backend** si pas de GPU NVIDIA dédié — Vulkan couvre déjà tout.
- **Q8_0 weights** au lieu de Q4_K_M — TG est bandwidth-bound, Q8 = ~×1.7 plus lent pour gain qualité minime sur 3B.
- **Speculative decoding draft-based** sur Ministral — pas de draft 0.5B compatible aujourd'hui ; et de toute façon souvent 0 gain ou régression sur CPU + target 3B.
- **Bitnet.cpp** — ne marche que pour modèles 1.58-bit BitNet natifs, pas Ministral.

---

# Sources clés à reprendre

## llama.cpp speed
- [Server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Speculative.md docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)
- [GBNF grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
- [Host-Memory Prompt Caching #20574](https://github.com/ggml-org/llama.cpp/discussions/20574)
- [Persistent KV per session #20572](https://github.com/ggml-org/llama.cpp/discussions/20572)
- [P-core pin #572](https://github.com/ggml-org/llama.cpp/discussions/572), [#9996](https://github.com/ggml-org/llama.cpp/discussions/9996)
- [Vulkan perf #10879](https://github.com/ggml-org/llama.cpp/discussions/10879)
- [Q4_K AVX2 block-interleave PR #12332](https://github.com/ggml-org/llama.cpp/pull/12332)
- [TurboQuant KV #20969](https://github.com/ggml-org/llama.cpp/discussions/20969)
- [ik_llama.cpp fork](https://github.com/ikawrakow/ik_llama.cpp)
- [tinyBLAS / Justine Tunney](https://justine.lol/matmul/)

## ML features
- [LLMLingua repo](https://github.com/microsoft/LLMLingua)
- [Selective Context](https://github.com/liyucheng09/Selective_Context)
- [SC-SOT diarization-conditioned ASR](https://arxiv.org/abs/2506.12672)
- [DiCoW](https://arxiv.org/abs/2510.03723)
- [LS-EEND streaming diarization](https://arxiv.org/html/2410.06670v1)
- [pyannote 3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) + [deepfilter-rt ONNX](https://github.com/shimondoodkin/deepfilter-rt)
- [Silero VAD](https://github.com/snakers4/silero-vad)
- [GLiNER PII](https://www.protecto.ai/blog/best-ner-models-for-pii-identification/)

## Hardware
- [QNN EP docs](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html)
- [OpenVINO EP](https://onnxruntime.ai/docs/execution-providers/OpenVINO-ExecutionProvider.html)
- [Windows ML 2025](https://blogs.windows.com/windowsdeveloper/2025/05/19/introducing-windows-ml-the-future-of-machine-learning-development-on-windows/)
- [Hexagon NPU driver Dec 2025](https://www.qualcomm.com/developer/blog/2025/12/hexagon-npu-driver-update-snapdragon-pcs)

## Style / agentic
- [LLM style imitation ACL 2025](https://aclanthology.org/2025.findings-emnlp.532.pdf)
- [Agentic LLMs 2025](https://datasciencedojo.com/blog/agentic-llm-in-2025/)

---

# Partie D — Idées RAM-frugales (vague 2)

Toutes triées sous **contrainte RAM stricte** (Ministral-3B Q4 mange déjà ~3 Go).
Plusieurs items en **RAM négative** (économisent de la RAM) — c'est l'objectif.

## 🥇 Les 3 "no-brainers" RAM-négatifs

### #N1 — DuoAttention (ICLR 2025)
- **Quoi** : Profile une seule fois Ministral-3B et étiquette chaque tête d'attention : "retrieval" (besoin de tout le KV) ou "streaming" (besoin que de sink+window).
- **RAM** : **NÉGATIVE** — libère 30-50% du KV cache (centaines de MB à 16k ctx)
- **Gain** : Prefill plus rapide, ctx effectif plus grand gratuitement
- **Effort** : Medium (calibration offline)
- **Source** : [github.com/mit-han-lab/duo-attention](https://github.com/mit-han-lab/duo-attention), [arXiv:2410.10819](https://arxiv.org/abs/2410.10819)

### #N4 — SAM-Decoding / SuffixDecoding (NeurIPS 2025 Spotlight)
- **Quoi** : Remplace ton PLD existant par un **suffix automaton** sur le transcript de la meeting en cours. Match O(1) du plus long suffixe identique, zéro modèle ajouté.
- **RAM** : ~5-10 MB (suffix automaton sur 100k tokens)
- **Gain** : **×1.8-4.5 speedup**, et **×1.3-3 au-dessus de PLD**
- **Effort** : Low (single C++ file, llama.cpp a déjà le scaffold speculative)
- **Source** : [suffix-decoding.github.io](https://suffix-decoding.github.io/), [SAM-Decoding repo](https://github.com/hyx1999/SAM-Decoding)

### #N9 — LayerSkip self-speculative decoding (Meta)
- **Quoi** : Utilise les **premières couches de Ministral lui-même** comme draft model. Pas de modèle séparé à charger.
- **RAM** : **0 MB ajoutés** (réutilise weights déjà en mémoire)
- **Gain** : **×1.34-2.16 speedup** sur summarization (ton workload exactement)
- **Effort** : Medium (variantes training-free dispo en 2025)
- **Source** : [Meta LayerSkip](https://ai.meta.com/research/publications/layerskip-enabling-early-exit-inference-and-self-speculative-decoding/)

➡️ Ces 3 seuls = **~×2.5 sur TG** sans ajouter de RAM. Combinés avec `-cram` + PLD existant : territoire **×8 end-to-end**.

## ⚡ Éviction adaptative du KV (réunions longues)

### #N2 — CAOTE / Ada-KV (2025)
- **Quoi** : Plus récent que SnapKV/H2O. Minimise l'erreur de l'**output** d'attention plutôt que l'importance des keys, budget par tête variable.
- **Gain** : **40-60% KV économisé**, +0.5-1 ppl mieux que SnapKV
- **Effort** : Medium (code de référence dispo, pas encore upstream llama.cpp)
- **Source** : [arXiv:2504.14051](https://www.arxiv.org/pdf/2504.14051v4), [arXiv:2407.11550](https://arxiv.org/pdf/2407.11550)

### #N3 — G-KV decoding-time eviction (Dec 2025)
- **Quoi** : **Spécifiquement tuné pour streaming** — i.e. ton live meeting où tu ne connais pas le prompt complet.
- **Gain** : **×3 KV reduction**, garde le recall long-context sur 90 min
- **Effort** : Medium-high
- **Source** : [arXiv:2512.00504](https://arxiv.org/pdf/2512.00504)

### #N5 — Cascade Inference (FlashInfer pattern)
- **Quoi** : Ton prompt système + speaker gallery + few-shots = ~2-3k tokens partagés entre TOUS les appels speculative summary. Cascade le garde dans un seul niveau KV partagé.
- **RAM** : Économise N copies du préfixe (~150 MB × parallel slots)
- **Gain** : **Jusqu'à ×31** sur shared-prefix decoding
- **Effort** : Medium (slot-aware routing dans llama-server)
- **Source** : [FlashInfer cascade](https://flashinfer.ai/2024/02/02/cascade-inference.html)

## 💾 RAG vraiment frugal (~30 MB pour archive multi-année)

### #N6 — USearch mmap + int8 Matryoshka
- **Quoi** : Matryoshka-aware embedding (entraîné pour 256-dim au lieu de 384/768), stocké en **int8 sur disque via USearch mmap**.
- **RAM** : **<30 MB résident quelle que soit la taille de l'archive**
- **Gain** : ×8-32 shrink stockage, <1% drop recall vs fp32
- **Effort** : Low (USearch = single-header lib ; MRL distillation pour convertir MiniLM)
- **Source** : [HF embedding quantization](https://huggingface.co/blog/embedding-quantization), [Voyage 2025](https://blog.voyageai.com/2025/01/07/voyage-3-large/)

### #N7 — Nomic-Embed-v2 MoE (multilingue)
- **Quoi** : 305M params actifs, GGUF Q4, **100 langues**, Matryoshka natif. Drop-in si tu veux multilingue.
- **RAM** : ~200-250 MB (vs MiniLM 90 MB) — seulement worth it pour multilingue
- **Source** : [HF nomic-embed-v2-moe](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF), [arXiv:2502.07972](https://arxiv.org/abs/2502.07972)

### #N8 — LM-DiskANN pour archives très larges
- **Quoi** : Quand tu dépasses 1M de chunks (~3 ans de réunions), HNSW commence à coûter. LM-DiskANN garde seulement les entry-points en RAM.
- **RAM** : **5-15 MB résident** à l'échelle milliard de vecteurs
- **Gain** : -90% RAM vs HNSW in-memory, <10ms latence
- **Effort** : Medium
- **Source** : [LM-DiskANN paper](https://cse.unl.edu/~yu/homepage/publications/paper/2023.LM-DiskANN-Low%20Memory%20Footprint%20in%20Disk-Native%20Dynamic%20Graph-Based%20ANN%20Indexing.pdf)

## ⏱️ Latency tricks zéro-RAM

### #N10 — CALM early-exit confidence-based (Google)
- **Quoi** : Sur les tokens boilerplate ("Action items:", "—", "**Décisions** :"), softmax confidence ~1.0 dès la couche 12/24 → sortir plus tôt.
- **RAM** : **0 MB ajoutés**
- **Gain** : **×3 latency** sur summarization
- **Effort** : Low (exit on max-prob threshold)
- **Source** : [Google CALM](https://research.google/blog/accelerating-text-generation-with-confident-adaptive-language-modeling-calm/)

### #N15 — PRESERVE calendar-driven prefetch
- **Quoi** : Quand Outlook montre une réunion dans T-5min, faire `PrefetchVirtualMemory()` sur le `.gguf` → page cache OS chaud.
- **RAM** : 0 MB résident change (juste page cache OS)
- **Gain** : TTFT premier token de la journée **3-5s → ~200ms**
- **Effort** : Low (un appel Windows depuis le tray daemon)
- **Source** : [arXiv:2501.08192](https://arxiv.org/abs/2501.08192)

## ✨ WOW features ultra-tiny

### #N12 — Chromaprint duplicate meeting detector
- **Quoi** : Lib C de **<2 MB**, sub-millisecond. Détecte auto : re-recordings, redial-ins, "ce client a déjà appelé hier ?"
- **RAM** : <2 MB
- **Gain** : Pure WOW, one-shot identifie repeat callers
- **Effort** : Very low
- **Source** : [chromaprint](https://github.com/acoustid/chromaprint), [acoustid](https://acoustid.org/chromaprint)

### #N13 — Lighthouse audio moment retrieval (ICASSP 2025)
- **Quoi** : Requête en langage naturel sur la piste audio : *"trouve le moment où le client a ri quand on a parlé de prix"* → timecode.
- **Pourquoi wow** : Signe la différence avec tout meeting tool du marché. "Audio time machine par texte".
- **RAM** : CNN ~50 MB
- **Effort** : Medium
- **Source** : [Lighthouse](https://github.com/line/lighthouse)

### #N14 — FunnyNet auto-highlight reel
- **Quoi** : CNN audio détecte rires/applaudissements/emphasis → bookmarks candidats injectés dans le summary.
- **Pourquoi wow** : "Highlight reel" automatique d'une réunion d'1h. Démo-friendly.
- **RAM** : ~30 MB
- **Effort** : Medium
- **Source** : [arXiv:2401.04210](https://arxiv.org/html/2401.04210v1)

### #N11 — NVIDIA Streaming Sortformer (2025)
- **Quoi** : Drop-in replacement pour stack ResNet34 si ça drift en bruyant. Sortie native pour talk-time ratios.
- **Bonus** : Dashboard "Alice 45%, Bob 22%, ..." gratuit
- **RAM** : ~150 MB
- **Effort** : Medium
- **Source** : [NVIDIA Streaming Sortformer](https://developer.nvidia.com/blog/identify-speakers-in-meetings-calls-and-voice-apps-in-real-time-with-nvidia-streaming-sortformer/)

## ❌ À ne *pas* faire (vague 2)

- **Deja Vu contextual sparsity** — nécessite retrain FFN routers, gains à 70B+ seulement
- **PowerInfer-2 complet** — overkill à 3B (c'est conçu pour 7B-47B)
- **Online LoRA nightly** sur les édits user — feasible mais ajoute stack training ; attendre ≥500 paires/mois

## Roadmap mise à jour (vague 2 intégrée)

### Sprint 1 — Speed pur (~1 semaine)
1. `-cram -1` (#1 vague 1)
2. P-core pin (#2)
3. Defender excl. (#3)
4. Build llama.cpp à jour (#4)
5. **SAM-Decoding** (#N4) — replace PLD
6. **LayerSkip self-speculative** (#N9)
7. **CALM early-exit** (#N10)

### Sprint 2 — KV thrift (~1 semaine)
1. **DuoAttention calibration** (#N1) — libère RAM
2. **Cascade Inference** (#N5) — shared prefix optim
3. **Ada-KV / CAOTE** (#N2) si meetings >2h fréquentes

### Sprint 3 — Features wow (~2 semaines)
1. Speaker gallery persistante (#F1)
2. RAG local **avec USearch mmap + int8 Matryoshka** (#F2 + #N6)
3. GBNF action items (#F5)
4. **Chromaprint duplicate detector** (#N12) — feature signature
5. **PRESERVE calendar prefetch** (#N15)
6. Speculative summary live (#F10)

### Sprint 4 — Différenciation
1. **Lighthouse audio retrieval** (#N13) — feature unique
2. **FunnyNet highlight reel** (#N14)
3. Planner→Writer→Critic (#F6)
4. GLiNER PII (#F9)

---

# Partie E — Features produit (extension au-delà du report)

Cadrées contre la compétition cloud (Granola, Otter, Fathom, Sembly, Read.ai, Fireflies, tl;dv) — identifier où l'offline gagne.

## 🎯 Cluster A — Briefing pré-réunion

### #E-A1. Deck-aware briefing pack
Drop un PPTX/PDF attaché à l'invite Outlook → l'agent parse les slides (`python-pptx`/`pdfplumber`), embed dans le RAG, produit un brief 1-page "ce que tu dois savoir avant cette réunion". **Granola a levé $125M en partie pour ça** — en cloud. L'offline est ton coin.
- Libs : `python-pptx`, `pdfplumber`, GLiNER, RAG existant
- Tricky : ajouter OCR (`tesseract` ou `paddleocr`) pour slides image
- Source : [Granola enterprise context server](https://www.granola.ai/chat)

### #E-A2. Carte "promesses ouvertes avec cette personne"
Avant chaque invite, surface chaque action item antérieur où un attendee chevauche, avec statut (open/done/stale >14j). Killer pour managers en 1:1 et AE en sync client.
- Source : [Claryti daily brief](https://www.claryti.ai/blog/what-is-meeting-intelligence)

### #E-A3. Talking points extractor depuis email threads
Lit les 30 derniers jours d'emails Outlook (via `pywin32` MAPI) avec les attendees → 3-5 talking points seeded dans l'agenda. Pour BD, partenariats, recruiters.

### #E-A4. Auto-agenda diff
Pour les invites récurrentes, diff les action items du dernier transcript vs aujourd'hui → agenda draft. PMs standups, EMs staff meetings.
- Source : [tl;dv coaching](https://tldv.io/features/coaching/)

## 🎤 Cluster B — Live assist "whisper in ear"

### #E-B5. Live context cards on speaker mention
Quand diar détecte qu'Alice parle → overlay carte transparente 200px : ses 3 derniers commitments, son rôle inféré, son dernier point de désaccord. **Aucun produit ne fait ça offline.**
- Libs : WinUI3 transparent always-on-top, Ministral sur speaker-change events

### #E-B6. Q&A local knowledge base mid-call
`Ctrl+Shift+Q` ouvre boîte → RAG contre Obsidian vault / `\\fileserver\policies\*` → réponse 1-phrase + source. **Équivalent offline de Glean SaaS.**
- Libs : RAG existant + file-watcher (`watchdog`)

### #E-B7. Nudge anti-monologue temps réel
Toast quand un speaker tient le floor >N secondes. Read.ai le fait en post-meeting — toi en live = novel.
- Source : [Read.ai coach](https://www.read.ai/articles/ai-meeting-coach)

### #E-B8. Mode interpréteur live FR↔EN local
sherpa → Ministral translate → Piper TTS opposite device, <2s latency, routé dans Teams via virtual audio cable. **Wordly/Palabra à $14+/h cloud, toi gratuit offline.**
- Caveat : Tag loopback device pour éviter echo
- Source : [Wordly](https://www.wordly.ai/)

## 🧠 Cluster C — Intelligence cross-meeting + agentic

### #E-C9. Commitment ledger avec stale-promise nudges
SQLite `owner/promise/due/status/source_meeting`. Tâche Windows quotidienne te ping pour items >14j sans update. **Sembly l'a en cloud, toi offline = wedge.**
- Source : [Sembly](https://www.sembly.ai/)

### #E-C10. Saved searches "tout ce que Alice a promis ce trimestre"
Requêtes pré-construites speaker × time × commitment-type. Pour managers prep perf reviews, lawyers prep depositions.
- Source : [Fireflies AskFred](https://fireflies.ai/blog/fireflies-launches-askfred-chatgpt-for-meetings/)

### #E-C11. Decision-change detection
Embedding similarity : décision contredit une past décision → flag *"Le 03/12 tu avais décidé X ; aujourd'hui not-X"*. **Genuinement rare même en cloud.**

### #E-C12. Auto-draft follow-up email + CRM patch (approval-gated)
Après "Stop recording" : draft email dans Outlook Drafts + payload Hubspot/Salesforce field-patch en attente d'approval 1-clic. **Feature signature Fathom 2025 cloud-only.**
- Source : [Fathom integrations](https://www.fathom.ai/integrations)

## 🎨 Cluster D — Outputs créatifs & coaching

### #E-C13. Recipe / lens marketplace 🌟
Chaque lens = `prompt.txt` + `grammar.gbnf` optionnel + hook TS. 8 lenses built-in : Coach Me, Write PRD, LinkedIn post, Exec 1-pager, Tweet thread, Negotiation review, Therapy reframe, Blog draft. **Killer move Granola fin 2025 — 80% prompt files, 20% code. ROI le plus élevé.**
- Source : [Granola Recipes](https://www.upstartsmedia.com/p/granola-launches-recipes)

### #E-C14. Negotiation coach mode
Toast quand l'utilisateur concède un chiffre dans les N sec d'un anchor counterparty. Post-meeting : chaque concession/anchor/silence >4s après prix. **Personne ne fait ça.**

### #E-C15. Auto-PPTX généré
"Turn this meeting into a 5-slide exec brief" → `python-pptx` écrit avec template uploadé. Consultants, internal-comms.

### #E-C16. Whiteboard photo OCR merge
Drop photo phone dans dossier watched → OCR (paddleocr ou Windows OCR API) → thread dans transcript au bon timestamp. **Zoom AI Companion vient de shipper ça Dec 2025.**

### #E-C17. Audio insight diary
Fin de journée : agent splice 30-60s de tes monologues à travers toutes meetings ("today I committed to", "what surprised me") en un MP3 avec bumpers TTS. **Nouveau pour meeting tools.**

## 🏢 Cluster E — Entreprise & plumbing

### #E-C18. Flux capture de consentement
TTS announcement au début du record + timestamps explicit verbal consent. Stocké comme clip audio crypto-signé séparé. **GDPR-grade**, lawyers/HR/regulated.

### #E-C19. Profiles redaction NDA-aware
Profil par contact ("Acme Corp sous NDA → redact $ figures + roadmap terms à l'export"). Au moment de partager Slack/Notion, redactor tourne d'abord.

### #E-C20. Auto-tracker billable hours
Tag meeting → `project_code`. Roll-up duration × rate → invoice CSV/PDF hebdo. Lawyers, consultants, freelancers. **Wedge Sembly "professional services" offline.**

### #E-C21. Bridge Obsidian/Logseq avec backlinks
Chaque minute écrite dans le vault avec `[[Person Name]]` et `[[Project]]` auto-résolus. Speakers = first-class nodes. **Énorme cohorte underserved.**

### #E-C22. Plugin SDK avec event bus 🌟
WebSocket localhost émet `transcript.partial`, `speaker.changed`, `action_item.detected`, `meeting.ended`. Users écrivent JS/Python subscribers. CLI scaffolder. **Moat long terme** — Granola/Otter/Fathom ont APIs fermées cloud-auth.

## 🚀 Top 5 (Partie E) à shipper en premier
1. **#E-A1** deck-aware brief
2. **#E-A2** open-promises card
3. **#E-C13** Recipe marketplace
4. **#E-C18** consent capture
5. **#E-C22** plugin SDK

## 🎬 Top 3 "wow demos" pour launch video
1. **#E-B5** live speaker context cards
2. **#E-B8** interpréteur live FR↔EN
3. **#E-C14** negotiation coach

Chacun = chose qu'aucun concurrent cloud ne peut matcher offline, démo en <30 sec.

---

# Partie F — Features verticales & multimodales (vague 3)

## 🩺 Cluster A — Verticals professionnels

### #F-A1. SOAP / K-SOAP Doctor Mode
Auto-remplit Subjective/Objective/Assessment/Plan depuis session médecin-patient. **Penn Medicine −30% "pajama time"** avec AI scribes. GP solo, télémédecine.
- Libs : Ministral + GBNF SOAP grammar, `en_core_med7_lg` pour NER médical
- Source : [jsl_meds_text2soap_v1](https://nlp.johnsnowlabs.com/2025/04/09/jsl_meds_text2soap_v1_en.html), [CliniKnote K-SOAP](https://arxiv.org/abs/2408.14568)

### #F-A2. Rubric-Aware Recruiter Mode
Live "belief-trace" : chaque réponse candidat met à jour score 0-5 par compétence avec audit log. **Hiring défendable bias-auditable.**
- Source : [Rubric-Aware Interview arXiv:2603.01775](https://arxiv.org/html/2603.01775)

### #F-A3. Robert's Rules Board-Secretary Mode
Détecte motions, seconds, amendments, votes → minutes parlementaires conformes. Nonprofit boards, HOAs, conseils étudiants.
- Effort : small (FSM sur tours diarisés)

### #F-A4. Journalist Quote-Attribution Mode
Pull-quotes par speaker avec timestamp + flag accuracy verbatim. Auto-byline draft. Reporters, podcasters.

## 📺 Cluster B — Multimodal écran-synchronisé

### #F-B1. Screen-Synced Transcript Rewind 🌟
Capture écran 1-2 fps indexée par timecode + OCR. Click phrase → vois ce qui était à l'écran. **"Cette barre rouge" résolu pour toujours.**
- Libs : `mss`, `paddleocr`, `imagehash`
- Privacy : allowlist windows à exclure
- Source : [MaViLS arXiv:2409.16765](https://arxiv.org/html/2409.16765)

### #F-B2. Slide-Change Chapter Auto-Boundaries
Transitions slides = chapitres naturels transcript + TOC. **TOC sans tagger.** Lecturers, sales engineers.
- Source : [SliTraNet](https://arxiv.org/pdf/2202.03540), [Change3D CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhu_Change3D_Revisiting_Change_Detection_and_Captioning_from_A_Video_Modeling_CVPR_2025_paper.pdf)

### #F-B3. Audio-Native Timestamp Q&A
Voice ou text : *"quand a-t-on parlé du budget Q4 ?"* → timestamps rangés + contexte 10s. Recherche par émotion / event-type.
- Libs : `bge-small` ou `multilingual-e5-small` + FAISS-on-disk
- Source : [DCASE 2025 Audio QA](https://dcase.community/challenge2025/task-audio-question-answering)

## 👥 Cluster C — Group dynamics & prosodie

### #F-C1. Interruption / Dominance Network Graph
Heatmap qui-interrompt-qui + score dominance 3-axes. **Surface patterns invisibles live.** DEI auditors, retros team.
- Source : [Cairn dominance](https://shs.cairn.info/revue-langage-et-societe-2020-1-page-169?lang=en)

### #F-C2. Prosody-Based Stress / Strain Detector 🌟
Score stress rolling par speaker (pitch jitter, vitesse, micro-tremor) → carte décompression post-meeting. **Dashboard biomarqueurs vocaux offline.**
- Lib : `wav2vec2-lg-xlsr-en-speech-emotion-recognition` ONNX
- Caveat : Brand "wellness signal", PAS diagnostic
- Source : [JMIR Mental Health 2025](https://mental.jmir.org/2025/1/e74260)

### #F-C3. Silent-Attendee Nudge
Alert background : *"Bob n'a pas parlé depuis 22 min"* — live + post-meeting. Scrum masters, facilitateurs inclusifs.

### #F-C4. Code-Switch FR↔EN Detector
Tag inline switch mid-utterance. **Préserve les deux langues** là où l'ASR casse. Teams FR-canadien, EU bilingue.
- Source : [SwitchLingua arXiv:2506.00087](https://arxiv.org/html/2506.00087v1)

## ⏪ Cluster D — Time-shifted listening

### #F-D1. "J'ai joint en retard, qu'est-ce que j'ai raté ?"
Hotkey → briefing 60s personnalisé par rôle. **Zéro silence awkward.**

### #F-D2. Rewind hotkey sans perdre contexte
F9 = replay 30 dernières sec, live transcript continue dans side pane. **TiVo pour meetings.**
- Effort : small (ring buffer WASAPI déjà là)

### #F-D3. Per-Recipient Briefing Generator
Même meeting → 4 résumés : engineering / exec sponsor / sales / intern absent. **Remplace emails distribution craftés main.** Chief-of-staff.

### #F-D4. 15-Second Meeting Trailer
Teaser audio auto-édité (3 best quotes + decision headline). **Meeting marketing.**

## 📈 Cluster E — Cross-meeting intelligence & anniversaires

### #F-E1. Topic-Evolution River Plot
Streamgraph topics récurrents qui montent/descendent sur semaines + sentiment lane. **Narrative longitudinal passif.**
- Libs : BERTopic + d3 streamgraph
- Source : [TopicFlow](https://alisonmsmith.github.io/assets/refs/springer-topicflow.pdf)

### #F-E2. Anniversary Long-Tail Promise Watcher
Daemon : *"Tu as dit que tu revisiterais le pricing dans 6 mois — c'est aujourd'hui"*. **Accountability sans effort.**

### #F-E3. Reference-Heatmap (Highest-Impact 60 Seconds)
Track quels segments past meetings se font cited dans meetings suivants → auto-surface "greatest hits" du quarter. Execs prépa all-hands.

### #F-E4. Meeting Effectiveness Score & Cancel-Suggestion
Score par meeting : decision-density, action-density, agenda-adherence. **Flagge meetings récurrents chroniquement bas → suggestion cancel.** COOs, ops leads.
- Source : [Sally.io KPIs](https://www.sally.io/blog/meeting-kpis-most-important-metrics)

## 🏛️ Cluster F — Legal-grade & portable cross-LLM

### #F-F1. Bates-Numbered Chain-of-Custody Export 🌟
Chaque page/segment a Bates ID séquentiel + SHA-256 + manifest immutable avec custody events. **Packaging admissible en cour.** In-house counsel, HR investigators, compliance.
- Libs : JSON manifest + Ed25519 dans Windows DPAPI vault
- Source : [California Rule 2.1040](https://courts.ca.gov/cms/rules/index/two/rule2_1040), [CoC SoK 2024](https://sefcom.asu.edu/publications/CoC-SoK-tps2024.pdf)

### #F-F2. Offline-Wikipedia Fact-Check (Kiwix ZIM) 🌟
Speaker affirme un fait → check side-panel contre ZIM cached → badge green/yellow/red. **Hallucination-resistant grounding, fully offline.**
- Libs : `llm-tools-kiwix`, ZIM FR (~100 Go)
- Source : [zim-llm](https://github.com/rouralberto/zim-llm), [Volo](https://github.com/AdyTech99/volo)

### #F-F3. Portable AI-to-AI Handoff Capsule
Export meeting + ledger comme prompt capsule à coller dans Claude/GPT/Mistral. **Survit au vendor lock-in.**
- Source : [openscilab/memor](https://github.com/openscilab/memor), [OpenMemory MCP](https://mem0.ai/blog/how-to-make-your-clients-more-context-aware-with-openmemory-mcp)

### #F-F4. Multi-Recorder Audio Merge (Higher SNR)
2 recordings indépendants → cross-correlation align + best-channel-per-turn → transcript unifié. **Sauve des recordings inutilisables.**
- Libs : `audalign`, `noisereduce`

## 🎁 Bonus quick-fires (Partie F)

- **#F-G1.** "Always-on" voice-memo via wake word "Hey Notes" → auto-classify projet. [openWakeWord](https://github.com/dscripka/openWakeWord), [Picovoice Porcupine](https://picovoice.ai/products/voice/wake-word/)
- **#F-G2.** Auto-quiz generator (5 MCQs Ebbinghaus 24h après)
- **#F-G3.** Decision-DAG visualization dépendances cross-meetings

## 🏆 Top 5 (Partie F) si tu dois shipper just 5

**#F-B1** screen-synced rewind · **#F-C2** prosody stress · **#F-A1** SOAP mode (ouvre vertical médical) · **#F-F1** Bates / chain-of-custody · **#F-F2** offline Wikipedia fact-check

Chacun : différenciant, défendable offline, bâti sur stacks 2025/2026 réelles.
