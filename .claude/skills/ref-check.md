# Skill: Reference Check and Review Workbook

Use this skill when the user wants a serious reference audit for a LaTeX, Overleaf, or similar academic paper. This skill is for checking what the paper currently cites against real source pages and recording the results in a review workbook.

This is a conservative workflow. The agent should not silently "fix" the bibliography, overstate certainty, or treat search snippets as verification. The output is a marked workbook for user review.

---

## What This Skill Does

- Compiles the paper first and treats the compiled bibliography as the source of truth for `reference_as_in_paper`.
- Uses the user's browser session to open DOI and URL targets and inspect the actual source page.
- Separates linked-reference checking from later missing-link discovery.
- Produces a row-ordered workbook that preserves the paper sequence and adds review fields instead of replacing the original citation text.
- Flags incorrect links, metadata issues, possible hallucinations, and cases that still need human review.

---

## What This Skill Does Not Do

- It does not verify a reference from search-result snippets alone.
- It does not silently resolve ambiguous cross-site matches.
- It does not assume a working paper should be replaced without checking whether the user wants the later journal version noted.
- It does not treat access restrictions or bot checks as evidence that a reference is false.

---

## Non-Negotiable Rules

1. Use the compiled bibliography, not the raw `.bib`, as the source of truth for the paper's current references.
2. Use the user's browser session for linked checks whenever possible, because access, cookies, and human-verification gates may matter.
3. Verify from the actual source page, not from search snippets.
4. Keep direct source-page verification separate from broader discovery work.
5. If the browser presents a human-verification gate, pause and ask the user to click through.
6. If the match is ambiguous, keep it flagged for the user instead of making a strong claim.

---

## Required Files

Before starting, confirm the following are present in the paper folder. If any required item is missing, the skill must halt and ask the user to provide it before continuing.

| File | Required for | What to do if missing |
|:---|:---|:---|
| Paper `.tex` source file | Step 1 compile and reference extraction | Halt. Cannot proceed without the source. Ask user to provide it. |
| `.bib` file(s) referenced by the paper | Step 1 compile | Halt. Compilation will fail without the bibliography source. Ask user to locate or provide them. |
| Bibliography style file(s) (`.bst`, `.sty`) | Step 1 compile | Attempt compile. If it fails due to missing style files, report the error, halt, and ask user to provide them. |
| Working LaTeX installation with `xelatex` or `pdflatex` | Step 1 compile | Halt. Report that LaTeX is not available and the skill cannot run Step 1. |
| Browser session access | Steps 3 through 5 source-page verification | Do not halt. Flag to the user that linked-reference checking requires browser access and will be skipped if unavailable. |

If Step 1 compilation fails for any reason, do not attempt to extract references from a partial or broken output. Report the exact LaTeX error, halt, and ask the user to resolve the compile issue before continuing.

## Required Inputs

Ask the user for:

1. The paper folder or manuscript path
2. The preferred workbook output path, if they already have one
3. Whether the paper has appendices or split bibliographies that must be checked separately
4. Whether the user wants working-paper rows checked for later journal publication

Confirm the Required Files check passes. Then begin Step 1.

---

## Step 1: Compile and Locate the Rendered References

- Inspect the manuscript setup before doing any reference extraction.
- If the paper uses `fontspec`, prefer `xelatex`.
- If the paper uses split bibliographies such as `bibunits`, capture each compiled reference section.
- Read the compiled `.bbl` output or the compiled PDF bibliography section only for extraction.

Target output:

- a row-ordered list of compiled references
- citation keys when available
- section tags such as `main_text` and `appendix`

Do not extract the master list from the raw `.bib` if the compiled bibliography says something else.

---

## Step 2: Build the Workbook Skeleton

Create a workbook that preserves the paper order exactly.

Core visible columns:

- `Original paper reference`
- `Reference from DOI/Link`
- `Incorrect DOI or Link`

Helpful hidden columns are allowed:

- citation key
- section
- DOI or URL used

This workbook is a review tool. Column A records what the paper currently says. Column B records what the source page says. Column C is used when the existing DOI or URL is incorrect.

---

## Step 3: Phase 1, Linked References Only

For rows that already have a DOI or URL:

1. Open the DOI or URL in the user's browser session.
2. Read the actual source page.
3. Write the source reference in the paper's style into `Reference from DOI/Link`.
4. If the DOI or URL is wrong, write `Incorrect DOI or Link` in column C.

Do not search for missing links in Phase 1. First finish the rows that already point somewhere.

---

## Step 4: Human-Verification Handling

If the browser lands on a page such as:

- `Just a moment...`
- `Are you a robot?`
- `Verify you’re human`

then:

1. stop on that reference
2. ask the user to click through
3. continue only after the real source page is readable

If many such pages appear, keep one browser tab per unresolved reference and hand the user a short queue.

---

## Step 5: Phase 2, Missing Links and Failed Linked Cases

Only after Phase 1 is stable:

1. work the rows with no DOI or URL
2. revisit incorrect DOI or URL rows
3. revisit linked rows where column B is still blank

Search order:

1. same journal site
2. same publisher site
3. same domain family
4. broader discovery only with user awareness

If the corrected source is on the same journal or publisher site and clearly matches, it can be used.

If the corrected source is cross-site, ambiguous, or only partially matches:

- keep the row flagged
- keep the tab open if helpful
- show the candidate to the user
- wait for approval before treating it as the likely source

---

## Step 6: Hallucination Rule

Use `hallucinated` only after conservative checking fails.

Do not mark an entry hallucinated just because:

- the local citation key is broken
- the DOI redirects oddly
- the source is access-restricted
- the paper cites an older working-paper version that may later have been published

Use `hallucinated` only when journal-first and broader guided checking still fail to find a matching referenced work.

---

## Workbook Review Layer

After the source-collection pass, add review columns so the workbook becomes a decision tool for the user.

Recommended columns:

- `Review status`
- `Source status`
- `Author seq`
- `Year`
- `Title / venue`
- `Vol / issue`
- `Pages / article no.`
- `DOI`
- `WP / report status`
- `Update needed`
- `Automated notes`

### Review Status Meanings

- `OK`
- `No source link`
- `Needs source check`
- `Needs metadata review`
- `Incorrect link`
- `hallucinated`

### What the User Should Be Able to Verify from the Workbook

The workbook should make it easy for the user to inspect:

- whether a possible hallucinated entry is truly unsupported
- whether a working paper appears to have a later journal version
- whether volume, issue, page, article number, year, venue, or DOI metadata looks wrong or outdated
- which rows still need a manual judgment call

### Color Guidance

- green: aligned or no action needed
- yellow: review or search required
- red: incorrect link, mismatch, or update needed
- gray: not present or not checked

---

## Browser Rules

- Use the user's browser session, not anonymous search alone, when institutional access or cookies may matter.
- Use search only to find a candidate source page, never as the final verification artifact.
- Keep unresolved tabs open at handoff time if the user still needs to inspect them.
- Close duplicate probe tabs once the queue is stable.

---

## Good Final Reporting

Summarize:

- workbook path
- linked references completed
- incorrect DOI or URL count
- no-link count remaining or resolved
- rows flagged for metadata review
- any rows that may be hallucinated
- any rows where a working paper may have a later journal version

Make clear that the workbook is a review aid and that the user remains the final verifier for ambiguous or substantive citation updates.
