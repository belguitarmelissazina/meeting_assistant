"""
Pipeline complet : Enregistrement -> Diarisation + Transcription -> Compte rendu

Appuie sur Entree pour demarrer l'enregistrement (micro + loopback systeme),
Ctrl+C pour l'arreter. Ensuite, la diarisation, la transcription et la
generation du compte rendu de reunion sont lancees automatiquement.

Usage:
    python record_and_process.py
    python record_and_process.py --num-speakers 3
    python record_and_process.py --output-dir ./ma_reunion
    python record_and_process.py --skip-minutes        # diarisation seulement
    python record_and_process.py --audio existing.wav  # traite un fichier existant
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_capture import AudioRecorder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("record_and_process")

ROOT = Path(__file__).resolve().parent


def record_audio(output_dir: Path) -> Path:
    """Enregistre l'audio jusqu'a Ctrl+C. Retourne le chemin du WAV."""
    rec = AudioRecorder()
    print()
    print("=" * 60)
    print("  ENREGISTREMENT")
    print("=" * 60)
    input("  Appuie sur Entree pour demarrer (Ctrl+C pour arreter)... ")
    rec.start()
    print(f"  Enregistrement en cours... (micro{' + loopback' if True else ''})")
    try:
        while rec.is_recording:
            time.sleep(0.5)
            dur = rec.duration
            lvl = rec.audio_level
            lb = rec.loopback_level if rec.has_loopback else 0.0
            bar_mic = "#" * int(lvl * 20)
            bar_lb = "#" * int(lb * 20)
            sys.stdout.write(
                f"\r  t={dur:6.1f}s  mic[{bar_mic:<20}] lb[{bar_lb:<20}] "
            )
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n  Arret demande...")

    tmp_wav = rec.stop()
    if not tmp_wav:
        raise RuntimeError("Aucune donnee audio capturee")

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    final = output_dir / f"reunion_{ts}.wav"
    shutil.move(tmp_wav, final)
    print(f"  Audio sauvegarde : {final}")
    return final


def run_diarization(audio: Path, output_dir: Path,
                    num_speakers: int | None) -> Path:
    """Lance diar_pipeline.run. Retourne le chemin du transcript midpoint."""
    print()
    print("=" * 60)
    print("  DIARISATION + TRANSCRIPTION")
    print("=" * 60)
    cmd = [sys.executable, "-m", "diar_pipeline.run",
           "-i", str(audio), "-o", str(output_dir)]
    if num_speakers:
        cmd += ["--num-speakers", str(num_speakers)]
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    transcript = output_dir / f"{audio.stem}.transcript.midpoint.txt"
    if not transcript.exists():
        raise FileNotFoundError(f"Transcript introuvable : {transcript}")
    return transcript


def run_meeting_minutes(transcript: Path, output_dir: Path,
                        extra_args: list[str]) -> None:
    """Lance meeting_minutes_pipeline sur le transcript."""
    print()
    print("=" * 60)
    print("  GENERATION DU COMPTE RENDU")
    print("=" * 60)
    out_md = output_dir / "compte_rendu.md"
    cmd = [sys.executable, "meeting_minutes_pipeline.py",
           "--transcript", str(transcript),
           "--output", str(out_md)] + extra_args
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print(f"  Compte rendu : {out_md}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--audio", type=Path, default=None,
                    help="Fichier audio existant (saute l'enregistrement)")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Dossier de sortie (defaut: outputs/<stem>)")
    ap.add_argument("--num-speakers", type=int, default=None)
    ap.add_argument("--skip-minutes", action="store_true",
                    help="Ne genere pas le compte rendu")
    args, extra = ap.parse_known_args()

    if args.audio:
        audio = args.audio.resolve()
        if not audio.exists():
            sys.exit(f"ERREUR: {audio} introuvable")
        out_dir = (args.output_dir or ROOT / "outputs" / audio.stem).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = (args.output_dir
                   or ROOT / "outputs" / time.strftime("reunion_%Y%m%d_%H%M%S")
                   ).resolve()
        audio = record_audio(out_dir)

    # Si l'audio vient d'etre enregistre, le out_dir diar doit correspondre au stem
    diar_out = out_dir if args.audio else out_dir
    transcript = run_diarization(audio, diar_out, args.num_speakers)

    if args.skip_minutes:
        print(f"\nTermine. Transcript : {transcript}")
        return

    run_meeting_minutes(transcript, diar_out, extra)

    print()
    print("=" * 60)
    print(f"  PIPELINE TERMINE  -  {diar_out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
