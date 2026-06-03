# Super-RA

`super-RA` is a public repository of research-assistant skills for empirical social science. The repository is designed for academics, research staff, and policy teams who need repeatable workflows for replication, documentation, and reference review.

The skills in this repository are strict by design. They are not generic prompts. Each skill is written as a bounded workflow with explicit inputs, ordered phases, stop conditions, outputs, and verification steps. The goal is to make serious analytical work more reproducible and less dependent on ad hoc prompting.

## Platform Support

This repository now ships skills for both Claude and Codex.

| Platform | Skill location | Notes |
|----------|----------------|-------|
| Claude | `.claude/skills/` | Claude can read project-local skills from this folder when the repository is the working directory. |
| Codex | `codex-skills/` | The repository includes Codex-native skill folders. For the most reliable setup, install them into your Codex skill library with `scripts/install_codex_skills.sh`. |

OpenAI skills are portable across products, but they do not automatically sync across products. This repository therefore keeps paired Claude and Codex versions side by side so each platform has a native, readable implementation.

## Available Skills

| Skill | Claude | Codex | What it does |
|-------|--------|-------|--------------|
| `replication-repo` | Yes | Yes | Builds a clean, self-contained replication repository from an existing empirical project without changing retained raw data values. |
| `ref-check` | Yes | Yes | Checks compiled paper references against source pages in the user's browser session and produces a review workbook for user verification. |

## Skill Details

### `replication-repo`

`replication-repo` turns an existing paper project into a clean replication package. The skill is procedural and should not be treated as a loose suggestion. It works through a fixed sequence:

1. Read all code and build the full raw-to-clean-to-output variable map.
2. Write and compile a `data_inventory` document.
3. Prune raw data files only by deleting variables proven to be unused.
4. Standardize code paths and output directories.
5. Build `master.do`.
6. Write project-level replication documentation.
7. Verify end-to-end reproducibility.

The core safeguard is non-negotiable: if a raw variable is retained, its values and name must not be changed. All transformations belong in cleaning scripts that write to `data/clean/`.

#### Prerequisites

The following must be present in the project folder before the skill starts. If the paper `.tex` file is absent, the skill halts immediately and asks for it — the skill cannot identify target tables and figures without the paper source.

| File or folder | Why it is required |
|:---|:---|
| Code scripts (`.do`, `.R`, `.py`) | Phase 1 variable map cannot be built without them. |
| **Paper `.tex` source file** | Required to identify which tables and figures the paper targets. The skill halts if this is missing. |
| Output tables and figures | Phase 7 end-to-end verification checks that every paper output is reproduced. |
| `data/raw/` files | Phases 1 and 3 variable tracing and pruning require the raw data to be present. |

#### Common failure modes

| Symptom | Likely cause |
|:---|:---|
| Skill cannot identify which figures to verify | `.tex` file is missing or not in the expected folder. Provide the paper source and re-invoke. |
| Phase 3 fails to find expected variables | Raw data files are missing or the code directory does not match the data directory. |
| `data_inventory.pdf` fails to compile | LaTeX installation is missing or font paths differ from the defaults. Adjust the font block in the `.qmd` file for the local TeX Live path. |
| Phase 7 reports no outputs | Restricted data may be missing. Check that pre-computed skip guards are in place for cleaning scripts that depend on restricted sources. |

#### Expected outputs

- `data_inventory.qmd` and `data_inventory.pdf`
- pruned raw files with unused variables removed
- standardized scripts using a single project root
- `master.do`
- replication instructions and output map in the target repository README

Skill files:

- Claude: [`.claude/skills/replication-repo.md`](.claude/skills/replication-repo.md)
- Codex: [`codex-skills/replication-repo/SKILL.md`](codex-skills/replication-repo/SKILL.md)

### `ref-check`

`ref-check` is a conservative reference-audit skill. It does not silently "fix" a bibliography. Instead, it compiles the paper, treats the compiled bibliography as the source of truth for what the paper currently cites, and checks those citations against actual source pages.

The workflow is browser-based:

- the agent uses the user's browser session to open DOI and URL targets
- the agent reads the source page, not just search snippets
- the agent records what the source page says in a workbook
- the user remains the final verifier for ambiguous or substantive bibliographic questions

The workbook is a review artifact. It is meant to help the user inspect:

- incorrect DOI or URL links
- possible hallucinated references
- working papers that may since have journal versions
- missing or incorrect year, volume, issue, page, article number, DOI, or venue metadata

#### Prerequisites

The following must be present in the paper folder before the skill starts. If Step 1 compilation fails for any reason, the skill halts and reports the exact error rather than attempting to extract references from broken output.

| File | Why it is required |
|:---|:---|
| **Paper `.tex` source file** | Step 1 compiles the paper to extract the rendered bibliography. The skill halts if this is missing. |
| **`.bib` file(s)** | Compilation fails without the bibliography source. |
| Bibliography style files (`.bst`, `.sty`) | Required for correct compilation. The skill attempts to compile and halts if style files are missing. |
| Working LaTeX installation (`xelatex` or `pdflatex`) | The skill cannot run Step 1 without a local LaTeX environment. |
| Browser session access | Required for Steps 3 through 5 source-page verification. If unavailable, linked-reference checking is skipped and flagged to the user. |

#### Common failure modes

| Symptom | Likely cause |
|:---|:---|
| Step 1 compile fails | Missing `.bib` or style file. Run `xelatex` manually, read the error log, and confirm all input files are in the folder. |
| References extracted from `.bib` instead of compiled output | The skill defaulted to the raw `.bib` because the compile failed silently. Always resolve compile errors before proceeding. |
| Browser check fails on every reference | Institutional proxy or VPN is not active. Browser session must be authenticated if the paper cites journal-paywalled sources. |
| Rows remain blank in column B after Phase 1 | Human-verification gate was not clicked through. Batch the unresolved tabs and ask the user to clear them. |

#### Expected outputs

- an Excel workbook ordered to match the paper bibliography
- a comparison column showing the source-page reference
- issue flags for incorrect links or unresolved cases
- a short final report listing rows that still require human follow-up

Skill files:

- Claude: [`.claude/skills/ref-check.md`](.claude/skills/ref-check.md)
- Codex: [`codex-skills/ref-check/SKILL.md`](codex-skills/ref-check/SKILL.md)

## Installation and Use

### Claude

Clone the repository into the project you want Claude to work on:

```bash
git clone https://github.com/YOUR-USERNAME/super-RA.git
```

Claude reads skills from `.claude/skills/` when the repository is the working folder.

### Codex

The Codex skills in this repository live in `codex-skills/` and follow the standard `SKILL.md` layout. For the most reliable installation, run:

```bash
sh scripts/install_codex_skills.sh
```

That script symlinks each skill folder into `${CODEX_HOME:-$HOME/.codex}/skills/`, which matches Codex's personal skill-library layout. After installation, invoke a skill in Codex with `$replication-repo` or `$ref-check`.

If your Codex environment already supports repo-local skills, the same skill folders remain readable in place. The installer exists so the repository remains usable even when repo-local discovery is not enabled.

## Reliability Checks

Run the repository validation script after edits:

```bash
sh scripts/validate_skills.sh
```

The validator checks:

- required Claude and Codex skill files exist
- Codex skill folders include `SKILL.md` and `agents/openai.yaml`
- the README mentions both skills and both platforms
- stray `.DS_Store` files are reported if they appear outside `.git/`

## Repository Layout

```text
super-RA/
├── README.md
├── LICENSE
├── .gitignore
├── .claude/
│   └── skills/
│       ├── replication-repo.md
│       └── ref-check.md
├── codex-skills/
│   ├── replication-repo/
│   │   ├── SKILL.md
│   │   └── agents/openai.yaml
│   └── ref-check/
│       ├── SKILL.md
│       ├── agents/openai.yaml
│       └── references/workbook-schema.md
└── scripts/
    ├── install_codex_skills.sh
    └── validate_skills.sh
```

## GitHub Use and Contributions

This repository is ready to be cloned, versioned, reviewed, and extended on GitHub.

When contributing:

- keep each skill scoped to a single workflow
- document inputs, outputs, and verification steps clearly
- preserve platform parity when a skill exists for both Claude and Codex
- avoid weakening safeguards in existing skills without explaining why
- update the root README whenever a skill is added, removed, or materially changed

To propose a new skill, open an issue with:

- the research task it addresses
- the required inputs
- the required outputs
- the main failure risks or edge cases

## Author

Developed and maintained by [Mamoor Ali Khan](https://mamooralikhan.com).

Last updated: June 3, 2026

## License

MIT. See [LICENSE](LICENSE).
