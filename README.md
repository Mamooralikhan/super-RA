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

Expected outputs include:

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

Expected outputs include:

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

Last updated: May 29, 2026

## License

MIT. See [LICENSE](LICENSE).
