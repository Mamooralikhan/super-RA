# Work Log

Running log of structural work on this repository. Newest entry first. Each entry records what changed, why, the decisions taken, and what remains open, so work can be resumed without re-deriving context.

Conventions: dates are absolute (YYYY-MM-DD). Decisions are numbered per entry so later entries can reference them, for example D2026-06-10.3.

---

## 2026-07-12: super-RA gets a brain, and ref-check stops silently under-checking multi-file papers

### Problem addressed

**super-RA had no brain.** There was no `CLAUDE.md` and no `settings.json` anywhere in the repository. The only governance was the six-point Operating Contract embedded in each `SKILL.md`, which loads only *after* a skill is invoked and claims authority over nothing else. super-RA was a library of three skills, not an operating identity. Installing it into a research project changed how three commands behaved; it did not change how the assistant worked.

The intent was always the opposite: you install super-RA into a project, and in that project **Claude becomes the super-RA**, governed by super-RA's rules rather than by whatever personal preferences the person happens to carry around.

**And `ref-check` had a silent hole.** The extractor read exactly one `.tex` file and never followed `\input` or `\include`. On a paper split across `sections/*.tex`, which is the norm in economics, every citation in a child file was invisible. It did not error and it did not warn. It reported fewer references, and every assertion still passed, because a citation the parser never saw cannot be flagged as missing from the `.bib`. The run looked clean and the report looked confident.

### What changed

- **Added the brain.** `brain/CLAUDE.md` is the canonical constitution: role, approval discipline, evidence rules, the sourcing register, pipeline-before-code, the statistical-test gate, attribution, and style. `brain/settings.json` is the enforcement layer. `brain/hooks/super_ra_notice.sh` tells the user at session start that super-RA has taken over.
- **The brain changes how Claude answers, not only what it may do.** Every claim shows its source, and the source is a clickable link: a file and line for the project, the paper itself for the literature. A claim with no source says so in plain words. Looking things up is a read, so it checks rather than guessing.
- **Added `scripts/install_super_ra.sh`.** Installs the brain and the skills into a target research project. On collision it refuses and reports, and changes nothing.
- **The repository now governs itself.** `CLAUDE.md` at the root embeds the brain block verbatim, plus a maintainer appendix. super-RA holds itself to the contract it ships.
- **Operating Contract clause 7, Precedence.** Carries the takeover into a skill invoked in a folder super-RA does not govern. Re-embedded verbatim in all three skills.
- **`ref-check` Step 0 now establishes its inputs.** It lists the `.tex` and `.bib` files it found, identifies the main file, reads the bibliography name out of the paper rather than off the file listing, and asks the user to confirm before touching a reference.
- **Extraction Rule 8.** `01_extract_citations.py` now resolves `\input`, `\include` and `\subfile` recursively, accepts multiple `.bib` files, prints every file it read with the citations each contributed, and halts on a live child it cannot find on disk.
- **Extraction Rule 9,** found by the pilot on a real second paper. The appendix was located by taking the first line starting with `\appendix`. On a paper that defines `\newcommand*\appendixwithtoc{ \appendix ... }` in the preamble, that lands inside the macro body: the preamble becomes "the body" and the whole document becomes "the appendix". It reported **all 35 references as appendix-only and zero in the body**, cleanly and without a warning. Now: find `\begin{document}` first, look for `\appendix` only after it, and match on a word boundary so `\appendixwithtoc` does not.
- **Extraction Rule 10,** prompted by a user report that an earlier version of the skill read `\cite` but not `\citep`. That specific bug was already gone, but testing the claim rather than trusting the code exposed a larger one: **14 of 24 real citation commands were invisible.** The regex named eight natbib commands, so it could not see natbib's capitalised sentence-start forms (`\Citep`, `\Citet`), the whole of biblatex (`\parencite`, `\textcite`, `\autocite`, `\footcite`, `\supercite`, `\fullcite`), apacite (`\citeA`, `\shortcite`, `\citeN`), or `\nocite{key}`, which prints. A paper mixing `\citep` with `\textcite` lost every `\textcite` silently. The extractor now matches **any** macro whose name contains "cite", collects its keys, and reports commands it does not recognise. It also prints a census of the citation commands the paper actually uses.
- **The PI gate.** `05_pi_review.py` now hard-fails before rendering unless the PI has spot-checked at least 10% of the references in person, has personally verified every entry any tier called `critical`, and has populated the ground-truth lists. No escape flag.
- **The integrity proof now covers every source file.** `06_render.py` used to re-check the byte size of the main `.tex` and the `.bib` only. It now checks every file step 01 read, including each `\input` child.
- **Validator gained four checks** (brain block identical, `settings.json` still guarantees supersession, the hook parses and is executable, README covers the brain) and extended the em-dash gate over `CLAUDE.md` and `brain/`.
- **Fixed two stale Codex-era lines in the README** that the validator could not catch, because check 6 greps for functional Codex references and not for prose. The README still claimed the validator "enforces that this contract stays identical across every skill on both platforms" and still told contributors to "preserve platform parity".

### Decisions

**D2026-07-12b.1. Supersession is enforced, not requested, and it was proven before it was built.**
By default Claude Code *concatenates* every instruction file it finds: "All discovered files are concatenated into context rather than overriding each other." A project brain alone would sit *underneath* the user's personal rules, not replace them. `claudeMdExcludes` is what actually unloads `~/.claude/CLAUDE.md`, and it can be set at the project layer.

This was verified empirically before a line of the brain was written, because the entire design rested on it. Two throwaway projects, identical except for that one setting, were each given a headless session and asked what they had loaded. The control named `~/.claude/CLAUDE.md` and could quote a word found only in it. The treatment could not see it at all, and still carried the project brain. The control is the point: without it, "the global file did not load" would have been worthless, since it might never load in a headless session anyway.

**D2026-07-12b.2. The brain is a superset, not a summary.**
Excluding a person's global `CLAUDE.md` means *everything* in it stops loading. A six-point brain would therefore leave a governed project with no sourcing discipline, no approval protocol, and no attribution rule, having deleted the file that supplied them. A brain that loosens the user's own safeguards is a downgrade wearing the clothes of an upgrade, so the brain carries the full constitution and states explicitly that a *stricter* rule from elsewhere still applies.

**D2026-07-12b.3. The brain lives at the project root, and this is not cosmetic.**
The exclusion glob is `**/.claude/CLAUDE.md`. A brain placed under `.claude/` would match its own exclusion rule, remove itself from context, and leave the project governed by nothing at all while still appearing to be governed by super-RA. That is the worst available outcome: the user believes they are protected and they are not. The root placement is load-bearing and is documented as such in three places.

**D2026-07-12b.4. Judgement goes in `CLAUDE.md`; prohibitions go in `settings.json`.**
The documentation is explicit that settings are enforced by the client while `CLAUDE.md` is only context. So the approval discipline and the sourcing register, which an agent must *reason with*, live in the brain; and the things that must simply never happen (git commits, `rm -rf`) live in `permissions.deny`, because a rule an agent can reason its way past is not a rule.

**D2026-07-12b.5. The installer refuses on collision. It does not back up and it does not merge.**
A research project's existing `CLAUDE.md` is somebody's work and may be load-bearing. Overwriting it is obviously wrong. Silently renaming it to `.pre-super-RA` and swapping the project's behaviour out from under its owner is *also* wrong, and is precisely the class of surprise the Operating Contract exists to prevent. Merging by importing their file underneath the brain is worst of all, because it re-admits the rules the brain was installed to supersede. So: report what was found, change nothing, let the human decide.

**D2026-07-12b.6. Clickable sources, not an epistemic notation.**
The brain first shipped the maintainer's personal notation (`***` grounded, `[ ]` inference, `[unverified]`). It was cut. super-RA is public, and a notation is a key the reader has to be taught before the output means anything; a stranger who installs this will not learn one. It was replaced with something that needs no explanation at all: **every claim carries a clickable source.** A file and line for a claim about the project, the paper itself for a claim from the literature, and for a claim with no source, plain words saying so, inside the sentence.

This makes the anti-fabrication rule sharper rather than softer, and the danger is worth naming: **asking a language model for references is the most reliable way to make it invent them,** and a fabricated link is worse than a fabricated bracket because it *looks* authoritative. So the brain carries `ref-check`'s own rule verbatim in spirit: every URL must be one that actually came back from a tool call. Never construct a DOI from a pattern. Never assemble a publisher URL because it ought to work. super-RA ships a skill built to catch invented citations, and it must not become the thing it was built to catch.

To make that workable, **verification is a read and needs no approval.** Reading a file and looking a source up are both reads. Writes, edits, commands, and deletions are still asked for. Without this, every sourced claim would cost an approval round trip and the register would be abandoned in practice.

**Verified with an A/B run**, same question, two folders differing only in the brain. Default Claude answered "roughly 40%" from memory as a headline. super-RA led with the fact that no single figure exists for the field, scoped the claim to lab experiments, gave the caveats, went and looked, and returned a real resolving DOI.

**D2026-07-12b.7. Extraction Rule 8 runs LAST, and the ordering was verified in both directions.**
The obvious implementation resolves `\input` first and is wrong twice over. The reference paper proves both failures:

- It `\input`s about fifteen table files *after* `\end{document}`. Expanding before truncating drags the whole dead zone back in through the side door, defeating Rule 2 entirely.
- It carries three *commented-out* `\input` lines whose targets do not exist on disk (`main.tex` lines 149, 980, 1041). Resolving children before stripping comments halts the pipeline on three files TeX itself never reads. A false halt is the same disease as a false accusation.

The correct order is truncate, then strip comments, then resolve children. It was tested both ways: the identical `\input` line is harmless when commented and a hard halt when live.

**D2026-07-12b.8. A missing child halts the run. It is never skipped with a warning.**
An `\input` pointing at a file that is not there is an unknown number of unchecked citations. This pipeline does not proceed on an unknown, and the whole reason Rule 8 exists is that *quietly checking less than you claimed to* is the failure mode that does the most damage.

**D2026-07-12b.9. The file list is printed, and that is a safety feature.**
Every `.tex` read is printed with the citation count it contributed. A user who knows their paper is split across ten files, and sees one file listed, catches the fault instantly. If the extractor says nothing, nobody can. On the reference paper the new extractor reads 19 files where the old one read 1.

### Verification

- Supersession proven with a control and a treatment (D2026-07-12b.1).
- `ref-check` regression on the reference paper: **66 cited (117 occurrences), 109 uncited of 175, 0 cited-but-missing, 0 dead-zone keys, 10 duplicate keys**, unchanged from before Rule 8, while now reading 19 `.tex` files instead of 1. Every child on that paper happens to carry zero citations, which is exactly why the old extractor got away with it.
- Purpose-built multi-file fixture: a main file plus three children citing four distinct works, one child `\input` from the dead zone, one commented-out `\input` to a nonexistent file. The old extractor would report **1** reference. The new one reports **4**, ignores the dead-zone child, does not halt on the commented one, and halts correctly when that same line is uncommented.
- Validator passes. All six pipeline templates compile. Operating Contract identical across the canonical copy and all three skills. Brain block identical across `brain/CLAUDE.md` and `CLAUDE.md`.

**D2026-07-12b.10. Rule 10 is a blind-spot detector, not a longer list.**
The obvious response to "you missed `\textcite`" is to add `\textcite` to the regex. That is the wrong fix, because it is the fix you make again on the next package, and the failure it patches is silent: a citation command the extractor does not know contributes nothing and *says* nothing.

So the extractor now matches **any** macro whose name contains "cite", takes its keys, and **names** the ones it does not recognise. Missing a citation command is structurally impossible. The worst case is over-collection, where some unrelated macro's argument enters the key list, and Rule 7 catches that instantly by finding a "key" that is not in the `.bib`.

That asymmetry is the whole argument, and it generalises well beyond this file: **over-collecting fails noisily, under-collecting fails silently.** When forced to guess, guess toward the noisy failure.

Both real papers reproduce identical numbers under the new scanner, which is the point: it widens what *can* be seen without changing what *is* seen.

**D2026-07-12b.11. The PI gate. A check that cannot fail is worse than no check.**
The regression suite shipped with both ground-truth lists empty, because they are per-paper, so on a fresh run it iterated over nothing and passed. It could not fail. That is worse than having no suite at all: a decoration that makes you feel checked is a reason to stop looking.

The fix was not to invent ground truth. The PI is **already required** to spot-check a sample by hand, and those spot-checks *are* the ground truth; the two things were sitting in the same file ignoring each other. Step 05 now refuses to render until the PI has re-fetched at least 10% in person, has personally verified every entry any tier called `critical` (the file asked for this in a comment and enforced nothing), and has populated both lists.

No escape flag, deliberately: a flag to skip it becomes the default path within two runs. `GROUND_TRUTH_DEFECTS` may legitimately be empty on a paper where nothing is wrong; it may not be empty on a paper where something was found. Tested across five scenarios, including a clean paper, which must and does pass.

### Verified in the pilot

A second, unrelated paper (a field experiment, ~200k of `.tex`, a 2,035-entry Zotero `.bib`) was run through extraction cold. It earned its keep immediately:

- **Rule 9 was found here**, and only here. The reference paper does not define an appendix macro, so the bug was invisible on it.
- **Rule 1 at full stretch:** the `.bib` holds 1,875 unique entries and the paper cites **35**. Verifying the whole file would be 54 times the work for zero effect on the submitted document.
- **Rule 8 at full stretch:** 72 `.tex` files resolved (71 children), zero unresolved.
- **Step 0 was necessary, not ceremonial.** The folder holds `main_new.tex`, `main_old.tex`, `extra_tables.tex` and more in `archive/`, and **`main_old.tex` also carries a `\documentclass`**. An agent that picks the first plausible `.tex` audits the wrong paper. The user had to be asked, and was.

---

## 2026-07-12: the first cold end-to-end run of /ref-check, and what it broke

`/ref-check` was driven cold, all three tiers, on a real second paper (a field experiment on voting; `main_new.tex`, 35 printing references drawn from a 1,875-entry `.bib`). It had never been done. Everything below is a defect the run exposed. None of them would have been found by reading the code.

### What the run found in the paper

35 references verified. **1 critical, 4 major, 4 decisions, 1 minor, 25 clean.** All 73 source files byte-for-byte unchanged, verified rather than asserted.

The critical one, `norms2023covid`, is the same shape as the World Bank finding on the first paper: the entry **fuses two different real records.** It gives the NBER working paper's exact title, the journal EDCC as the venue, and the year 2023. The PI checked both records at Crossref personally. NBER w28651 carries that title but is dated 2021 and never appeared in EDCC. The real EDCC article, by the same six authors, is titled *"Correcting Misperceptions about Support for Social Distancing to Combat COVID-19"* and printed in 2024, 73(1), 221-242. **The combination as cited exists nowhere.** A compile would never reveal it.

### The defects the run exposed in the skill itself

**D2026-07-12c.1. THE REGRESSION SUITE CAUGHT A LIVE FALSE ALARM, AND IT WOULD HAVE SHIPPED.**
This is the finding that justifies the whole day. The Associate's natural phrasing for "this entry is fine" is *"No discrepancy: all fields match the Crossref record exactly."* That sentence contains no phrase from `POSITIVE_CONFIRMATION`, so the classifier read it as a **substantive finding** and promoted **five entries the PI had personally confirmed as correct** to `major`.

It is the D5 negation bug again, in words nobody anticipated. And the suite that caught it **could not have caught it yesterday**: it shipped with empty ground-truth lists and passed vacuously. The gate added this morning is what turned a decoration into a check, and the check fired on its first live run and stopped the report.

The fix adds `"no discrepancy"` and four siblings to the exclusion list. Note what is deliberately **not** added: a bare `"is correct as"` would look like a sensible catch-all and would be a disaster, because `gottlieb2016men`'s finding reads *"the year is correct as the article's ONLINE-FIRST date, BUT the pagination is print-only"*, which is a real defect. **Match the affirmation, never the adjective.**

**D2026-07-12c.2. Do not restate the subagent's output schema in the prompt. Point at the contract.**
The prompt said "read your contract and follow it exactly", then helpfully restated the schema in its own words. The two disagreed. The subagent followed the prompt, because the prompt was nearer. Eighteen references were fetched perfectly and written in a shape nothing downstream could read. Nobody hallucinated and nobody disobeyed: **a second copy of a spec is a spec that will drift**, and when it drifts, the copy closest to the agent wins.

**D2026-07-12c.3. An LLM subagent will not reliably hit an exact JSON shape, however clearly you specify it. Normalise on read.**
Both Associate contracts say "Write your JSON array." Two subagents, identical prompt, identical contract: one wrote a bare array, the other wrapped it in `{"entries": [...]}`, mirroring its input file. A third divergence nested every added field under an `"associate": {...}` sub-object. None of this is disobedience; it is two defensible readings of one sentence, and it is the same independence that makes the Associate tier worth having.

So the consumers now normalise: **be liberal in what you accept, strict in what you validate.** The wrapper carries no meaning, and every check that matters runs on the entries either way.

**D2026-07-12c.4. Overlay, do not trust.** Step 04 was rebuilding each record from whatever the Associate echoed back. One subagent dropped the `assistant` sub-record while reshaping, at which point the unclicked gate read a missing `not_found` as False and **falsely accused `bhavnani08` of reaching the PI unclicked**, when it was correctly recorded as `no_link`. A false accusation manufactured by a schema mismatch is precisely the disease this pipeline exists to cure. Step 04 now takes step 03's record as authoritative and overlays only the fields the Associate actually owns.

**D2026-07-12c.5. The batch count lived in two places.** `02_make_batches.py` had `N_BATCHES`; `03_collect_assistant.py` hardcoded `range(1, 5)` and `04` hardcoded `(1, 2)`, both assuming the 66-reference paper. Adapting one for a 35-reference paper left the others hunting for files that were never meant to exist. Both now discover the batches on disk. One purpose, one place.

**D2026-07-12c.6. The report byline is a fixed super-RA mark, not a name to ask for.**
`06_render.py` used to take `--author` as a required argument and die without it. That was the right fix for the wrong problem. The real failure was a byline with a hole in it, and **a fixed mark cannot have one.** Every report now carries super-RA, its creator Mamoor Ali Khan (mamooralikhan.com), the repository, and a plain disclosure that Claude Code executed the run. The three roles are named separately because that is what is true: super-RA supplies the method, Claude Code executes, and **the author of the paper decides.** A tool mark must never read as authorship over someone else's bibliography.

**D2026-07-12c.7. The report prints in the PAPER'S bibliography style, and we reimplement nothing.**
The report rendered citations in a house format we invented: every author inverted, the year in parentheses. No journal prints that. An author had to translate the report back into their own bibliography before they could act on it, and a "corrected" line they cannot recognise is a line they will not trust.

The obvious fix is to hand-write an AER formatter, then an APSR one, then Chicago. That is the wrong move, and it gets worse with each style added: **a hand-rolled formatter that is subtly wrong makes a correct entry look wrong**, which is exactly the disease this pipeline exists to cure.

So nothing is reimplemented. `01` reads `\bibliographystyle{...}` out of the paper, and `bst_render.py` drives **BibTeX itself** over the author's real `.bst`. No LaTeX compile is needed: BibTeX wants only a synthetic `.aux` naming the style, the data, and the keys. `aer.bst` produces AER, `apsr.bst` produces APSR, and we support every style the user has installed by supporting none of them ourselves. Where BibTeX is absent, the report falls back to the generic format **and says so**, so the promise that `ref-check` needs no LaTeX install still holds.

**D2026-07-12c.8. Every reference must be rendered in its OWN BibTeX run.**
Two runs (one per column) were not enough, and finding out why was the whole lesson. **A bibliography style formats each entry in the light of its neighbours.** That is correct for a bibliography and poison for a report:

- **`\bysame`.** When consecutive entries share a leading author the style suppresses the repeated name. `jayachandran2015genderroots` sorted immediately before `jayachandranvoena2026`, so the latter rendered as **"and Alessandra Voena"**, with "Jayachandran, Seema" simply gone. Splitting the columns did not help, because two *different* references can share a first author.
- **Year disambiguation.** Two entries by the same authors in the same year become `2016a` and `2016b`, inventing a suffix the paper does not print.

Both artifacts are the style file behaving **correctly**. The principle underneath: **in a bibliography a row is read in the context of its neighbours; in a report, every row is read alone, so every row must be formatted alone.** One entry, one run, no neighbours. It costs milliseconds and buys a guarantee instead of a hope.

A third bug fell out of the same work: `_parse_bbl` used `[^{}]*` to match `\harvarditem`'s label group, which cannot cross a nested brace, so **any entry with an accent in an author name silently vanished from the report** while every unaccented entry rendered fine. The same disease again, in a new file.

**D2026-07-12c.9. A degraded output must be announced BEFORE the work, not discovered after it.**
The report falls back to a generic citation format when it cannot use the paper's own style: the paper is biblatex (no `\bibliographystyle` exists at all), or names a `.bst` the machine does not have, or BibTeX is not installed. The first version simply did it, and mentioned it in the finished report.

That is the wrong order. **A fallback the user was never given a chance to prevent is a fallback they will rightly resent.** Finding out at the end, after sixty web fetches, leaves two bad options: accept it, or redo the whole run.

So step 01 now runs a **preflight** and says so up front, before a single reference is fetched. It costs one `which bibtex` and one `kpsewhich`; there was never an excuse for learning it late. It states three things, and the third is what makes it worth printing:

1. what will happen (generic format),
2. what it does **not** affect (not one finding; every error is still found and every link still checked; only the typesetting changes),
3. **what the user can do**, with the remedies spelled out, and the crucial reassurance that **any of them needs only step 06 re-run. No reference is re-fetched and nothing is lost.**

`06_render.py` gained `--style` so taking a remedy is one flag, not a new run. The report also prints the fallback notice in amber above the table, so a reader cannot mistake a generic rendering for how their paper actually prints, and then read a formatting difference as a data error.

The general rule, and it outlives this file: **when the tool is about to do something less than it promised, say so while the user can still choose.**

### Open

- CI running `scripts/validate_skills.sh` on every push.
- Whether `replication-repo` and `script-provenance` should adopt the `references/pipeline/` pattern and ship runnable code rather than prose.
- The Assistant and Associate tiers have now been run on two papers. Batch sizing has not been tested on a very large bibliography (200+ printing references).
- `bst_render.py` is exercised on `aer`, `apsr`, `chicago` and `plainnat`. A biblatex paper is **detected** and announced, and the user can supply a close BibTeX equivalent with `--style`, but biblatex's own styles are not rendered natively (that would need biber). Numeric styles are untested.

---

## 2026-07-12: Codex support removed, and ref-check rewritten as a three-tier verification pipeline

### Problem addressed

Two problems, one entry, because the second forced the first.

**ref-check did not work well enough.** The old skill compiled the paper, drove the user's browser page by page, and produced an Excel workbook. It depended on a working LaTeX install, an active VPN, publisher logins, and the user personally clicking through bot checks. It was slow, it needed babysitting, and it verified a reference by looking at whatever page the browser landed on.

The rewrite was built and proven on a real paper before it was ported here. On a 66-reference economics paper it found three critical errors that a compile-and-eyeball pass would never surface: a World Bank citation whose own URL serves a report about a different country, an entry that fused three different real papers into one, and a citation to a work that does not exist under the authors given. It needed no browser, no VPN, and no LaTeX.

**Codex could not run it.** The new method depends on subagents. The Assistant fetches, and a separate Associate, with its own context, re-clicks every link and checks the Assistant's work. That independence is the entire anti-hallucination mechanism, and on the real run the Associate corrected the Assistant on 15 of 66 entries, two of which were cases where the Assistant had wrongly accused a bibliography that was actually correct. A single agent reviewing its own output is not an independent check, so a degraded Codex variant would have been a worse skill wearing the same name.

### What changed

- **Removed Codex entirely.** Deleted `codex-skills/` and `scripts/install_codex_skills.sh`. This repository is Claude only.
- **Rewrote `scripts/validate_skills.sh`.** Dropped the platform-parity check, which existed only to compare the two copies of each skill and has nothing left to compare. Added a check that Codex stays removed, and a check that every shipped pipeline template compiles. Kept every rule that still means something: required files, frontmatter, the Operating Contract verbatim, no em-dashes, no `ref-audit`, README coverage.
- **Rewrote `ref-check`.** Three tiers: an Assistant that only fetches, from a closed source universe; an Associate that trusts nothing and re-clicks every link; a PI, run by the main agent and never delegated, that rules on author order, currency, and institutional authorship.
- **Retired the Excel workbook.** Deleted `references/workbook-schema.md`. The deliverable is now two HTML reports, rendered by one script from one JSON so they cannot disagree with each other.
- **Shipped the pipeline as working templates** under `references/pipeline/`, not as prose. The extraction guards are the real asset and they must not be re-derived from scratch on each run.
- **Removed the Codex invocation line** from `replication-repo` and `script-provenance`. Nothing else in those two skills was touched.

### Decisions

1. **The extraction rules ship as code, not as advice.** Four of the seven guards in `01_extract_citations.py` were discovered only after the pipeline had already produced a confident, well-formatted, entirely wrong finding about a specific reference. Truncating at `\end{document}`, first-wins duplicate keys, a brace-aware field parser, and splitting on a leading-whitespace `@` are not stylistic preferences. Each one, when absent, caused the pipeline to invent a defect in a bibliography that was correct. Prose would let the next agent re-derive them badly. `references/extraction-rules.md` records why each exists.

2. **Report, never fix.** No script writes to the `.tex` or the `.bib`, and no corrected `.bib` is emitted. A citation decision belongs to the author: which version of a working paper to cite, whether a 1971 revised edition is the one they read. Step 01 records the byte sizes of both source files and step 06 re-checks them, so the claim is verified rather than asserted.

3. **A published version of a working paper is reported, never applied.** Changing the year rewrites every in-text `\citep{}`. The pipeline surfaces it as a decision for the author.

4. **Absent from Crossref is not the same as does not exist.** On the real run, both machine tiers flagged a 1971 Olson edition as a wrong year because Crossref registers only 1965 and 2009. The 1971 revised Harvard edition is real; Crossref's coverage of pre-digital books is simply poor. The PI tier exists to overrule that class of confident machine error, and the skill says so explicitly.

5. **Any prose-reading classifier has a negation bug.** The phrase that flags a problem also occurs in the sentence saying there is none. The first version read "Year is CORRECT as given" as a defect and promoted 18 correct entries to "major". `05_pi_review.py` therefore pairs every positive trigger with an exclusion list checked first, and carries a ground-truth regression suite that runs on every invocation.

6. **No scroll container in the reports.** The first build trapped the table in a `max-height` pane. The reader's verdict was that it made the report unreadable: you scroll the page and nothing moves, you scroll the pane and lose your place. The page scrolls, and exactly one element is sticky.

7. **Reports are signed, and the byline is not optional.** `06_render.py` takes `--author` as a **required** argument and exits if it is empty. This is a direct response to a real failure: a report was shipped to co-authors crediting nobody, because the author's name was not to hand and the missing element was quietly dropped instead of being asked for. A partial byline is a failure, not a graceful degradation.

### Open items

- [ ] The `GROUND_TRUTH_DEFECTS` and `GROUND_TRUTH_CORRECT` lists in `05_pi_review.py` ship empty by design, since they are per-paper. Watch whether agents actually populate them, or whether the regression suite quietly degrades into a no-op that always passes.
- [ ] The `references/pipeline/` pattern (shipping runnable templates, not just docs) is now the strongest form of a skill in this repository. Decide whether `replication-repo` and `script-provenance` should adopt it.
- [ ] The CI item below is now more valuable, because the validator compiles the pipeline templates and can catch a broken template on push.

---

## 2026-06-17: New skill script-provenance

### Problem addressed

On multi-member projects, two recurring pains block reproducible coding. First, paths: every `.do`, `.R`, or `.py` file has to be edited at the top to match each person's machine, worst of all when the project lives in a Box or Dropbox mount whose absolute prefix differs per user. Second, package drift: code written under one package version silently produces different results after an update, and teams have no shared record of who is on which version.

### Approach

Added a third skill, `script-provenance`, on the same contract and parity rules as the existing two. It standardizes scripts and installs a cross-team version provenance system.

- **Paths.** File-anchored, not the `here` package. The script's own location is the origin; climbing up uses `..` segments; every other path is built downward from `ROOT`. Clean in Python (`__file__`) and R (`this.path`, the one dependency, deliberately not `here`). Stata cannot self-locate a do-file, so it anchors through a `.provenance/.projroot` marker plus one editable root line, stated honestly rather than faked.
- **Header.** Author, purpose, created and updated dates, inputs, outputs. Author is never invented; purpose on a retrofit is inferred then confirmed.
- **Version provenance.** Three layers. A baseline of blessed versions. A per-member ledger, one TSV file per member so shared folders never conflict. An offline in-script check that warns only when a version changed since the member's last run or differs from baseline, and points to reconcile. Plus a restoration layer (renv or groundhog, uv or pinned requirements, vendored ado) as the cure. An on-demand `reconcile` builds a package-by-member table and, with one optional network call, flags who is behind the latest release.

### Files

- `.claude/skills/script-provenance/SKILL.md` and `codex-skills/script-provenance/SKILL.md` (byte-identical), with `references/templates.md` and `references/provenance-system.md` mirrored on both platforms.
- `codex-skills/script-provenance/agents/openai.yaml`.
- `scripts/validate_skills.sh`: added `script-provenance` to the skills list, required-file checks for both reference files on both platforms, and a parity `cmp` for the references.
- `README.md`: table row, full Skill Guide section, repository layout, date.

### Decisions

1. **File-anchored paths, not `here`.** The maintainer's stated method anchors to the script and climbs with `..`. Stock `here` anchors to a root marker via the working directory and climbs the other way. We follow the maintainer's method. The one R dependency is `this.path`, which is not `here`, taken because base R cannot self-locate a script across all run modes. Decided with the user via the question flow on 2026-06-17.
2. **In-script check is offline and speaks only on change.** Scripts run many times a day, so a network call or per-run chatter was rejected. The latest-release lookup lives only in the on-demand reconcile.
3. **One ledger file per member, identity from the home directory.** A shared Box or Dropbox folder gives every member the same files, so identity cannot live in the project. It is read from `~/.config/script-provenance/whoami`, falling back to username and host. This is the only artifact outside the project, optional, and created for the invoking user only with approval, to stay within the folder-scope contract.
4. **Tripwire plus restoration, stated as separate things.** The check proves a version changed, not that a result changed; the wording is always "verify." The cure is the restoration lockfile. Both are built; neither is presented as the other.
5. **Stata parity is partial and labeled.** Stata cannot self-locate a do-file and does not expose reliable ado versions. The skill records what it can and points to vendored ado files, rather than claiming parity with R and Python.

### Open items

- [ ] Run `scripts/validate_skills.sh` on a machine with `sh` to confirm the new parity and required-file checks pass before publishing. (The agent does not commit; the maintainer controls version control.)
- [ ] The runtime helpers (`provenance.R`, `provenance.py`, `provenance.do`) and `reconcile.R` in `references/provenance-system.md` are skeletons written to be dropped into a real project. They have not been executed against a live multi-member setup. The skill's Phase 5 verifies them on the actual project at use time.
- [ ] Decide whether `script-provenance` should become the single source of truth for the path standard, so `replication-repo` Phase 6 (which uses a `master.do` `$root` global) references it instead of carrying a parallel convention.

---

## 2026-06-10: Operating contract, approval gate, browser briefing, format overhaul

### Problems identified (review of the repo as of commit 7a66edf)

1. No shared operating context. No skill stated the research-associate role, the no-hallucination rule, the ask-first-when-vague rule, or folder scoping. The replication skill even asked for paths outside the invocation folder.
2. The replication skill built its dependency map internally and then pruned raw data in place with no user approval between mapping and deletion. Cross-script dependency chains were not explicitly required in the map.
3. Claude skills were flat `.md` files without YAML frontmatter, so they registered with weak fallback descriptions and triggered unreliably. Codex versions had proper frontmatter, so the platforms were not at parity.
4. Drifting duplicates existed on the maintainer machine: `~/.claude/commands/ref-audit.md` and `~/.claude/commands/replication-repo.md`, with a different name (`ref-audit`) than the repo (`ref-check`).
5. The em-dash ban was violated by the repo's own skill files, and nothing enforced the ban on generated artifacts.
6. `ref-check` had no user briefing before driving the user's browser: no tooling pre-flight, no VPN/login confirmation, no expectation-setting about verification gates and open tabs.
7. The validator only checked file existence and README strings.

### Changes made

- Created `context/OPERATING-CONTRACT.md` with a marked contract block (role, evidence rule, vague-scope rule, folder scope, approval before irreversible actions, no em-dashes). The block is embedded verbatim in all four skill files.
- Converted Claude skills to the proper format: `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter. Deleted the old flat files. Added `references/workbook-schema.md` to the Claude ref-check skill for parity.
- Rewrote `replication-repo` (both platforms, identical files):
  - Phase 1 now requires per-output dependency chains crossing scripts, not just per-script traces.
  - New Phase 2 is a hard approval gate: the map is written to `dependency_map.md`, shown as trees with the proposed deletion list and all ambiguities, and nothing is modified until the user approves. Approval is recorded with a date.
  - New Phase 3 copies the project into `replication_package/` inside the invocation folder. All later phases operate on the copy. The original project is never modified.
  - Renumbered phases 1 through 9. Removed all em-dashes. Removed the invitation to accept project paths outside the invocation folder.
- Rewrote `ref-check` (both platforms, identical files):
  - New Step 0: user briefing (what will happen in their browser, expected tab volume, their mid-run duties) plus browser tooling pre-flight (Claude in Chrome extension on Claude, browser tool on Codex) plus access confirmation (VPN or proxy, publisher logins) plus explicit go-ahead.
  - Added explicit rule that the agent never enters credentials or clicks through verification gates itself.
  - Stated that the skill never edits the `.bib` or the paper; the workbook is the deliverable.
- Added `scripts/install_claude_skills.sh`: symlinks `.claude/skills/*` into `~/.claude/skills/` and warns about the stale `~/.claude/commands/` copies.
- Rewrote `scripts/validate_skills.sh` to enforce: required files, frontmatter, byte-identical platform pairs, contract block identical to canonical, no em-dashes, retired name `ref-audit` absent, README coverage.
- Rewrote `README.md` as a guided document: contract summary, quick start per platform, a walkthrough of each skill (what it does, what you need, how a run unfolds, what you get), and an In Development section.
- Updated `codex-skills/*/agents/openai.yaml` default prompts to reflect the approval gate and the browser briefing.

### Decisions

1. **Copy model over in-place pruning.** The replication package is built in `replication_package/` inside the project folder. Rationale: the original files remain the restoration reference, and the prior in-place model contradicted its own "restore from the original" instruction. Cost: doubled disk use for large raw data. Revisit if a user hits disk limits; the alternative is mandatory per-file backups before in-place pruning.
2. **Skill name is `ref-check` everywhere.** `ref-audit` is retired; the validator fails if it reappears in the repo.
3. **Parity by byte-identical files.** Claude and Codex `SKILL.md` for the same skill are kept identical, with platform notes inline. Enforced with `cmp` in the validator. Edit one, copy to the other.
4. **Contract duplication over inclusion.** Skills cannot reliably follow external includes, so the contract is pasted into each skill and the validator diffs every copy against `context/OPERATING-CONTRACT.md`.
5. **Folder scope wording permits browsing only where a step requires it**, so ref-check's web verification remains compatible with the scoping rule.

### Open items

- [x] 2026-06-10: Maintainer confirmed the In Development list (`data-audit`, `pap-check`, `lit-table`) as the working roadmap.
- [x] 2026-06-10: Removed the stale `~/.claude/commands/ref-audit.md` and `~/.claude/commands/replication-repo.md` and installed the repo skills via `scripts/install_claude_skills.sh`. The repo is now the single source of truth on the maintainer machine.
- [ ] Consider a CI workflow (GitHub Actions) that runs `scripts/validate_skills.sh` on every push. Note: the validator uses plain `grep`, so a default ubuntu runner suffices.
- [ ] When the first new skill from the roadmap is drafted, decide whether the workbook-schema pattern (a `references/` folder per skill) becomes the standard for all skills.

---

## Earlier history

See git log before 2026-06-10: initial skill drafts, Codex ports, install and validation scripts, Required Files checks (commits 1ed470a through 7a66edf).
