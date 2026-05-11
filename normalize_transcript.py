"""
Normalise un transcript en decoupant chaque tour de parole en phrases.
Preserve timestamps et speakers. Utile pour uniformiser la granularite
entre differents modeles de transcription avant chunking semantique.

Usage :
    python normalize_transcript.py INPUT.txt OUTPUT.txt
    python normalize_transcript.py INPUT.txt OUTPUT.txt --max-chars 300
"""
import argparse
import re
from pathlib import Path

# Regex des formats supportes (copie de v3.load_segments_from_transcript)
RE_TS_LONG  = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]\s+(.+?):\s+(.*)")
RE_TS_SHORT = re.compile(r"^\[(\d{2}):(\d{2})\]\s+\*{0,2}(.+?)\*{0,2}:\s+(.*)")
# Format range : [MM:SS.ms - MM:SS.ms]  SPEAKER : text  (ou HH:MM:SS.ms)
RE_TS_RANGE = re.compile(
    r"^\[[\d:.]+\s*-\s*[\d:.]+\]\s+(.+?)\s*:\s*(.*)"
)
RE_NO_TS    = re.compile(r"^(.+?):\s+(.+)$")

# Split en phrases : apres . ! ? suivi d'un espace ou fin de ligne,
# sauf apres abbreviations courantes FR.
ABBREV = {"M.", "Mme.", "Mlle.", "Dr.", "Pr.", "St.", "Ste.", "cf.",
          "ex.", "etc.", "p.", "pp.", "n°.", "No.", "vs.", "env."}


def split_sentences(text: str, max_chars: int | None = None) -> list[str]:
    """Decoupe en phrases en respectant les abbreviations courantes.
    Si max_chars est fourni, force un split dur sur les phrases trop longues."""
    if not text.strip():
        return []

    # Marque temporairement les abbreviations pour eviter de splitter dessus
    placeholder = "\x00"
    protected = text
    for ab in ABBREV:
        protected = protected.replace(ab, ab.replace(".", placeholder))

    # Split apres . ! ? suivi d'espace
    parts = re.split(r"(?<=[.!?])\s+", protected)
    # Restaure les points
    sentences = [p.replace(placeholder, ".").strip() for p in parts if p.strip()]

    # Split dur sur longueur max si demande
    if max_chars:
        out = []
        for s in sentences:
            while len(s) > max_chars:
                # Coupe au dernier espace avant max_chars
                cut = s.rfind(" ", 0, max_chars)
                if cut <= 0:
                    cut = max_chars
                out.append(s[:cut].strip())
                s = s[cut:].strip()
            if s:
                out.append(s)
        sentences = out

    return sentences


def normalize_line(line: str, max_chars: int | None) -> list[str]:
    """Retourne 1..N lignes normalisees pour une ligne d'entree."""
    line = line.rstrip()
    if not line.strip():
        return []

    # Detecte le format (timestamps ignores pour economiser des tokens LLM)
    m = RE_TS_RANGE.match(line)
    if not m:
        m = RE_TS_LONG.match(line)
        if m:
            _, _, _, speaker, text = m.groups()
        else:
            m = RE_TS_SHORT.match(line)
            if m:
                _, _, speaker, text = m.groups()
            else:
                m = RE_NO_TS.match(line)
                if m:
                    speaker, text = m.groups()
                else:
                    # Ligne non parsable : on la laisse telle quelle
                    return [line]
    else:
        speaker, text = m.groups()
    prefix = f"{speaker.strip()}:"

    sentences = split_sentences(text, max_chars=max_chars)
    if not sentences:
        return []
    return [f"{prefix} {s}" for s in sentences]


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalise un transcript par phrase.")
    ap.add_argument("input", help="Transcript source .txt")
    ap.add_argument("output", help="Transcript normalise .txt")
    ap.add_argument("--max-chars", type=int, default=300,
                    help="Longueur max d'une phrase apres split (0 = pas de limite dure). Defaut : 300.")
    args = ap.parse_args()

    max_chars = args.max_chars if args.max_chars > 0 else None

    src = Path(args.input)
    dst = Path(args.output)
    if not src.exists():
        raise SystemExit(f"Fichier introuvable : {src}")

    n_in, n_out = 0, 0
    with src.open("r", encoding="utf-8") as f_in, dst.open("w", encoding="utf-8") as f_out:
        for line in f_in:
            n_in += 1
            for out_line in normalize_line(line, max_chars):
                f_out.write(out_line + "\n")
                n_out += 1

    ratio = n_out / n_in if n_in else 0
    print(f"Normalise : {src.name} ({n_in} lignes) -> {dst.name} ({n_out} lignes, x{ratio:.1f})")


if __name__ == "__main__":
    main()
