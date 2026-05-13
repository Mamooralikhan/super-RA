# Super-RA

A collection of Claude Code skills for research assistant work in empirical social science. Each skill defines a structured, multi-phase agent that executes a specific research task with explicit standards, ordered phases, and user-controlled checkpoints.

Skills are designed for the workflows of research assistants in economics, political science, development studies, and related fields, including projects with foundations, multilateral institutions, and policy organizations.

---

## What is a Claude Skill?

A Claude skill is a markdown file that instructs Claude Code to carry out a bounded, well-defined task. When you type `/skill-name` in Claude Code, the agent reads the skill definition and executes the task in structured phases, pausing for your approval at each decision point.

Skills in this repository are opinionated. They enforce standards for reproducibility, data integrity, analytical rigor, and documentation. They are not general-purpose prompts.

---

## Installation

Clone this repository into your project, or copy the `.claude/skills/` directory into an existing project:

```bash
git clone https://github.com/YOUR-USERNAME/super-RA.git
```

Claude Code detects skill files in `.claude/skills/` automatically. No additional configuration is required.

---

## Skills

Skills are organized by research workflow phase. Each skill entry lists its status, required inputs, and primary outputs.

### Data and Replication

| Skill | Status | What it does |
|-------|--------|--------------|
| [`/replication-repo`](#replication-repo) | Available | Builds a complete, self-contained replication repository from an existing empirical project |

### Code and Analysis

| Skill | Status | What it does |
|-------|--------|--------------|
| `/coding-agent` | Planned | Reviews and standardizes analysis code for reproducibility, path discipline, and output consistency |

### Literature

| Skill | Status | What it does |
|-------|--------|--------------|
| `/lit-review` | Planned | Synthesizes a targeted literature review from a set of papers, structured around a research question |

### Writing and Review

| Skill | Status | What it does |
|-------|--------|--------------|
| `/peer-review` | Planned | Produces a structured academic referee report for a submitted manuscript |

---

## Skill Reference

### `/replication-repo`

Builds a clean, self-contained replication repository from an existing empirical project. The skill enforces that raw data values are never modified: only unused variables are removed, and all transformations happen in cleaning scripts that write to `data/clean/`.

**Required inputs:**
- Paper LaTeX source file (`.tex`)
- Tables folder (e.g., `tabs/`)
- Figures folder (e.g., `figs/`)
- Code directory containing analysis scripts (`.do`, `.R`, `.py`)

**Outputs:**

| Output | Description |
|--------|-------------|
| `data_inventory.pdf` | Documents every raw and clean data file, variables retained and removed, and which paper output each variable feeds |
| Pruned raw data files | Raw files with unreferenced columns removed; values never changed |
| Standardized scripts | All paths use a single `$root` global; outputs write to `output/tables/` and `output/figures/` |
| `master.do` | Single entry point that reproduces all results from a clean state |
| `README.md` | Replication instructions, software requirements, data access notes, and full output map |

**Phases:**
1. Read all code; build complete variable map from raw file to paper output
2. Produce `data_inventory.qmd` and compile `data_inventory.pdf`
3. Prune raw data files to the minimum required variable set
4. Standardize all script paths and output directories
5. Build `master.do`
6. Write `README.md`
7. Verify end-to-end reproducibility from a clean state

Full skill definition: [`.claude/skills/replication-repo.md`](.claude/skills/replication-repo.md)

---

## Repository Structure

```
super-RA/
├── README.md
├── LICENSE
└── .claude/
    └── skills/
        └── replication-repo.md       # available
        # coding-agent.md             # planned
        # lit-review.md               # planned
        # peer-review.md              # planned
```

---

## Contributing

Contributions are welcome, including new skills, refinements to existing ones, and documentation of how skills have been applied in real projects.

**To propose a new skill**, open a GitHub Issue with:
- The research task the skill addresses
- The inputs it requires
- The outputs it produces
- Any institutional constraints or edge cases worth handling

**To submit a skill**, open a pull request with a new `.md` file in `.claude/skills/`.

**Standards for new skills:**

- Scope the skill to a single, well-defined task with a clear completion criterion.
- Structure execution as explicit, ordered phases.
- State clearly what the skill enforces and what decisions remain with the user.
- List all required inputs and expected outputs up front.
- Document edge cases and known pitfalls in a dedicated section.
- The skill should ask the user for any required inputs at invocation, before beginning Phase 1.

---

## Author

Developed and maintained by [Mamoor Ali Khan](https://mamooralikhan.com). All skills in this repository are original work by Mamoor Ali Khan.

Last updated: May 13, 2026

---

## License

MIT. See [LICENSE](LICENSE).
