# ref-check pipeline

Copy these six scripts into the user's project (a `scripts/` folder is the convention) and adapt
them. They are templates, not a library. They encode a set of guards that were each learned by
getting something wrong, and the comments explain which.

## The job is to report, not to fix

The `.tex` and the `.bib` are **read-only for every step**. No script here writes to either, and
none of them emits a corrected `.bib`. Step 01 records the byte size of both files, and step 06
re-checks those sizes and prints whether they changed. That is a claim the pipeline verifies
rather than merely asserts.

## Not found is reported as not found

No tier may substitute a guess, a near-match, or an out-of-universe source for a reference it
could not locate. A fabricated citation or link is the single unrecoverable failure this pipeline
exists to prevent. An honest empty result is a correct and complete answer.

## Run order

Every step runs in sequence. **Running one alone is not valid**, because each consumes the
previous step's output. The agent tiers sit between the scripts.

| Step | Command | Produces |
|------|---------|----------|
| 01 | `python3 01_extract_citations.py --tex <paper>.tex --bib <refs>.bib` | `bib_verification/data/01_references.json`: the references that actually print |
| 02 | `python3 02_make_batches.py` | `data/02_batches/assistant_*.json` |
| .. | **ASSISTANT TIER**: subagents, **one at a time, never concurrent**. Contract: `../methodology-assistant.md` | `data/03_assistant/batch_*.json` |
| 03 | `python3 03_collect_assistant.py` | `03_assistant_merged.json` (anti-fabrication gate) and the Associate batches |
| .. | **ASSOCIATE TIER**: subagents, one at a time. Re-clicks **every** link. Contract: `../methodology-associate.md` | `data/04_associate/batch_*.json` |
| 04 | `python3 04_collect_associate.py` | `04_associate_merged.json`. Gate: **no entry reaches the PI unclicked** |
| 05 | `python3 05_pi_review.py` | `05_pi_review.json`: final status, severity, and the PI's rulings |
| 06 | `python3 06_render.py --author "<name>"` | `reports/bibliography_audit.html` and `reports/bibliography_comparison.html` |

Each batch writes its own JSON on completion, so an interruption never loses finished work.

## Before you touch step 01

Read `../extraction-rules.md`. Every guard in `01_extract_citations.py` exists because breaking
it produced a **false accusation against a bibliography that was correct**. A bad extractor does
not fail loudly. It invents a defect, and the three tiers below it then earnestly investigate a
problem that never existed.

## Before you touch step 05

`05_pi_review.py` decides severity partly by reading the Associate's prose. That is fragile in one
specific way: **the phrase that flags a problem also appears in the sentence saying there is no
problem.** The first version read "Year is CORRECT as given" as a defect and promoted 18 correct
entries to "major".

The file therefore carries `POSITIVE_CONFIRMATION` (checked first) alongside `COSMETIC_MARKERS`,
and two ground-truth lists that you must fill in as the tiers find things:

- `GROUND_TRUTH_DEFECTS`: real defects that must always be caught.
- `GROUND_TRUTH_CORRECT`: entries a tier affirmed as correct, which must never be flagged.

`run_regression()` asserts against both on every run. **If you change the keyword lists, re-read
the entire flagged bucket**, not just the case that prompted the change. Reasoning about the
patterns in the abstract is exactly how the original bug survived.

## Step 05 is yours, not a subagent's

The PI tier is judgement. Write your rulings into `RULINGS` in `05_pi_review.py`, not into the
chat. A ruling in a transcript is lost. A ruling in the script travels with the pipeline, can be
audited and argued with, and survives a re-run.

## One purpose, one place

A later fix goes **inside** the numbered step that owns it, so that re-running from 01 never
forgets it. Do not add ad-hoc side scripts.
