# Super-RA

`super-RA` is a public repository of research-assistant skills for empirical social science. It is built for academics, research staff, and policy teams who need repeatable workflows for replication, documentation, and reference review.

The skills are strict by design. Each one is a bounded workflow with explicit inputs, ordered phases, hard stop conditions, and verification steps. They are not loose prompts. The goal is to make serious analytical work reproducible and less dependent on ad hoc prompting.

## How These Skills Behave

Every skill in this repository carries the same Operating Contract, kept canonically in [context/OPERATING-CONTRACT.md](context/OPERATING-CONTRACT.md) and embedded verbatim in each skill file. In short:

- The agent acts as a careful research associate working for a professor. It has no margin to hallucinate and no authority to act outside the stated scope of work.
- If the request is vague, the agent asks clarifying questions first and proceeds only after you confirm the scope.
- All knowledge and decisions come from the folder the agent is invoked from. It does not read or write outside that folder, and it does not use prior model knowledge of your paper or data to fill gaps.
- No file is modified, deleted, or overwritten before you approve the specific plan that requires it.
- Generated artifacts contain no em-dashes.

The validation script enforces that this contract stays identical across every skill on both platforms.

## Quick Start

### Claude

Claude skills live in `.claude/skills/`, one folder per skill with a `SKILL.md`. They are picked up automatically when this repository is your working folder. To use them from any project, install them into your personal skill library:

```bash
sh scripts/install_claude_skills.sh
```

The installer symlinks each skill into `~/.claude/skills/` and warns if it finds older standalone copies in `~/.claude/commands/` that could drift from the repository versions. Invoke with `/replication-repo` or `/ref-check`.

### Codex

Codex skills live in `codex-skills/`, in the standard `SKILL.md` layout. Install them into your Codex skill library:

```bash
sh scripts/install_codex_skills.sh
```

The installer symlinks each skill folder into `${CODEX_HOME:-$HOME/.codex}/skills/`. Invoke with `$replication-repo` or `$ref-check`.

Paired Claude and Codex skill files are kept byte-identical so the two platforms never drift. The validator checks this.

## Available Skills

| Skill | Claude | Codex | What it does |
|-------|--------|-------|--------------|
| `replication-repo` | Yes | Yes | Converts an empirical project into a clean replication package, with a user-approved dependency map before anything is changed, and without ever modifying the original project folder. |
| `ref-check` | Yes | Yes | Audits a compiled paper's references against real source pages using your own browser session, and produces a color-coded review workbook for your verification. |

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

Skill files: [Claude](.claude/skills/replication-repo/SKILL.md) | [Codex](codex-skills/replication-repo/SKILL.md)

### `ref-check`: reference audit with your own browser

**What it does.** Compiles your paper, treats the compiled bibliography as the source of truth for what the paper cites, opens each DOI and URL in your own browser session, reads the actual source page, and records what it finds in an Excel review workbook. It does not edit your `.bib` or your paper. You stay the final verifier.

**Why your browser?** Institutional access, VPN cookies, and publisher logins decide whether the real source page is reachable. Anonymous search snippets are not verification. Using your session means the agent sees what you would see.

**What you need in the folder before starting:**

- the paper `.tex` source and its `.bib` file(s)
- bibliography style files (`.bst`, `.sty`) if the paper needs them
- a working LaTeX installation (`xelatex` or `pdflatex`)
- a connected browser session (Claude in Chrome extension for Claude, the built-in browser tool for Codex)

**What the skill asks of you, and when.** Before opening a single page, the agent briefs you: how many references it found, roughly how many tabs it will open, and what it needs you to confirm first, namely that your VPN or institutional proxy is on and that you are logged into the publisher sites you normally use. During the run, it will pause and hand you a short queue whenever a site shows a human-verification gate, because the agent does not click through those itself. At the end, unresolved tabs stay open so you can inspect them.

**How a run unfolds:**

1. Briefing and browser pre-flight (the agent waits for your go-ahead).
2. Compile the paper and extract the rendered bibliography in paper order.
3. Build the workbook skeleton: original reference, source-page reference, incorrect-link flag.
4. Phase 1: check every reference that already has a DOI or URL, in batches.
5. Phase 2: only after Phase 1 is stable, work the rows with no link and revisit failures.
6. Add the review layer: status columns, metadata columns, and color coding per the [workbook schema](codex-skills/ref-check/references/workbook-schema.md).

**What you get:** an Excel workbook in paper order showing, for every reference, what the paper says next to what the source page says, with flags for incorrect links, suspect metadata, working papers that may have later journal versions, and the rare row that may be hallucinated. A reference is marked `hallucinated` only after conservative journal-first checking fails, never just because a link redirects oddly or a source is paywalled.

Skill files: [Claude](.claude/skills/ref-check/SKILL.md) | [Codex](codex-skills/ref-check/SKILL.md)

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

- required files exist for both platforms
- every `SKILL.md` has `name` and `description` frontmatter
- paired Claude and Codex skill files are byte-identical
- the Operating Contract block in every skill matches the canonical copy
- no em-dashes in skills, contract, or README
- the README documents every skill and both platforms

## Repository Layout

```text
super-RA/
├── README.md
├── WORKLOG.md                      <- running log of changes and decisions
├── LICENSE
├── .gitignore
├── context/
│   └── OPERATING-CONTRACT.md       <- canonical contract, embedded in every skill
├── .claude/
│   └── skills/
│       ├── replication-repo/
│       │   └── SKILL.md
│       └── ref-check/
│           ├── SKILL.md
│           └── references/workbook-schema.md
├── codex-skills/
│   ├── replication-repo/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   └── ref-check/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── references/workbook-schema.md
└── scripts/
    ├── install_claude_skills.sh
    ├── install_codex_skills.sh
    └── validate_skills.sh
```

## Contributing

- Keep each skill scoped to a single workflow.
- Keep the Operating Contract block identical everywhere; edit it only in `context/OPERATING-CONTRACT.md` and copy it out.
- Preserve platform parity: edit one platform's `SKILL.md`, copy it to the other, run the validator.
- Do not weaken safeguards in existing skills without explaining why.
- Update the README and WORKLOG whenever a skill is added, removed, or materially changed.

## Author

Developed and maintained by [Mamoor Ali Khan](https://mamooralikhan.com).

Last updated: June 10, 2026

## License

MIT. See [LICENSE](LICENSE).
