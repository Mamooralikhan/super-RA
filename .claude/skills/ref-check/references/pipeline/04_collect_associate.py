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
import re
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


def load_batch(path):
    """Read a batch an LLM subagent wrote, and NORMALISE ITS SHAPE.

    On the first cold run, two Associate subagents were given the identical prompt pointing at
    the identical contract, which says "Write your JSON array to the exact path given in your
    prompt." One wrote a bare array. The other wrapped it in {"batch": 2, "entries": [...]},
    mirroring the shape of the input file it had just read. Neither hallucinated and neither
    disobeyed; they read one sentence two ways, which is what independent agents do.

    BE LIBERAL IN WHAT YOU ACCEPT, STRICT IN WHAT YOU VALIDATE. The wrapper carries no meaning.
    Every check that matters, above all the unclicked gate, runs on the entries either way.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("entries", "references", "records", "results"):
            if isinstance(data.get(k), list):
                return data[k]
    sys.exit(f"FATAL: {Path(path).name} is neither a JSON array nor an object wrapping one.")


# The fields the Associate is the AUTHOR of. Everything else on a record belongs to step 03 and
# is not the Associate's to restate, lose, or reshape.
ASSOCIATE_FIELDS = (
    "link_status", "link_verified", "verified_metadata", "bib_discrepancies",
    "corrections_made", "corroborating_source", "still_not_found", "associate_note",
)


def normalise(entry):
    """Take one Associate record, however it chose to lay itself out, and flatten it.

    THIRD SHAPE DIVERGENCE ON THE FIRST COLD RUN, AND THE MOST INSTRUCTIVE ONE. The contract
    heading reads "Output: add these fields, keep everything else". Two subagents, same prompt,
    same contract:

        batch 2  put link_status, verified_metadata, ... at the TOP LEVEL. Correct.
        batch 1  nested every one of them under an "associate": {...} sub-object, and dropped
                 the "assistant" record on the floor while it was at it.

    The second layout is not unreasonable. It is arguably tidier. It is simply not the one the
    consumer expected, and the consumer had no business expecting anything: an LLM writing JSON
    to a prose spec will land on a defensible-but-different shape often enough that treating it
    as an error is just building a pipeline that breaks on Tuesdays.

    Worse, because batch 1 dropped the "assistant" sub-record, the unclicked gate below would
    have read a missing not_found as False and then FALSELY ACCUSED bhavnani08 of reaching the PI
    unclicked, when in truth it was correctly recorded as no_link. A false accusation manufactured
    by a schema mismatch is exactly the disease this whole pipeline exists to cure.
    """
    if isinstance(entry.get("associate"), dict):
        for k, v in entry["associate"].items():
            entry.setdefault(k, v)
    return entry


def main():
    base = {r["key"]: r for r in json.loads(REFS.read_text(encoding="utf-8"))["references"]}
    expected = set(base)

    merged, errors = {}, []

    # DISCOVER the batches; never hardcode how many there are. See the same note in step 03: the
    # batch count was hardcoded here AND in step 02, so adapting one for a differently sized paper
    # left the other looking for a file that was never meant to exist. The coverage check below is
    # the real gate, and it names any reference that actually went missing.
    batch_paths = sorted(INDIR.glob("batch_*.json"),
                         key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    if not batch_paths:
        sys.exit(f"FATAL: no batch_*.json in {INDIR.relative_to(ROOT)} -- Associate tier has not run.")

    # OVERLAY, DO NOT TRUST. Step 03's merged record is authoritative for everything the
    # Associate does not own. We take the Associate's FINDINGS and lay them over that base,
    # rather than accepting whatever the subagent chose to echo back. An agent that forgets to
    # copy a field forward can then no longer corrupt the record by omission.
    for path in batch_paths:
        for e in load_batch(path):
            e = normalise(e)
            key = e.get("key")
            if key in merged:
                errors.append(f"{key}: appears in more than one Associate batch")
                continue
            if key not in base:
                errors.append(f"{key}: not a reference in this paper")
                continue
            rec = dict(base[key])
            for f in ASSOCIATE_FIELDS:
                if f in e:
                    rec[f] = e[f]
            merged[key] = rec

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
