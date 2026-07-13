#!/usr/bin/env python3
"""
STEP 03 of the bibliography verification pipeline. See scripts/00_README.md for run order.

Consumes : bib_verification/data/03_assistant/batch_{1..4}.json
           bib_verification/data/01_references.json   (to rejoin the original bib fields)
Produces : bib_verification/data/03_assistant_merged.json
           bib_verification/data/04_batches/associate_{1,2}.json   (input to the Associate tier)

Merges the four Assistant batches and VALIDATES them. This is a gate, not a formality: if the
Assistant tier produced something structurally impossible, the pipeline stops here rather than
carrying a fabrication forward into a report the author will trust.

Checks, in order of seriousness:
  1. COVERAGE       -- all 66 keys present exactly once, no extras, no dupes.
  2. FABRICATION    -- any entry that is not not_found MUST carry an http(s) primary_link;
                       any entry that IS not_found MUST carry primary_link: null. An entry
                       claiming a find with no link, or a null find with a link, is incoherent.
  3. SCHEMA         -- every required field present.
  4. LINK PLAUSIBILITY -- links must not point at the forbidden out-of-universe domains.
                       This catches a drifting agent that wandered to ResearchGate.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "bib_verification" / "data" / "01_references.json"
INDIR = ROOT / "bib_verification" / "data" / "03_assistant"
OUT = ROOT / "bib_verification" / "data" / "03_assistant_merged.json"

REQUIRED = {"key", "entry_type", "source_universe_used", "primary_link",
            "fetched_metadata", "fetch_note", "not_found", "searched_where"}
META_REQUIRED = {"authors", "year", "title", "venue", "volume", "issue", "pages", "doi"}

# Domains the Assistant was forbidden from using as evidence. A link here means the agent
# left its closed universe, and the entry cannot be trusted as-is.
FORBIDDEN_DOMAINS = [
    "researchgate.net", "academia.edu", "semanticscholar.org", "scholar.google",
    "wikipedia.org", "scribd.com", "citeseerx", "sci-hub", "libgen",
]


def load_batch(path):
    """Read a batch an LLM subagent wrote, and NORMALISE ITS SHAPE.

    THE CONTRACT SAYS "write your JSON array". IT IS NOT ENOUGH, AND THIS IS NOT A COMPLAINT
    ABOUT THE AGENTS. On the first cold run, two Associate subagents were given the identical
    prompt, pointing at the identical contract, which says "Write your JSON array to the exact
    path given in your prompt." One wrote a bare array. The other wrapped it in
    {"batch": 2, "entries": [...]}, mirroring the shape of the INPUT file it had just read.

    Neither hallucinated. Neither disobeyed. They simply landed on different readings of a
    sentence, which is what independent agents do, and it is the same property that makes the
    Associate tier worth having in the first place.

    So the consumer normalises. BE LIBERAL IN WHAT YOU ACCEPT, STRICT IN WHAT YOU VALIDATE: the
    top-level wrapper carries no meaning, and every check that matters (coverage, forbidden
    domains, the unclicked gate) runs on the entries either way. Rejecting a batch of 17 good
    fetches over a wrapper key would be pedantry with a real cost.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("entries", "references", "records", "results"):
            if isinstance(data.get(k), list):
                return data[k]
    sys.exit(f"FATAL: {Path(path).name} is neither a JSON array nor an object wrapping one.")


def main():
    refs = {r["key"]: r for r in json.loads(REFS.read_text(encoding="utf-8"))["references"]}

    merged, errors, warnings = {}, [], []

    # DISCOVER the batches; never hardcode how many there are.
    #
    # This used to be `range(1, 5)`, which silently assumed the 66-reference paper this pipeline
    # was built on. On a 35-reference paper the sensible split is 2 batches, and step 02 was duly
    # adapted, at which point step 03 died looking for a batch_3.json that was never meant to
    # exist. The batch count was defined in TWO places and they drifted the moment one was
    # touched. One purpose, one place: the files on disk are the truth.
    #
    # Nothing is weakened by globbing, because the real gate is the COVERAGE check below: every
    # key in 01_references.json must appear exactly once across the batches. A batch that is
    # genuinely missing shows up there, by name, as an uncovered reference.
    batch_paths = sorted(INDIR.glob("batch_*.json"),
                         key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    if not batch_paths:
        sys.exit(f"FATAL: no batch_*.json in {INDIR.relative_to(ROOT)} -- Assistant tier has not run.")

    for path in batch_paths:
        i = int(re.search(r"(\d+)", path.stem).group(1))
        for e in load_batch(path):
            key = e.get("key")
            if key in merged:
                errors.append(f"{key}: appears in more than one batch")
                continue
            e["_batch"] = i
            merged[key] = e

    # 1. Coverage
    missing = sorted(set(refs) - set(merged))
    extra = sorted(set(merged) - set(refs))
    if missing:
        errors.append(f"MISSING from Assistant output ({len(missing)}): {missing}")
    if extra:
        errors.append(f"UNKNOWN keys not in the citation list: {extra}")

    for key, e in sorted(merged.items()):
        # 3. Schema
        gaps = REQUIRED - set(e)
        if gaps:
            errors.append(f"{key}: missing schema fields {sorted(gaps)}")
            continue
        mgaps = META_REQUIRED - set(e.get("fetched_metadata") or {})
        if mgaps:
            warnings.append(f"{key}: fetched_metadata missing {sorted(mgaps)}")

        link = e.get("primary_link")
        nf = bool(e.get("not_found"))

        # 2. Fabrication / coherence
        if nf:
            if link:
                errors.append(f"{key}: not_found=true but carries a link ({link}) -- incoherent")
        else:
            if not link:
                errors.append(f"{key}: claims a find but has NO link -- unevidenced claim")
            elif not re.match(r"^https?://", str(link)):
                errors.append(f"{key}: primary_link is not an http(s) URL: {link!r}")

        # 4. Out-of-universe
        if link:
            low = str(link).lower()
            for bad in FORBIDDEN_DOMAINS:
                if bad in low:
                    errors.append(f"{key}: link is OUT OF UNIVERSE ({bad}): {link}")

    if errors:
        print("VALIDATION FAILED. The Assistant tier's output cannot be trusted as-is.\n")
        for e in errors:
            print("  ERROR  ", e)
        for w in warnings:
            print("  warn   ", w)
        sys.exit(1)

    # Rejoin the original bib record so the Associate can compare source-vs-bib without
    # re-reading the .bib itself.
    records = []
    for key in sorted(merged):
        a = merged[key]
        r = refs[key]
        records.append({
            "key": key,
            "entry_type": r["entry_type"],
            "cited_in": r["cited_in"],
            "cite_count": r["cite_count"],
            "entry_flags": r["entry_flags"],
            "bib_fields": r["raw_fields"],
            "raw_bibtex": r["raw_bibtex"],
            "assistant": {k: v for k, v in a.items() if k != "_batch"},
            "assistant_batch": a["_batch"],
        })

    payload = {
        "tier": "assistant",
        "note": "Validated. Every located entry carries a real fetched link; every not_found carries null.",
        "counts": {
            "total": len(records),
            "located": sum(1 for r in records if not r["assistant"]["not_found"]),
            "not_found": sum(1 for r in records if r["assistant"]["not_found"]),
            "by_universe": dict(Counter(r["assistant"]["source_universe_used"] for r in records)),
            "doi_recovered": sum(
                1 for r in records
                if "doi" not in r["bib_fields"] and (r["assistant"]["fetched_metadata"] or {}).get("doi")
            ),
        },
        "references": records,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Batches for the Associate tier. Two agents, run STRICTLY ONE AT A TIME -- this is about
    # keeping each agent's context clean over ~33 entries, not about fan-out.
    batchdir = ROOT / "bib_verification" / "data" / "04_batches"
    batchdir.mkdir(parents=True, exist_ok=True)
    for old in batchdir.glob("associate_*.json"):
        old.unlink()
    half = (len(records) + 1) // 2
    for i, chunk in enumerate((records[:half], records[half:]), start=1):
        (batchdir / f"associate_{i}.json").write_text(
            json.dumps({
                "batch": i, "of": 2,
                "methodology": "scripts/methodology_associate.md",
                "reminder": "Click EVERY link yourself. Report, do not fix the .bib. "
                            "not_found is a valid answer.",
                "entries": chunk,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8")

    c = payload["counts"]
    print("VALIDATION PASSED")
    print(f"  total          : {c['total']}")
    print(f"  located        : {c['located']}")
    print(f"  not_found      : {c['not_found']}  "
          f"{[r['key'] for r in records if r['assistant']['not_found']]}")
    print(f"  source universe: {c['by_universe']}")
    print(f"  DOIs recovered : {c['doi_recovered']} (entries that had no DOI in the .bib)")
    for w in warnings:
        print("  warn           ", w)
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
