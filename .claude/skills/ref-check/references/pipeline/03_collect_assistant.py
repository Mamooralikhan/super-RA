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


def main():
    refs = {r["key"]: r for r in json.loads(REFS.read_text(encoding="utf-8"))["references"]}

    merged, errors, warnings = {}, [], []

    for i in range(1, 5):
        path = INDIR / f"batch_{i}.json"
        if not path.exists():
            sys.exit(f"FATAL: missing {path.relative_to(ROOT)} -- Assistant tier incomplete.")
        for e in json.loads(path.read_text(encoding="utf-8")):
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
