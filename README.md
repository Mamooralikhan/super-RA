# Super-RA: Claude Skills for Empirical Research

A collection of Claude Code skills for research workflows in economics, political science, and related fields. Each skill defines a structured, multi-phase agent behavior for a specific research task. Skills are designed to be reusable across projects and explicit about what they will and will not do.

---

## What is a Claude Skill?

A Claude skill is a markdown file that instructs Claude Code to carry out a bounded, well-defined task. When invoked with `/skill-name`, Claude Code reads the skill definition and executes the task in structured phases, pausing for user approval at key decision points.

Skills in this repository are opinionated about best practices. They are not general-purpose prompts; they enforce standards for reproducibility, data integrity, and documentation.

---

## Prerequisites

- [Claude Code](https://claude.ai/code), installed and authenticated
- The project repository or folder open in Claude Code
- Access to the input files described in each skill (listed below)

---

## Installation

Clone this repository or copy the `.claude/skills/` directory into your project:

```bash
git clone https://github.com/YOUR-USERNAME/super-RA.git
```

If you are adding skills to an existing project, copy the relevant `.md` file from `.claude/skills/` into the `.claude/skills/` directory of your project. Claude Code will detect the skill automatically.

---

## Available Skills

### `/replication-repo`

Builds a clean, self-contained replication repository from an existing empirical project. The skill enforces the principle that raw data values are never modified: only unused variables are removed, and all transformations happen in cleaning scripts.

**What it produces:**

| Output | Description |
|--------|-------------|
| `data_inventory.pdf` | Documents every data file, variable retained, variable removed, and the paper output each variable feeds |
| Pruned raw data files | Raw files stripped of columns not referenced by any script |
| Standardized code | All scripts use a single `$root` global; outputs write to `output/tables/` and `output/figures/` |
| `master.do` | Single entry point that runs the full pipeline from a clean state |
| `README.md` | Replication instructions, software requirements, data access notes, and output map |

**Required inputs:**

- The paper's LaTeX source file (`.tex`)
- A folder of tables (e.g., `tabs/`)
- A folder of figures (e.g., `figs/`)
- The code directory with analysis scripts (`.do`, `.R`, `.py`)

**How to invoke:**

1. Open Claude Code with the project repository in context.
2. Run `/replication-repo`.
3. Claude will ask for: (a) the code directory path, (b) the paper title and journal, and (c) whether any data files are restricted-access.
4. Claude will report completion of each phase before starting the next. Phases that require judgment calls will pause for user input.

**Phases executed:**

1. Read all code and build a complete variable map: raw file to variable to clean variable to paper output
2. Produce `data_inventory.qmd` and compile `data_inventory.pdf`
3. Prune raw data files to the minimum required variable set
4. Standardize all script paths and output directories
5. Build `master.do`
6. Write `README.md`
7. Verify end-to-end reproducibility

See [`.claude/skills/replication-repo.md`](.claude/skills/replication-repo.md) for the full skill definition, including rules, edge cases, and pitfalls.

---

## Repository Structure

```
super-RA/
├── README.md
├── LICENSE
└── .claude/
    └── skills/
        └── replication-repo.md
```

---

## Contributing

Contributions of new skills and refinements to existing ones are welcome.

**To propose a new skill:**
1. Open a GitHub Issue describing the research task the skill addresses, the inputs it requires, and the outputs it produces.
2. Submit a pull request with a new `.md` file in `.claude/skills/`.

**Standards for new skills:**

- Scope the skill to a single, well-defined task.
- Structure execution as explicit, ordered phases.
- State clearly what the skill enforces and what decisions remain with the user.
- List all required inputs and expected outputs.
- Document edge cases and known pitfalls.

---

## License

MIT. See [LICENSE](LICENSE).
