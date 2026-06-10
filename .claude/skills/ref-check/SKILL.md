---
name: ref-check
description: Audit references in LaTeX or Overleaf-style papers by compiling the manuscript, using the compiled bibliography as the source of truth, briefing the user before driving their own browser session, checking linked references against actual source pages, handling human-verification gates conservatively, and producing a color-coded Excel review workbook that marks possible link, metadata, and hallucination issues for user verification. Use when the user asks for reference checking, bibliography verification, DOI or URL validation, source-by-source citation auditing, or a staged reference review workflow.
---

# Ref Check

Use this skill for serious bibliography audits where the user wants a compiled-paper-first workflow and a reviewable spreadsheet artifact.

This skill is conservative by design. It helps the user inspect what the paper cites and how those citations compare with source pages. It does not silently finalize ambiguous references or overstate what the model has verified.

This skill operates the user's own browser. That is deliberate: institutional access, cookies, and login state matter for reaching real source pages. Because of this, the skill must keep the user informed and involved. Step 0 exists for exactly that reason and must never be skipped.

<!-- BEGIN OPERATING CONTRACT -->
## Operating Contract

These rules apply before and during every phase of this skill. They override convenience and speed.

1. **Role.** You are a careful research associate working for a professor. You clean, maintain, and administer research workflows. You have no margin to hallucinate and no authority to perform operations outside the stated scope of work.
2. **Evidence.** Assert only what you have verified from files inside the working folder. If a claim cannot be verified from the folder, say "Not verifiable from the project folder" and stop that line of work until the user resolves it.
3. **Vague scope.** If the request is ambiguous or underspecified, ask clarifying questions first, restate the scope of work in your own words, and proceed only after the user confirms.
4. **Folder scope.** All file reads and writes happen inside the folder this skill was invoked from. Decisions about the project come only from evidence in that folder. Do not use prior model knowledge of the paper, the dataset, or the literature to fill evidence gaps. External web pages may be consulted only when a skill step explicitly requires it, and only as material for user review.
5. **Approval before irreversible actions.** Never modify, delete, or overwrite a user file before the user has approved the specific plan that requires it.
6. **Style.** Generated artifacts must not contain em-dashes. Use commas, periods, or restructuring instead.
<!-- END OPERATING CONTRACT -->

## What This Skill Does

- Compiles the paper first and treats the compiled bibliography as the source of truth for what the paper currently cites.
- Briefs the user on the browser operations before opening a single page.
- Uses the user's browser session to inspect actual DOI and URL targets.
- Separates linked-reference verification from missing-link discovery.
- Produces an Excel workbook that preserves paper order and adds review columns instead of replacing the original citation text.
- Flags incorrect links, metadata issues, possible hallucinations, and rows that still need human review.

## What This Skill Does Not Do

- It does not verify a reference from search-result snippets alone.
- It does not silently resolve ambiguous cross-site matches.
- It does not assume a working paper should be replaced without checking whether the user wants the later journal version noted.
- It does not treat access restrictions or bot checks as evidence that a reference is false.
- It does not edit the `.bib` file or the paper. The workbook is the deliverable; the user decides what to change.

## Non-Negotiable Rules

1. Use the compiled bibliography, not the raw `.bib`, as the source of truth for `Original paper reference`.
2. Do not mark a reference as verified from search-result snippets alone. Verify from the actual source page.
3. Use the user's browser session for source-page checks, because access, cookies, and click-through gates matter.
4. If the browser shows a human-verification gate, pause and ask the user to click through.
5. Keep direct source-page verification separate from broader discovery work.
6. If a match is ambiguous, keep it flagged for the user instead of making a strong claim.

## Required Files

Before starting, confirm the following are present in the working folder, meaning the folder the skill was invoked from. If any required item is missing, halt and ask the user to provide it before continuing.

| File | Required for | What to do if missing |
|:---|:---|:---|
| Paper `.tex` source file | Step 1 compile and reference extraction | Halt. Cannot proceed without the source. Ask the user to provide it. |
| `.bib` file(s) referenced by the paper | Step 1 compile | Halt. Compilation will fail without the bibliography source. Ask the user to locate or provide them. |
| Bibliography style file(s) (`.bst`, `.sty`) | Step 1 compile | Attempt compile. If it fails due to missing style files, report the error, halt, and ask the user to provide them. |
| Working LaTeX installation with `xelatex` or `pdflatex` | Step 1 compile | Halt. Report that LaTeX is not available and the skill cannot run Step 1. |
| Browser session access | Steps 3 through 5 source-page verification | Do not halt yet. Step 0 handles the check and the guidance. |

If Step 1 compilation fails for any reason, do not attempt to extract references from a partial or broken output. Report the exact LaTeX error, halt, and ask the user to resolve the compile issue before continuing.

## Step 0: User Briefing and Browser Pre-Flight

Do this before compiling anything and before opening any web page.

### Tell the user what is about to happen

Explain, in plain terms:

- This skill will operate their own browser to open DOI and URL targets, one reference at a time.
- Roughly how many references the paper appears to have, and therefore roughly how many pages will be opened, in batches.
- The browser will visibly navigate. They should not close tabs the skill opens until told the queue is stable.
- They will be asked to click through human-verification gates ("Just a moment...", "Verify you are human") when those appear. The skill cannot and should not bypass these itself.
- At handoff, unresolved tabs stay open so they can inspect them.

### Verify browser tooling is connected

- In Claude Code, confirm the Claude in Chrome extension is connected and a browser is reachable before proceeding. If it is not, halt and walk the user through connecting it.
- In Codex, confirm the browser tool is available in this session. If it is not, halt and report what is missing.
- If browser tooling is unavailable and cannot be enabled, tell the user that linked-reference checking will be skipped, mark all linked rows as `Needs source check`, and continue only with the non-browser parts of the workflow after the user agrees.

### Confirm access prerequisites with the user

Ask the user to confirm, before the first page is opened:

1. Their VPN or institutional proxy is active if the paper cites paywalled journal sources.
2. They are logged into publisher sites they normally use through the library or directly.
3. They are comfortable with the skill driving the browser for this session, and roughly how long the batch may take.

### Collect the remaining inputs

1. The preferred workbook output path inside the working folder, if they have one.
2. Whether the paper has appendices or split bibliographies that must be checked separately.
3. Whether working-paper rows should be checked for later journal versions.

Get an explicit go-ahead. Then run the Required Files check and begin Step 1.

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

## Step 2: Build the Workbook Skeleton

Create a workbook that preserves the paper order exactly. Follow `references/workbook-schema.md` in this skill folder for the full column and color conventions.

Core visible columns:

- `Original paper reference`
- `Reference from DOI/Link`
- `Incorrect DOI or Link`

Hidden helper columns are allowed: citation key, section, current DOI or URL.

Column A records what the paper currently says. Column B records what the source page says. Column C is used when the existing DOI or URL is incorrect.

## Step 3: Phase 1, Linked References Only

For rows that already have a DOI or URL:

1. Open the DOI or URL in the user's browser session.
2. Read the actual source page.
3. Write the source reference, in the paper's citation style, into `Reference from DOI/Link`.
4. If the DOI or URL is wrong, write `Incorrect DOI or Link` in column C.

Work in batches and tell the user when each batch starts and finishes. Do not search for missing links in Phase 1. First finish the rows that already point somewhere.

## Step 4: Human-Verification Handling

If the browser lands on a page such as `Just a moment...`, `Are you a robot?`, or `Verify you are human`:

1. Stop on that reference.
2. Ask the user to click through.
3. Continue only after the real source page is readable.

If many such pages appear, keep one browser tab per unresolved reference and hand the user a short, explicit queue: which tabs, which references, what to do.

## Step 5: Phase 2, Missing Links and Failed Linked Cases

Only after Phase 1 is stable:

1. Work the rows with no DOI or URL.
2. Revisit incorrect DOI or URL rows.
3. Revisit linked rows where column B is still blank.

Search order:

1. same journal site
2. same publisher site
3. same domain family
4. broader discovery only with user awareness

If the corrected source is on the same journal or publisher site and clearly matches, it can be used. If the corrected source is cross-site, ambiguous, or only partially matches:

- keep the row flagged
- keep the tab open if helpful
- show the candidate to the user
- wait for approval before treating it as the likely source

## Step 6: Hallucination Rule

Use `hallucinated` only after conservative checking fails.

Do not mark an entry hallucinated just because:

- the local citation key is broken
- the DOI redirects oddly
- the source is access-restricted
- the paper cites an older working-paper version that may since have been published

Mark `hallucinated` only when journal-first and broader guided checking still fail to find a matching referenced work.

## Workbook Review Layer

After the source-collection pass, add review columns so the workbook becomes a decision tool. Use the columns, status values, and color conventions defined in `references/workbook-schema.md`.

The workbook should make it easy for the user to inspect:

- whether a possible hallucinated entry is truly unsupported
- whether a working paper appears to have a later journal version
- whether volume, issue, page, article number, year, venue, or DOI metadata looks wrong or outdated
- which rows still need a manual judgment call

Interpretation rules:

- `Not present` is different from `Unchecked`.
- Books and reports may legitimately lack volume, pages, or DOI.
- The user remains the final verifier for ambiguous metadata changes.

## Browser Rules

- Use the user's browser session, not anonymous search alone, when institutional access or cookies may matter.
- Use search only to find a candidate source page, never as the final verification artifact.
- Keep unresolved tabs open at handoff time if the user still needs to inspect them.
- Close duplicate probe tabs once the queue is stable.
- Never enter credentials, complete logins, or click through verification gates on the user's behalf. Hand those to the user.

## Good Final Reporting

Summarize:

- workbook path
- linked references completed
- incorrect DOI or URL count
- no-link count remaining or resolved
- rows flagged for metadata review
- any rows that may be hallucinated
- any rows where a working paper may have a later journal version
- which tabs remain open and what the user should do with each

Make clear that the workbook is a review aid and that the user remains the final verifier for ambiguous or substantive citation updates.

## Invocation

- Claude: invoke with `/ref-check` or by asking for a reference audit while this skill is installed.
- Codex: invoke with `$ref-check`.
