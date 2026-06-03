---
name: ref-check
description: Audit references in LaTeX or Overleaf-style papers by compiling the manuscript, using the compiled bibliography as the source of truth, checking linked references through the user's browser session, handling human-verification gates conservatively, and producing a color-coded Excel review workbook that marks possible link, metadata, and hallucination issues for user verification. Use when the user asks for reference checking, bibliography verification, DOI or URL validation, source-by-source citation auditing, or a staged reference review workflow.
---

# Ref Check

Use this skill for serious bibliography audits where the user wants a compiled-paper-first workflow and a reviewable spreadsheet artifact.

This skill is conservative by design. It should help the user inspect what the paper cites and how those citations compare with source pages. It should not silently finalize ambiguous references or overstate what the model has verified.

## What This Skill Does

- Compiles the paper first and treats the compiled bibliography as the source of truth.
- Uses the user's browser session to inspect actual DOI and URL targets.
- Separates linked-reference verification from missing-link discovery.
- Produces an Excel workbook that preserves paper order and adds review columns instead of replacing the original citation text.
- Flags incorrect links, metadata issues, possible hallucinations, and rows that still need human review.

## What the User Gets

The output workbook is a review aid, not an unreviewed replacement bibliography. It should help the user verify:

- whether an existing DOI or URL is wrong
- whether a citation may be hallucinated
- whether a working paper appears to have a later journal version
- whether year, venue, volume, issue, pages, article number, or DOI metadata appear incorrect or outdated

## When to Use This Skill

Use it when the user wants any of the following:

- reference checking
- bibliography verification
- DOI or URL validation
- a paper-to-source citation audit
- a spreadsheet of references with comparisons
- a staged workflow such as "linked references first, missing links second"

## Non-Negotiable Rules

1. Use the compiled bibliography, not the raw `.bib`, as the source of truth for `Original paper reference`.
2. Do not mark a reference as verified from search-result snippets alone.
3. Use the user's browser session for source-page checks when access, cookies, or click-through gates may matter.
4. If the browser shows a human-verification gate, pause and ask the user to click through.
5. Keep direct source-page verification separate from broader discovery work.
6. For high-stakes review work, do not silently best-guess an ambiguous citation as correct.

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

## Workflow

### Step 1: Compile and Locate the Rendered References

- Inspect the manuscript setup first.
- If the paper uses `fontspec`, prefer `xelatex`.
- If the paper uses split bibliographies such as `bibunits`, capture each compiled reference section.
- Read the compiled `.bbl` output or compiled PDF bibliography section only for extraction.

Target output:

- a row-ordered list of compiled references
- citation keys when available
- section tags such as `main_text` and `appendix`

### Step 2: Build the Workbook Skeleton

Start with these core columns:

- `Original paper reference`
- `Reference from DOI/Link`
- `Incorrect DOI or Link`

Hidden helper columns are fine:

- citation key
- section
- current DOI/URL

Preserve the paper sequence exactly.

### Step 3: Phase 1, Linked References Only

For rows that already have a DOI or URL:

1. open the DOI or URL in the user's browser session
2. read the actual source page
3. write the source reference in the paper's style into `Reference from DOI/Link`
4. if the DOI or URL is wrong, write `Incorrect DOI or Link` in column C

Do not search for missing links in Phase 1.

### Step 4: Human-Verification Handling

If the browser lands on a page such as:

- `Just a moment...`
- `Are you a robot?`
- `Verify you’re human`

then:

1. stop on that reference
2. ask the user to click through
3. continue only after the real source page is readable

If many such pages exist, batch them and keep one tab per unresolved reference.

### Step 5: Phase 2, Missing Links and Failed Linked Cases

Only after Phase 1 is stable:

1. work the rows with no DOI or URL
2. revisit incorrect DOI or URL rows
3. revisit linked rows where column B is still blank

Search order:

1. same journal site
2. same publisher site
3. same domain family
4. broader discovery only with user awareness

If the corrected source is on the same journal or publisher site and clearly matches, it can be used without escalation.

If the corrected source is cross-site, ambiguous, or only partially matches:

- keep the row flagged
- keep the candidate visible to the user
- wait for approval before treating it as the likely source

### Step 6: Hallucination Rule

Use `hallucinated` only after conservative checking fails.

Do not mark an entry hallucinated just because:

- the local citation key is broken
- the DOI redirects oddly
- the source is access-restricted
- the paper cites an older working-paper version

Mark `hallucinated` only when the cited work does not show up after journal-first and broader guided checking.

## Workbook Review Layer

After the source-collection pass, add review columns so the workbook becomes a decision tool.

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

### Color Guidance

- green: good or aligned
- yellow: review or search required
- red: incorrect link, mismatch, or update needed
- gray: not present or not checked

### Interpretation Rules

- `Not present` is different from `Unchecked`
- books and reports may legitimately lack volume, pages, or DOI
- working-paper rows should be checked for later journal publication if the user wants that review
- the user remains the final verifier for ambiguous metadata changes

## Browser Rules

- Use the user's browser session, not generic search alone, when institutional access matters.
- Use search only to find the source page, never as the final verification artifact.
- Keep unresolved tabs open at handoff time.
- Close duplicate probe tabs once the queue is stable.

## Suggested Execution Shape

When the user gives a paper folder:

1. ask for the paper folder path, preferred workbook output path, whether split bibliographies exist, and whether working-paper rows should be checked for later journal publication
2. confirm Required Files check passes
3. compile
4. extract compiled references
5. build workbook
6. Phase 1 linked rows
7. pause for human-verification gates
8. Phase 2 missing links and incorrect links
9. add review columns and polish the workbook

## Good Final Reporting

Summarize:

- workbook path
- linked references completed
- incorrect DOI or URL count
- no-link count remaining or resolved
- rows flagged for metadata review
- any rows requiring manual follow-up

Make clear that the workbook is a review artifact and that the user should verify possible hallucinations, publication-status updates, and contested metadata before changing the paper bibliography.

If the user wants to invoke this skill explicitly, use `$ref-check`.
