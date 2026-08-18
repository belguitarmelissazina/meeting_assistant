"""Copie (sans supprimer les originaux) tous les comptes rendus de la REUNION RTE
(Jerome Picault / Maya Sahraoui) dans un dossier dedie, renommes par
technique / architecture / modele.

But : Melissa met ensuite ce dossier sur SharePoint et peut referencer chaque CR
depuis le rapport (docs/Rapport_Partie_LLM.docx) grace au nom de fichier.

IMPORTANT :
- Lecture seule des sources ; ecriture UNIQUEMENT dans docs/comptes_rendus_references/.
- Le run Llama-3.2-1B et le batch results/meeting_minutes/transcript.normalized/
  portent sur une AUTRE reunion (alex / web scraping) -> volontairement EXCLUS.
- Idempotent : reexecutable sans effet de bord (ecrase les copies du dossier dedie).

Usage : python docs/collect_comptes_rendus.py
"""

from __future__ import annotations
import shutil
from pathlib import Path

DOCS = Path(__file__).resolve().parent
DIAR = DOCS.parent                       # diarisation-final
BENCH = DIAR.parent / "benchmark_llm"    # benchmark_llm (voisin)
DEST = DOCS / "comptes_rendus_references"

# (chemin source relatif a sa racine, racine, nom de destination)
# Racine "D" = diarisation-final, "B" = benchmark_llm
MAPPING: list[tuple[str, str, str]] = [
    # --- Architecture EXTRACTION (V4 : resume+extraction JSON + assemblage deterministe) ---
    ("results/meeting_minutes_v4/dicte_audio_3.normalized/qwen2.5/seq/compte_rendu.md", "B",
     "archi_extraction_v4_qwen2.5-3b.md"),
    ("results/meeting_minutes_v4/dicte_audio_3.normalized/ministral/seq/compte_rendu.md", "B",
     "archi_extraction_v4_ministral3b.md"),

    # --- CHUNKING V2 : clustering HDBSCAN (mesure sur transcript1) ---
    ("results/meeting_minutes_v2/qwen2.5/compte_rendu.md", "B", "chunking_v2_hdbscan_qwen2.5-3b.md"),
    ("results/meeting_minutes_v2/ministral/compte_rendu.md", "B", "chunking_v2_hdbscan_ministral3b.md"),
    ("results/meeting_minutes_v2/qwen3/compte_rendu.md", "B", "chunking_v2_hdbscan_qwen3-4b.md"),
    ("results/meeting_minutes_v2/smollm3/compte_rendu.md", "B", "chunking_v2_hdbscan_smollm3.md"),

    # --- CHUNKING V3 : detection de frontieres semantiques (boundary, retenu) ---
    ("results/meeting_minutes_v3/qwen2.5/compte_rendu.md", "B", "chunking_v3_boundary_qwen2.5-3b.md"),
    ("results/meeting_minutes_v3/ministral/compte_rendu.md", "B", "chunking_v3_boundary_ministral3b.md"),
    ("results/meeting_minutes_v3/ministral/compte_rendu0.md", "B", "chunking_v3_boundary_ministral3b_run0.md"),
    ("results/meeting_minutes_v3/qwen3/compte_rendu.md", "B", "chunking_v3_boundary_qwen3-4b.md"),
    ("results/meeting_minutes_v3/smollm3/compte_rendu.md", "B", "chunking_v3_boundary_smollm3.md"),
    ("results/meeting_minutes_v3/transcript_formatted/ministral/compte_rendu.md", "B",
     "chunking_v3_boundary_ministral3b_transcript-formatted.md"),
    ("results/meeting_minutes_v3/dicte_audio_3.normalized/ministral/compte_rendu.md", "B",
     "chunking_v3_boundary_ministral3b_dicte3.md"),

    # --- Reference qualitative ---
    ("compte_rendu_reference.md", "B", "reference_v3-boundary_qwen2.5-3b.md"),

    # --- Divers benchmark_llm (racine) ---
    ("compte_rendu.md", "B", "divers_benchmark-root.md"),
    ("compte_rendu_benchmark.md", "B", "divers_benchmark-recap.md"),
    ("compte_rendu_mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.md", "B",
     "divers_ministral3b_benchmark-root.md"),

    # --- OPTIMISATIONS (diarisation-final, Ministral 3B, dicte_audio_3) ---
    ("_bench_plan_attack_results/legacy/run0/compte_rendu.md", "D",
     "opt_plan-action_legacy_ministral3b.md"),
    ("_bench_plan_attack_results/perchunk/run0/compte_rendu.md", "D",
     "opt_plan-action_perchunk_ministral3b.md"),
    ("_bench_prod_mainline_fa/compte_rendu.md", "D", "opt_flash-attention_on_ministral3b.md"),
    ("_bench_prod_mainline_fa/compte_rendu_v1.md", "D", "opt_flash-attention_on_ministral3b_bis.md"),
    ("_bench_prod_mainline_no_fa/compte_rendu.md", "D", "opt_flash-attention_off_ministral3b.md"),
    ("_bench_prod_ik_llama_v5/compte_rendu.md", "D", "opt_ik-llama_v5_ministral3b.md"),
    ("_bench_results/old/run0/compte_rendu.md", "D", "archi_extraction_ancien-run_ministral3b.md"),

    # --- ARCHITECTURE AGENTIQUE (orchestrateur + workers, dicte_audio_3) ---
    ("_bench_orchestrator_v1/compte_rendu_v1.md", "D", "agentique_v1_ministral3b.md"),
    ("_bench_orchestrator_v2/compte_rendu_v2.md", "D", "agentique_v2_ministral3b.md"),
    ("_bench_orchestrator_v3/compte_rendu_v3.md", "D", "agentique_v3_ministral3b.md"),
    ("_bench_orchestrator_v4/compte_rendu_v4.md", "D", "agentique_v4_ministral3b.md"),
    ("_bench_orchestrator_v6_qwen7b/compte_rendu_v4.md", "D", "agentique_v6_qwen7b.md"),
    ("_bench_orchestrator_v7_3b/compte_rendu_v4.md", "D", "agentique_v7_ministral3b.md"),
    ("_bench_orchestrator_v8_3b/compte_rendu_v4.md", "D", "agentique_v8_ministral3b.md"),
    ("_bench_orchestrator_v9_hybride/compte_rendu_v9.md", "D", "agentique_v9_hybride_7b3b.md"),
    ("_bench_orchestrator_v10_qwen3b_nodiar/compte_rendu_v4.md", "D",
     "agentique_v10_qwen3b_sans-diarisation.md"),
]

# Reunion AUTRE (alex / web scraping) -> on NE copie PAS (juste documente).
EXCLUS = [
    "results/meeting_minutes/transcript.normalized/*  (reunion alex, petits modeles + Llama-3.2-1B)",
]


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    roots = {"D": DIAR, "B": BENCH}
    copies, manquants = [], []

    for rel, root_key, dest_name in MAPPING:
        src = roots[root_key] / rel
        dst = DEST / dest_name
        if src.exists():
            shutil.copy2(src, dst)
            copies.append((dest_name, str(src)))
        else:
            manquants.append((dest_name, str(src)))

    print(f"Dossier dedie : {DEST}\n")
    print(f"== {len(copies)} comptes rendus copies (originaux intacts) ==")
    for name, src in copies:
        print(f"  {name:55s} <- {src}")

    if manquants:
        print(f"\n== {len(manquants)} sources introuvables (ignorees) ==")
        for name, src in manquants:
            print(f"  {name:55s} (absent) {src}")

    print("\n== Volontairement EXCLUS (autre reunion) ==")
    for e in EXCLUS:
        print(f"  - {e}")


if __name__ == "__main__":
    main()
