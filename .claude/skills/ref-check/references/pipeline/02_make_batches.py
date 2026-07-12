#!/usr/bin/env python3
"""
STEP 02 of the bibliography verification pipeline. See scripts/00_README.md for run order.

Consumes : bib_verification/data/01_references.json
Produces : bib_verification/data/02_batches/assistant_{1..4}.json

Splits the 66 printing references into 4 batches for the Assistant tier.

Batching here is ONLY about keeping each agent's context clean over ~17 entries. It is NOT
fan-out: the four Assistant agents run strictly one at a time, back to back, never concurrently.

Batches are contiguous over the sorted key list so that a reader can tell at a glance which
batch any given reference lives in.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "bib_verification" / "data" / "01_references.json"
OUTDIR = ROOT / "bib_verification" / "data" / "02_batches"

N_BATCHES = 4

# Fields the Assistant needs. It does NOT get the raw bibtex blob -- it gets the parsed record,
# so it cannot be confused by BibTeX syntax, and the flags that tell it where to work hardest.
KEEP = ("key", "entry_type", "raw_fields", "entry_flags", "missing_required_fields", "year")


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    refs = data["references"]

    OUTDIR.mkdir(parents=True, exist_ok=True)
    for old in OUTDIR.glob("assistant_*.json"):
        old.unlink()

    # Even, contiguous split: sizes differ by at most one.
    n = len(refs)
    base, extra = divmod(n, N_BATCHES)
    start = 0
    for i in range(N_BATCHES):
        size = base + (1 if i < extra else 0)
        chunk = refs[start:start + size]
        start += size
        payload = {
            "batch": i + 1,
            "of": N_BATCHES,
            "methodology": "scripts/methodology_assistant.md",
            "reminder": "Closed source universe. Never fabricate a link. not_found is a correct answer.",
            "entries": [{k: r[k] for k in KEEP} for r in chunk],
        }
        out = OUTDIR / f"assistant_{i+1}.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        flagged = sum(1 for r in chunk if r["entry_flags"])
        print(f"batch {i+1}: {len(chunk):2d} entries ({flagged} flagged)  -> {out.relative_to(ROOT)}")

    print(f"\nTotal {n} entries across {N_BATCHES} batches. Agents run ONE AT A TIME.")


if __name__ == "__main__":
    main()
