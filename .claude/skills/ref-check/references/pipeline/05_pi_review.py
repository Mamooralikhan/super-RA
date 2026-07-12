#!/usr/bin/env python3
"""
STEP 05 of the bibliography verification pipeline. See scripts/00_README.md for run order.

Consumes : bib_verification/data/04_associate_merged.json
Produces : bib_verification/data/05_pi_review.json

THE PI TIER. This is judgement, not fetching, and it is NOT delegated to a subagent.

The rulings below were made by the PI after personally spot-checking 10 of the 66 references
(15%) against live sources -- reading the World Bank PDF's cover page directly, and querying
Crossref for the disputed DOIs, years and author lists. Encoding them here, rather than leaving
them in a chat transcript, is deliberate: the ruling and its reason travel with the pipeline and
can be audited, challenged, and re-run.

WHAT THE PI ADDS THAT THE LOWER TIERS STRUCTURALLY CANNOT:

  1. AUTHOR HIERARCHY. The published author order governs. The Associate verified order on every
     entry; the PI rules on what to do where the .bib disagrees.
  2. CURRENCY. A working paper that has since been published is out of date -- but "correcting"
     it silently would rewrite every in-text \\citep{} rendering. So it is REPORTED as a decision
     for the author, never applied.
  3. CONTEXT THE MACHINE LACKS. The clearest case here is olson1971logic. Both lower tiers called
     the 1971 date an ERROR because Crossref registers only 1965 and 2009. That is wrong: the
     1971 revised Harvard edition is real and routinely cited; Crossref's DOI coverage of
     pre-digital book editions is simply poor. Treating "absent from Crossref" as "does not
     exist" would have reversed a correct authorial choice. The PI overrules the lower tiers.

FINAL STATUS -- one of four:
  verified                      -- found at an authoritative source, link clicked, metadata matches.
  not_found                     -- searched the authoritative universe; genuinely not there.
  not_independently_verifiable  -- reachable but not confirmable to that standard. NOT an error.
  needs_author_review           -- something is wrong, or the call belongs to the author.

SEVERITY -- how much the author should care:
  critical  -- the citation points at the WRONG WORK. Must be fixed before submission.
  major     -- metadata is wrong in a way a reader or copyeditor would catch.
  decision  -- nothing is wrong; the author must choose (e.g. cite the published version?).
  minor     -- cosmetic: missing DOI, exporter junk in a field, capitalisation.
  clean     -- no discrepancy worth the author's time.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "bib_verification" / "data" / "04_associate_merged.json"
OUT = ROOT / "bib_verification" / "data" / "05_pi_review.json"

# References the PI personally re-fetched and confirmed (15% sample, plus every critical claim).
PI_SPOT_CHECKED = {
    # FILL THIS IN AS YOU GO. Map key -> what you personally checked and what you saw.
    # Target roughly 15% of the references, PLUS every entry any tier called critical.
    # Example:
    #   "smith2019": "PI queried Crossref directly: published-print 2020, not 2019 as the .bib says.",
}

# ---------------------------------------------------------------------------------------------
# THE PI'S RULINGS. Anything not named here falls through to the default rule further down.
#
# WRITE YOUR RULINGS HERE, NOT IN THE CHAT. A ruling recorded in a transcript is lost; a ruling
# recorded here travels with the pipeline, can be audited and argued with, and survives a re-run.
#
# Format:  "key": (final_status, severity, "the ruling, addressed to the author")
#
#   final_status: verified | not_found | not_independently_verifiable | needs_author_review
#   severity:     critical | major | decision | minor | clean
#
# Write the ruling as prose the author will actually read. Say what is wrong, say how you know,
# and say what they have to decide. If you overruled a lower tier, say so and say why.
#
# Worked examples from the run this pipeline was built on, kept because they show the SHAPE of
# each severity. Delete them and write your own.
#
#   "worldbank2014report": (
#       "needs_author_review", "critical",
#       "THE CITED REPORT DOES NOT EXIST. The URL in the .bib serves a report about a different "
#       "country; I downloaded it and read the cover. The issuing body's own search API returns "
#       "zero hits for the cited title. DECIDE: which work did you intend to cite?"
#   ),
#   "smith2023roads": (
#       "needs_author_review", "major",
#       "WRONG YEAR. The .bib says 2023; the journal of record says 2024, and I confirmed it at "
#       "Crossref. Same paper, only the year is wrong. Note the consequence: fixing it changes "
#       "the in-text citation everywhere it appears."
#   ),
#   "jones2025working": (
#       "needs_author_review", "decision",
#       "THIS IS NOW PUBLISHED. The .bib types it @unpublished. It appeared in a journal in 2026. "
#       "DELIBERATELY NOT APPLIED: switching to the published version changes the year and rewrites "
#       "your in-text citations. That is your call, not the pipeline's."
#   ),
#   "olson1971logic": (
#       "needs_author_review", "decision",
#       "PI OVERRULES BOTH LOWER TIERS. They flagged the year as an error because Crossref "
#       "registers only the 1965 and 2009 editions. That inference is unsound: the 1971 revised "
#       "edition is real and routinely cited, and Crossref's coverage of pre-digital book editions "
#       "is poor. ABSENT FROM CROSSREF IS NOT THE SAME AS DOES NOT EXIST. No change needed."
#   ),
# ---------------------------------------------------------------------------------------------
RULINGS = {
}

# ---------------------------------------------------------------------------------------------
# CLASSIFYING A DISCREPANCY LINE. Read this before touching the patterns below.
#
# The Associate writes its findings as PROSE. That makes keyword matching dangerous in one very
# specific way: a phrase that flags a problem almost always also appears inside the sentence that
# says there ISN'T one. "Year is CORRECT as given" contains "year"; "the truncation is
# legitimate" contains "truncat"; "which is correct as cited" contains "cited".
#
# The first version of this rule had exactly that bug and promoted 18 entries to 'major',
# including several whose trigger sentence literally began "Year is CORRECT as given".
#
# So: every positive trigger is paired with an explicit EXCLUSION list, and the exclusions are
# checked FIRST. When you change either list, re-read the ENTIRE flagged bucket -- not just the
# one case that prompted the change.
# ---------------------------------------------------------------------------------------------

# The Associate is affirming the .bib is RIGHT. These sentences must never promote an entry.
POSITIVE_CONFIRMATION = (
    "is correct as given", "is correct as cited", "year is correct", "which is correct",
    "is expected and correct", "correct and unfixable", "is legitimate",
    "truncation is legitimate", "not the author's fault", "cannot be resolved",
    "not applied", "informational:", "false positive", "false alarm",
    "own preferred form", "the bib's form is the fuller", "conventional citation year",
    "no 'upgrade' to report", "not a defect", "match the source's first",
    "are the first ten in the authoritative order", "in the bib's order",
)

# Real but cosmetic: worth listing in the report, not worth the author's decision time.
COSMETIC_MARKERS = (
    "no doi", "doi of record", "carries no doi", "has no doi", "street address",
    "google scholar", "elided", "house style", "cosmetic", "trivial", "styling only",
    "article number", "capitalis", "lower-case", "abbreviat", "duplicate_key", "hygiene",
    "footnote asterisk", "harmless", "middle initial", "no middle initial",
    "city belongs in an address field", "and others",
    # The publisher field naming a DELIVERY PLATFORM ('Oxford Academic', 'Wiley Online Library')
    # rather than the publisher. The aer/natbib style ignores publisher for @article entirely, so
    # this never reaches the page.
    "delivery platform",
    # 'Monogan III' vs Crossref's 'James E. Monogan'. The .bib preserves the generational suffix
    # the author himself uses; Crossref drops it. The .bib is arguably the more correct form.
    "generational suffix",
)


def classify_line(line):
    """Return 'affirming' | 'cosmetic' | 'substantive' for one discrepancy sentence.

    Exclusions are checked FIRST. This ordering is the whole point.
    """
    low = line.lower()
    if any(p in low for p in POSITIVE_CONFIRMATION):
        return "affirming"
    if any(m in low for m in COSMETIC_MARKERS):
        return "cosmetic"
    return "substantive"


def default_ruling(rec):
    """Entries the PI did not rule on individually.

    Conservative in the right direction: an entry is only called clean when the Associate actually
    clicked its link AND nothing substantive survived classification.
    """
    if rec.get("still_not_found") or rec["link_status"] in ("mismatch", "dead"):
        return ("not_found", "critical",
                "Could not be confirmed at any authoritative source. Reported as not found rather "
                "than guessed at.")

    disc = rec.get("bib_discrepancies") or []
    if not disc:
        return ("verified", "clean", "Confirmed at an authoritative source; no discrepancy found.")

    substantive = [d for d in disc if classify_line(d) == "substantive"]
    if substantive:
        return ("needs_author_review", "major", "Substantive discrepancy: " + substantive[0])

    cosmetic = [d for d in disc if classify_line(d) == "cosmetic"]
    if cosmetic:
        return ("verified", "minor",
                f"Confirmed at an authoritative source. {len(cosmetic)} cosmetic point(s) noted "
                "(missing DOI, exporter junk in a field, house-style differences) -- nothing that "
                "changes the reference.")

    return ("verified", "clean",
            "Confirmed at an authoritative source. The Associate's notes affirm the .bib is "
            "correct as written.")


# ---------------------------------------------------------------------------------------------
# REGRESSION SUITE. Runs on every invocation; a failure aborts the pipeline.
#
# These two lists are GROUND TRUTH, hand-confirmed during the Assistant/Associate tiers and by
# the PI's own spot-checks. The classifier above is prose-driven and therefore fragile, so it is
# pinned against reality here. If you touch POSITIVE_CONFIRMATION or COSMETIC_MARKERS, this is
# what tells you whether you broke something -- reasoning about the patterns in the abstract is
# exactly how the original negation bug survived.
# ---------------------------------------------------------------------------------------------

# Real defects. Every one MUST end up as needs_author_review.
# Real defects, hand-confirmed. Every one MUST end up as needs_author_review.
# BUILD THIS LIST AS THE TIERS FIND THINGS. It is what tells you the classifier still works.
GROUND_TRUTH_DEFECTS = [
]

# Entries a tier explicitly AFFIRMED as correct. None may ever be reported as a defect.
# A false alarm here wastes the author's time and erodes trust in every other finding.
# Populate this with the entries whose notes say things like "year is correct as given".
GROUND_TRUTH_CORRECT = [
]


def enforce_pi_work(records):
    """THE PI MUST ACTUALLY DO THE WORK BEFORE A REPORT IS PRODUCED. This gate says so.

    WHY THIS EXISTS. The regression suite below is the only thing standing between the prose
    classifier and a repeat of the negation bug that once promoted 18 correct entries to 'major'.
    But it is pinned against GROUND_TRUTH_DEFECTS and GROUND_TRUTH_CORRECT, and those lists ship
    EMPTY, because they are per-paper. So on a fresh run the suite iterated over nothing and
    passed. It could not fail. A check that cannot fail is not a check, it is a decoration that
    makes you feel checked, which is strictly worse than having none.

    The fix is not to invent ground truth. It is to notice that the PI is ALREADY REQUIRED to
    spot-check a sample by hand, and that those spot-checks ARE the ground truth. The two things
    were sitting in the same file ignoring each other. This gate wires them together.

    THERE IS NO ESCAPE HATCH, DELIBERATELY. A flag to skip this would become the default path
    within two runs, and then we would be back to a decoration. If the pipeline stops here, the
    answer is to go and check the references, which is the job.

    Note what the last two rules do NOT require: a paper with genuinely nothing wrong may leave
    GROUND_TRUTH_DEFECTS empty, and that is correct. It is only empty-while-you-found-something
    that is forbidden.
    """
    n = len(records)
    if n == 0:
        return

    problems = []

    # 1. A sample, actually re-fetched by the PI in person.
    required = min(n, max(3, math.ceil(0.10 * n)))
    if len(PI_SPOT_CHECKED) < required:
        problems.append(
            f"PI_SPOT_CHECKED holds {len(PI_SPOT_CHECKED)} entries; this run needs at least "
            f"{required} of {n} ({required/n:.0%}). Re-fetch that many yourself, and write down "
            f"what you SAW, not what a lower tier told you."
        )

    # 2. Every critical claim, checked by the PI personally. The docstring at the top of this file
    #    has always asked for this. Nothing enforced it. A tier calling something critical and
    #    nobody verifying it is how a false accusation reaches an author.
    criticals = [r["key"] for r in records if r["severity"] == "critical"]
    unchecked = [k for k in criticals if k not in PI_SPOT_CHECKED]
    if unchecked:
        problems.append(
            "these entries are CRITICAL and the PI did not personally verify them: "
            + ", ".join(unchecked)
            + ". A critical finding accuses the author of citing the wrong work. Look at it "
              "yourself before the report says so."
        )

    # 3 and 4. The regression suite needs something to pin against, or it passes vacuously.
    if any(r["final_status"] == "needs_author_review" for r in records) and not GROUND_TRUTH_DEFECTS:
        problems.append(
            "entries were flagged needs_author_review, but GROUND_TRUTH_DEFECTS is empty. The "
            "regression suite has nothing to pin the classifier against and will pass no matter "
            "what you break. List the defects you confirmed by hand."
        )
    if any(r["severity"] in ("clean", "minor") for r in records) and not GROUND_TRUTH_CORRECT:
        problems.append(
            "entries were affirmed as correct, but GROUND_TRUTH_CORRECT is empty. That list is "
            "what catches a false alarm, and a false alarm wastes the author's time and erodes "
            "trust in every other finding on the page. List the entries you confirmed are fine."
        )

    if problems:
        print("PI GATE FAILED. No report will be produced.\n")
        for p in problems:
            print(f"  - {p}\n")
        print("This is not a bug. The pipeline refuses to render a report the PI has not stood\n"
              "behind. Populate PI_SPOT_CHECKED, GROUND_TRUTH_DEFECTS and GROUND_TRUTH_CORRECT\n"
              "in this file, then run again.")
        raise SystemExit(1)


def run_regression(records):
    by_key = {r["key"]: r for r in records}

    # A ground-truth key that is not in the run at all is a typo, not a defect. Say so plainly
    # rather than dying on a KeyError three frames down.
    stray = [k for k in list(GROUND_TRUTH_DEFECTS) + list(GROUND_TRUTH_CORRECT) if k not in by_key]
    if stray:
        print("REGRESSION CANNOT RUN. These ground-truth keys are not in this run:")
        for k in stray:
            print(f"  unknown key: {k}")
        raise SystemExit(1)

    missed = [k for k in GROUND_TRUTH_DEFECTS
              if by_key[k]["final_status"] != "needs_author_review"]
    false_alarms = [k for k in GROUND_TRUTH_CORRECT
                    if by_key[k]["final_status"] == "needs_author_review"]
    leaks = []
    for r in records:
        if r["key"] in RULINGS or r["final_status"] == "needs_author_review":
            continue
        subs = [d for d in (r.get("bib_discrepancies") or [])
                if classify_line(d) == "substantive"]
        if subs:
            leaks.append((r["key"], subs[0][:80]))

    if missed or false_alarms or leaks:
        print("REGRESSION FAILED -- the classifier no longer matches reality.\n")
        for k in missed:
            print(f"  MISSED a known real defect : {k}")
        for k in false_alarms:
            print(f"  FALSE ALARM on a correct entry: {k}")
        for k, s in leaks:
            print(f"  LEAK (substantive -> clean): {k}: {s}")
        raise SystemExit(1)

    print(f"  regression: {len(GROUND_TRUTH_DEFECTS)} known defects all caught, "
          f"{len(GROUND_TRUTH_CORRECT)} affirmed-correct entries all cleared, no leaks.")


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    out = []

    for rec in data["references"]:
        key = rec["key"]
        if key in RULINGS:
            status, severity, note = RULINGS[key]
        else:
            status, severity, note = default_ruling(rec)

        rec["final_status"] = status
        rec["severity"] = severity
        rec["pi_note"] = note
        rec["pi_spot_checked"] = key in PI_SPOT_CHECKED
        rec["pi_spot_check_note"] = PI_SPOT_CHECKED.get(key, "")
        out.append(rec)

    enforce_pi_work(out)
    run_regression(out)

    from collections import Counter
    statuses = Counter(r["final_status"] for r in out)
    severities = Counter(r["severity"] for r in out)

    payload = {
        "tier": "pi",
        "note": "Judgement tier. Not delegated. Rulings are recorded in scripts/05_pi_review.py.",
        "spot_check": {
            "sampled": len(PI_SPOT_CHECKED),
            "of": len(out),
            "pct": round(100 * len(PI_SPOT_CHECKED) / len(out), 1),
            "detail": PI_SPOT_CHECKED,
        },
        "counts": {"by_status": dict(statuses), "by_severity": dict(severities)},
        "references": out,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"PI review complete. Spot-checked {len(PI_SPOT_CHECKED)}/{len(out)} "
          f"({payload['spot_check']['pct']}%) personally.\n")
    print("  by final status:")
    for k, v in statuses.most_common():
        print(f"     {k:30s} {v}")
    print("\n  by severity:")
    for k in ("critical", "major", "decision", "minor", "clean"):
        if severities.get(k):
            print(f"     {k:30s} {severities[k]}")
    print("\n  CRITICAL:", [r["key"] for r in out if r["severity"] == "critical"])
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
