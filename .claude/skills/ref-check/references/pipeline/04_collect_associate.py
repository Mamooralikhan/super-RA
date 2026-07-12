#!/usr/bin/env python3
"""
STEP 04 of the bibliography verification pipeline. See scripts/00_README.md for run order.

Consumes : bib_verification/data/04_associate/batch_{1,2}.json
Produces : bib_verification/data/04_associate_merged.json

Merges the Associate tier and enforces its ONE non-negotiable guarantee:

    NO ENTRY REACHES THE PI TIER UNCLICKED.

The Associate exists to be the anti-hallucination layer. If it did not actually fetch a link,
it did not do its job, and the entry cannot be presented to the author as verified. A missing
or unrecognised link_status is therefore a hard failure, not a warning.

Valid link_status values:
  resolved_and_matched  -- Associate personally loaded the page and it matched.
  blocked_corroborated  -- page refused the fetch (403/paywall); confirmed via a second
                           authoritative source, which MUST be named.
  mismatch              -- page loaded and is NOT the work claimed. A serious finding.
  dead                  -- link does not resolve at all.
  no_link               -- entry is not_found; there is nothing to click.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDIR = ROOT / "bib_verification" / "data" / "04_associate"
REFS = ROOT / "bib_verification" / "data" / "03_assistant_merged.json"
OUT = ROOT / "bib_verification" / "data" / "04_associate_merged.json"

VALID_STATUS = {"resolved_and_matched", "blocked_corroborated", "mismatch", "dead", "no_link"}
# Statuses that mean the Associate actually established something about the link.
CLICKED = {"resolved_and_matched", "blocked_corroborated", "mismatch", "dead"}


def main():
    expected = {r["key"] for r in json.loads(REFS.read_text(encoding="utf-8"))["references"]}

    merged, errors = {}, []
    for i in (1, 2):
        path = INDIR / f"batch_{i}.json"
        if not path.exists():
            sys.exit(f"FATAL: missing {path.relative_to(ROOT)} -- Associate tier incomplete.")
        for e in json.loads(path.read_text(encoding="utf-8")):
            key = e.get("key")
            if key in merged:
                errors.append(f"{key}: appears in more than one Associate batch")
                continue
            merged[key] = e

    missing = sorted(expected - set(merged))
    extra = sorted(set(merged) - expected)
    if missing:
        errors.append(f"MISSING from Associate output ({len(missing)}): {missing}")
    if extra:
        errors.append(f"UNKNOWN keys: {extra}")

    for key, e in sorted(merged.items()):
        status = e.get("link_status")
        if status not in VALID_STATUS:
            errors.append(f"{key}: invalid or missing link_status {status!r}")
            continue

        # THE GATE. An entry the Assistant located must have been clicked by the Associate.
        assistant_found = not e.get("assistant", {}).get("not_found", False)
        if assistant_found and status not in CLICKED:
            errors.append(
                f"{key}: Assistant located it, but Associate status is {status!r} -- UNCLICKED. "
                "No entry may reach the PI tier unverified."
            )

        # A blocked fetch is only acceptable if a corroborating source is actually named.
        if status == "blocked_corroborated" and not (e.get("corroborating_source") or "").strip():
            errors.append(f"{key}: blocked_corroborated but names NO corroborating source")

        if "verified_metadata" not in e:
            errors.append(f"{key}: no verified_metadata")

    if errors:
        print("VALIDATION FAILED. The Associate tier did not meet its guarantee.\n")
        for x in errors:
            print("  ERROR  ", x)
        sys.exit(1)

    records = [merged[k] for k in sorted(merged)]
    status_counts = Counter(r["link_status"] for r in records)

    clicked = sum(1 for r in records if r["link_status"] in CLICKED)
    corrected = [r["key"] for r in records if r.get("corrections_made")]
    with_disc = [r["key"] for r in records if r.get("bib_discrepancies")]
    still_nf = [r["key"] for r in records if r.get("still_not_found")]
    mismatched = [r["key"] for r in records if r["link_status"] == "mismatch"]

    payload = {
        "tier": "associate",
        "guarantee": "Every entry the Assistant located was independently re-fetched by the Associate.",
        "counts": {
            "total": len(records),
            "links_clicked": clicked,
            "by_link_status": dict(status_counts),
            "assistant_records_corrected": len(corrected),
            "entries_with_bib_discrepancies": len(with_disc),
            "still_not_found": len(still_nf),
        },
        "still_not_found_keys": still_nf,
        "mismatch_keys": mismatched,
        "assistant_corrected_keys": corrected,
        "references": records,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    c = payload["counts"]
    print("VALIDATION PASSED -- no entry reaches the PI tier unclicked.\n")
    print(f"  total                     : {c['total']}")
    print(f"  links clicked             : {c['links_clicked']}")
    print(f"  by link_status            : {c['by_link_status']}")
    print(f"  Assistant records corrected: {c['assistant_records_corrected']}  {corrected}")
    print(f"  entries w/ bib discrepancy : {c['entries_with_bib_discrepancies']}")
    print(f"  MISMATCH (link != work)    : {mismatched}")
    print(f"  still not found            : {still_nf}")
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
