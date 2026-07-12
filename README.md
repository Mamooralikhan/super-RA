# Super-RA

`super-RA` is a research assistant for empirical social science: a **brain** you install into a project, and three **skills** that run inside it. It is built for academics, research staff, and policy teams who need repeatable workflows for replication, documentation, and reference review.

It is strict by design. Each skill is a bounded workflow with explicit inputs, ordered phases, hard stop conditions, and verification steps. They are not loose prompts. The goal is to make serious analytical work reproducible and less dependent on ad hoc prompting.

## The Brain

Install super-RA into a project and **Claude becomes the super-RA in that project.**

```bash
sh scripts/install_super_ra.sh /path/to/your/project
```

From then on, every Claude Code session launched in that folder is governed by the super-RA brain ([brain/CLAUDE.md](brain/CLAUDE.md)). Your personal `~/.claude/CLAUDE.md` is **not loaded there**, the brain replaces it, and a notice at session start tells you so.

This is a real replacement, not a suggestion. By default Claude Code *concatenates* every instruction file it finds, so a project's rules are merely appended underneath your personal ones. super-RA installs a `claudeMdExcludes` rule that stops the global file from loading at all. Only an organization's managed-policy file outranks it, which is correct: a company's compliance rules should beat a research tool.

What the brain governs:

- **Every claim shows its source, and the source is clickable.** There is no notation to learn. A claim about your project links to the file and the line. A claim from the literature links to the paper. A claim with no source says so, in plain words, in the sentence itself.
- **It never invents a link.** Every URL must be one that actually came back from a tool call. No DOI constructed from a pattern, no publisher URL assembled because it ought to work. A link that looks right and goes nowhere is worse than no link, because it turns the assistant's uncertainty into your confidence, invisibly.
- **It checks instead of guessing.** Reading files and looking sources up are reads, and reads are free. If it cannot point to where something came from, it goes and finds out, or it tells you it could not.
- **Approval.** Every write, edit, command, and deletion is asked for first, in words. A yes in a previous task is not a yes in this one.
- **Pipeline before code.** The first deliverable of a data task is an agreed, numbered, ordered pipeline, not code.
- **Attribution.** Every deliverable is signed, and the use of Claude Code is disclosed rather than hidden. A byline is never shipped with a missing name.

The effect is that Claude stops behaving like a general assistant. Asked a factual question it cannot ground, a default session answers fluently from memory. A super-RA session tells you it cannot verify that, offers to go and check, and comes back with something you can click.

Two layers do the work, and they are not interchangeable. Judgement lives in `CLAUDE.md`, because it is something an agent must reason with. Prohibitions live in `.claude/settings.json`, because a rule an agent can reason its way past is not a rule. See [brain/README.md](brain/README.md).

**The installer refuses to overwrite.** If the target project already has a `CLAUDE.md` or a `.claude/settings.json`, it reports what it found, changes nothing, and leaves the decision to you.

**One step is yours.** Project settings and hooks are trust-gated. Until you accept the workspace-trust dialog once in that folder, the brain is inert.

## The Skills

Every skill also carries the Operating Contract, kept canonically in [context/OPERATING-CONTRACT.md](context/OPERATING-CONTRACT.md) and embedded verbatim in each skill file. That contract is what carries super-RA's discipline into a skill invoked in a folder super-RA does **not** govern. It is honest about its own limit: a skill cannot unload your global rules mid-session. Only installing the brain does that.

To use the skills from any project, install them into your personal skill library:

```bash
sh scripts/install_claude_skills.sh
```

The installer symlinks each skill into `~/.claude/skills/` and warns if it finds older standalone copies in `~/.claude/commands/` that could drift from the repository versions. Invoke with `/replication-repo`, `/ref-check`, or `/script-provenance`.

super-RA targets Claude. Codex support was removed on 2026-07-12, because `ref-check` depends on subagents and a single agent reviewing its own work is not an independent check. Shipping a degraded variant under the same name would have been worse than shipping nothing. See [WORKLOG.md](WORKLOG.md).

## Available Skills

| Skill | What it does |
|-------|--------------|
| `replication-repo` | Converts an empirical project into a clean replication package, with a user-approved dependency map before anything is changed, and without ever modifying the original project folder. |
| `ref-check` | Verifies every reference that actually prints in your paper against an authoritative online source, using three tiers that check each other, and reports what is wrong in two HTML reports. It never edits your `.bib`. |
| `script-provenance` | Standardizes R, Python, and Stata scripts with a common header and file-anchored paths, so a mixed team runs them without editing paths, and tracks package versions across the team to catch silent reproducibility breaks. |

## Skill Guide

### `replication-repo`: from messy project to replication package

**What it does.** Reads every script in your project, maps every dependency from raw variable to paper output, asks for your approval of that map, then builds a clean, self-contained replication package as a copy. Your original project folder is never modified.

**What you need in the folder before starting:**

- the project code (`.do`, `.R`, `.py`)
- the raw data files
- the paper `.tex` source (the skill halts without it, because it cannot know which tables and figures to target)
- existing output tables and figures, for end-to-end verification

**How a run unfolds:**

1. The agent confirms the folder contents and asks for the paper title, journal, and whether any data are restricted-access (DHS, MICS, IPUMS, and similar).
2. It reads all code and builds the full dependency map: every table and figure traced back through every script, intermediate file, and raw variable, including chains that cross multiple scripts.
3. **Approval gate.** It writes the map to `dependency_map.md`, shows you each output as a tree, lists every raw variable proposed for deletion and everything ambiguous, and stops. Nothing in your project is touched until you approve.
4. After approval, it copies the project into `replication_package/` and does all further work there: data inventory document, pruning of unused raw variables, path standardization, `master.do`, and the package README.
5. It verifies end to end by running `master.do` from a clean state and confirming every paper output is reproduced.

**What you get:** `replication_package/` containing `dependency_map.md`, `data_inventory.qmd` and `data_inventory.pdf`, pruned raw files with values untouched, standardized scripts under a single project root, `master.do`, and a README that a new research assistant can follow without reverse engineering anything.

**Core safeguard.** If a raw variable is retained, its values and name are never changed. All transformations happen in cleaning scripts that write to `data/clean/`. Pruning removes only variables you approved for deletion in step 3.

Skill file: [.claude/skills/replication-repo/SKILL.md](.claude/skills/replication-repo/SKILL.md)

### `ref-check`: verify every reference that actually prints

**What it does.** Reads your `.tex` and `.bib` directly, works out which references *actually print*, and verifies each one against an authoritative online source. It reports what is wrong in two HTML reports. It never edits your `.bib` or your paper. You stay the final verifier.

**The scope is smaller than you think.** A `.bib` usually holds many entries the paper never cites, and uncited entries never print. On the paper this skill was built against, the `.bib` had 175 unique entries and the paper cited 66. The skill establishes that number first and tells you, before committing you to a long run.

**Why three tiers.** The tiers check each other, and that is the whole point.

- **Assistant** fetches, and only fetches. Its source universe is *closed*: the journal of record (or Crossref, where publishers file their own official metadata), the author's own site, or the official issuing institution. Blogs, ResearchGate, Academia.edu and aggregators are forbidden. It is not allowed to invent a link, and when it finds nothing it says so.
- **Associate** trusts none of that and re-clicks every link itself. On the real run it corrected the Assistant on 15 of 66 entries, and two of those were entries the Assistant had *wrongly accused*. Without an independent re-click, the report would have told the author to fix things that were already correct.
- **PI** is the main agent, never delegated. It rules on author order, on whether a working paper has since been published, and on institutional authorship, and it spot-checks a sample personally.

**What it catches.** On a 66-reference paper it found three critical errors that compiling the paper would never reveal: a World Bank citation whose own URL serves a report about a **different country**, an entry that **fused three different real papers** into one, and a citation to a work that **does not exist** under the authors given. It also found a wrong year, two wrong author forenames, and an author field that BibTeX silently collapses from six authors into five.

**What you need in the folder:** the paper `.tex` and its `.bib`. That is all. No LaTeX install, no VPN, no publisher logins, no browser.

**It asks which files, and it never guesses.** A research folder usually holds several `.tex` files and more than one `.bib`. The skill lists what it found, identifies the main file, reads the bibliography name out of the paper itself rather than off the file listing, and asks you to confirm before a single reference is touched. It then follows every `\input` and `\include` recursively, and prints each file it read with the number of citations it contributed. A paper split across `sections/*.tex` keeps its citations in the children, and an extractor that reads only the main file does not error: it just reports fewer references and looks perfectly healthy doing it.

**Report, do not fix.** The `.tex` and `.bib` are read-only for the whole run, and no corrected `.bib` is produced. Which version of a working paper to cite, or whether a 1971 revised edition is the one you read, is your decision and not the pipeline's. The skill records the byte sizes of both files at the start and re-checks them at the end, so "nothing was modified" is verified rather than asserted.

**Honest limits.** A paywalled page that refuses an automated fetch is *not* evidence that a reference is false; those entries are corroborated at a second authoritative source and labelled `blocked_corroborated`, so you can see that nobody actually loaded the page. And `not found` is reported as not found, never quietly replaced with a plausible guess.

**What you get:** two HTML reports, rendered by one script from one JSON so they cannot disagree with each other. An audit trail with four columns (Original, Assistant, Associate, PI) showing where the tiers disagreed, and a red/green comparison of what needs changing and why. Both carry a hygiene panel covering duplicate `.bib` keys, which of them actually print, and how many entries are never cited.

**Requires subagents**, so it is Claude only. The Associate's independence from the Assistant is the anti-hallucination mechanism, and one agent reviewing its own work is not an independent check.

Skill file: [.claude/skills/ref-check/SKILL.md](.claude/skills/ref-check/SKILL.md). Method: [extraction rules](.claude/skills/ref-check/references/extraction-rules.md), [report schema](.claude/skills/ref-check/references/report-schema.md), [pipeline templates](.claude/skills/ref-check/references/pipeline/).

### `script-provenance`: portable scripts and team-wide version tracking

**What it does.** Solves two recurring pains on multi-member projects. First, paths: every script is made file-anchored, so the script's own location is the origin and climbing up uses `..` segments, with no absolute path hardcoded. The same file then runs unchanged on any machine and inside any Box or Dropbox mount, with no path edit on open. Second, package drift: each script records the package versions it ran with and warns, only when something changed, that results may be affected. A per-member ledger and an on-demand reconcile report show the whole team who is on which version and who is behind.

**The path method.** The script file is the only anchor. To reach the project root, the path block climbs with `..` segments, then every other path is built downward from that root. This works cleanly in Python and, with the `this.path` package, in R. Stata cannot self-locate a do-file, so it anchors through a marker file and one editable root line, and the skill says so rather than pretending parity.

**The version method.** Three layers. A baseline of blessed versions, the ones that produced the committed results. A per-member ledger, one file per teammate so shared folders never conflict, recording each environment. An offline in-script check that stays silent until a version changes, then prints one line and points to reconcile. A restoration layer (renv or groundhog for R, uv or a pinned requirements file for Python, vendored ado files for Stata) is what reinstalls the exact old versions when a drift is confirmed. The check is the tripwire; the restoration layer is the cure.

**What you need in the folder before starting:**

- the scripts to standardize (`.R`, `.py`, `.do`)
- knowledge of the project root and the folder depth of the scripts
- the author name to stamp, and a one-line purpose for any new script

**How a run unfolds:**

1. The agent confirms the mode (standardize existing scripts, initialize only, scaffold a new script, or reconcile), the languages present, and the author.
2. It inventories every script: current paths, hardcoded absolute paths, headers, and packages.
3. **Approval gate.** It writes `provenance_plan.md` with the header to add, the before-and-after of every path line, and the version-check call per script, then stops. No script is edited until you approve, since a wrong path rewrite can break a pipeline.
4. After approval, it applies the header, the file-anchored path block, and the version check, changing nothing else in the script logic.
5. It installs the `.provenance/` system, sets the baseline and the restoration lockfile, and verifies by running a script from outside its own folder and by triggering one simulated drift.

**What you get:** standardized scripts that any teammate runs without editing a path, a `.provenance/` folder holding the baseline, the per-member ledgers, and the reconcile script, and dated reconcile reports under `.provenance/reports/` that show, package by package, who is on which version and who is behind the latest release.

**Honest limits.** The check proves a version changed, not that a result changed, so it always says "verify." Stata records package versions only partially, because it does not expose reliable ado version numbers.

Skill file: [.claude/skills/script-provenance/SKILL.md](.claude/skills/script-provenance/SKILL.md)

## In Development

More skills are being built on the same contract. Planned next:

| Skill | Status | What it will do |
|-------|--------|-----------------|
| `data-audit` | Planned | Pre-cleaning audit of a raw dataset: structure, identifiers, duplicates, missingness, and codebook consistency, reported before any cleaning decisions are made. |
| `pap-check` | Planned | Compare a draft against its pre-analysis plan and flag deviations in outcomes, specifications, and samples for the authors to justify or document. |
| `lit-table` | Planned | Build a structured comparison table of cited empirical papers: design, identification strategy, sample, and headline estimates, each sourced to the cited paper. |

Progress and decisions are tracked in [WORKLOG.md](WORKLOG.md). To propose a skill, open an issue with the research task, required inputs, required outputs, and the main failure risks.

## Reliability Checks

Run the validator after any edit:

```bash
sh scripts/validate_skills.sh
```

It enforces:

- required files exist
- every `SKILL.md` has `name` and `description` frontmatter
- the Operating Contract block in every skill matches the canonical copy
- the brain block in `CLAUDE.md` matches `brain/CLAUDE.md`
- `brain/settings.json` still carries the three things that make super-RA supersede rather than merely suggest: the `claudeMdExcludes` rule, the deny rules, and the session notice
- the session-notice hook parses and is executable
- no em-dashes in skills, contract, brain, or README
- every shipped pipeline template compiles
- Codex support stays removed
- the README documents every skill

## Repository Layout

```text
super-RA/
├── README.md
├── CLAUDE.md                       <- the brain, governing this repo. super-RA holds itself
│                                      to the contract it ships.
├── WORKLOG.md                      <- running log of changes and decisions
├── LICENSE
├── .gitignore
├── brain/                          <- what gets installed into a research project
│   ├── CLAUDE.md                   <- THE BRAIN. The canonical constitution.
│   ├── README.md                   <- how supersession actually works, and why
│   ├── settings.json               <- claudeMdExcludes, deny rules, the session hook
│   └── hooks/
│       └── super_ra_notice.sh      <- tells the user super-RA has taken over
├── context/
│   └── OPERATING-CONTRACT.md       <- canonical contract, embedded in every skill
├── .claude/
│   └── skills/
│       ├── replication-repo/
│       │   └── SKILL.md
│       ├── ref-check/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── extraction-rules.md      <- why each parser guard exists
│       │       ├── methodology-assistant.md <- tier 1 contract
│       │       ├── methodology-associate.md <- tier 2 contract
│       │       ├── report-schema.md         <- HTML columns, statuses, layout rules
│       │       └── pipeline/                <- six runnable templates, 01 to 06
│       └── script-provenance/
│           ├── SKILL.md
│           └── references/
│               ├── templates.md
│               └── provenance-system.md
└── scripts/
    ├── install_super_ra.sh         <- install the brain INTO a research project
    ├── install_claude_skills.sh    <- install the skills into ~/.claude/skills/
    └── validate_skills.sh
```

## Contributing

- Keep each skill scoped to a single workflow.
- Keep the Operating Contract block identical everywhere; edit it only in `context/OPERATING-CONTRACT.md` and copy it out. The same goes for the brain block: edit `brain/CLAUDE.md`, then copy it into `CLAUDE.md`. The validator checks both.
- Do not weaken safeguards in existing skills without explaining why.
- Read [.claude/skills/ref-check/references/extraction-rules.md](.claude/skills/ref-check/references/extraction-rules.md) before touching `01_extract_citations.py`. Every guard in it was learned from a bug that produced a confident, entirely wrong accusation against a bibliography that was correct.
- Update the README and WORKLOG whenever a skill is added, removed, or materially changed.

## Author

Developed and maintained by [Mamoor Ali Khan](https://mamooralikhan.com).

Last updated: July 12, 2026

## License

MIT. See [LICENSE](LICENSE).
