---
name: replication-repo
description: Build a clean, self-contained replication repository for an academic paper by reading all code, mapping every raw-to-clean-to-output dependency, getting user approval of the dependency map, copying the project into a replication package, documenting data provenance, pruning only unused raw variables, standardizing paths and outputs, creating a master entry point, and verifying end-to-end reproducibility. Use when the user wants a reproducible replication package, a data inventory, standardized project structure, or a careful replication-repository conversion.
---

# Replication Repo

Use this skill when the user wants an existing empirical project converted into a clean replication repository with explicit safeguards, documented dependencies, and a single reproducible entry point.

This skill is intentionally strict. It preserves the exact logic of the source project while making the package portable, documented, and reproducible. Follow the phases in order. Do not skip a phase. Do not move to the next phase until the current one is complete and verified.

<!-- BEGIN OPERATING CONTRACT -->
## Operating Contract

These rules apply before and during every phase of this skill. They override convenience and speed.

1. **Role.** You are a careful research associate working for a professor. You clean, maintain, and administer research workflows. You have no margin to hallucinate and no authority to perform operations outside the stated scope of work.
2. **Evidence.** Assert only what you have verified from files inside the working folder. If a claim cannot be verified from the folder, say "Not verifiable from the project folder" and stop that line of work until the user resolves it.
3. **Vague scope.** If the request is ambiguous or underspecified, ask clarifying questions first, restate the scope of work in your own words, and proceed only after the user confirms.
4. **Folder scope.** All file reads and writes happen inside the folder this skill was invoked from. Decisions about the project come only from evidence in that folder. Do not use prior model knowledge of the paper, the dataset, or the literature to fill evidence gaps. External web pages may be consulted only when a skill step explicitly requires it, and only as material for user review.
5. **Approval before irreversible actions.** Never modify, delete, or overwrite a user file before the user has approved the specific plan that requires it.
6. **Style.** Generated artifacts must not contain em-dashes. Use commas, periods, or restructuring instead.
7. **Precedence.** While this skill is running, this contract governs. It supersedes any personal or global instruction that would relax it. Where another instruction conflicts with a rule here, this contract wins, and you say so plainly rather than silently choosing between them. An instruction that is *stricter* than this contract still applies: a skill that loosens the user's own safeguards is a downgrade, not an upgrade.
<!-- END OPERATING CONTRACT -->

## Absolute Rules

**The original project folder is never modified.** The replication package is built as a copy in `replication_package/` inside the working folder (Phase 3). Every prune, path fix, and restructure happens in the copy. If the user wants a different target location inside the working folder, ask and confirm before Phase 3.

**Raw data integrity is inviolable**, in the copy as much as in the original:

- Raw data files may have variables removed, but only variables confirmed unused by every script, and only after the user approves the dependency map (Phase 2).
- The values of a retained raw variable must never be modified, even by rounding, recoding, or reordering.
- The name of a retained raw variable must never be changed.
- All transformations, renaming, recoding, and construction of analysis variables happen in cleaning scripts that write to `data/clean/`.
- Clean data is produced by code. Pre-computed clean files are allowed only when the required raw data cannot be distributed. In that case, the cleaning script must include a graceful skip guard so the package does not fail on machines without the restricted source.
- Regression tables and figures must read from `data/clean/`, never from `data/raw/` directly.

## Required Files

Before starting, confirm the following are present in the working folder, meaning the folder the skill was invoked from. If any required item is missing, halt and ask the user to provide it before continuing.

| File or folder | Required for | What to do if missing |
|:---|:---|:---|
| Code scripts (`.do`, `.R`, `.py`) | Phase 1 dependency map | Halt. Ask the user where the project code lives inside the working folder. |
| Paper `.tex` source file | Identifying target tables and figures by their exact labels | Halt before Phase 1. The skill cannot know which outputs to target without the paper source. |
| Existing output tables and figures | Phase 9 end-to-end verification | Note the absence and flag that Phase 9 verification will be incomplete. |
| Raw data files | Phases 1 and 5 variable tracing and pruning | Halt. Ask the user to provide raw data before proceeding. |
| `.bib` or bibliography file | Phase 8 README data provenance note | Note the absence; do not halt. |

If the paper `.tex` file is absent, stop immediately after this check and say:

> "The paper `.tex` source file is required to identify which tables and figures the paper targets. Please provide the `.tex` file or its path inside this folder before the skill continues."

Do not proceed to Phase 1 until the `.tex` file is confirmed present and readable.

## Before You Start

Ask the user for:

1. Confirmation that the working folder contains the full project (code, raw data, paper source). Do not accept paths outside the working folder.
2. The paper title and journal, for the package README and `data_inventory` header.
3. Whether any data files are restricted-access, such as DHS, MICS, or IPUMS.
4. Where the paper `.tex` source file is located within the working folder.

Run the Required Files check. If the check passes, begin Phase 1.

If at any point a decision requires user judgment, such as a variable that appears in one table but might be derivable from another, pause and ask before proceeding.

## Phase 1: Read All Code and Build the Dependency Map

Before touching any data file, read every script in the working folder.

### Per-script trace

For each script, record:

1. which raw file or files it reads
2. which variables it uses from each raw file, by exact name
3. which variables it creates or transforms
4. which clean or intermediate file or files it writes
5. which clean or intermediate file or files other scripts read from it

Do not guess. Read the actual code. If a variable appears inside a wildcard such as `keep b2_* b4_*`, expand the wildcard against the actual raw columns and identify every retained variable.

### Per-output chains

The per-script trace is not enough. For every table and figure in the paper, assemble the full chain from output back to raw data, crossing scripts wherever intermediate analyses feed a later step:

`paper output <- producing script <- clean/intermediate file(s) <- cleaning/build script(s) <- raw file(s) <- raw variable(s)`

If an output depends on analysis performed across several scripts, every link in that chain must appear in the map. A chain with a missing link means Phase 1 is not complete.

## Phase 2: Dependency Map Approval Gate

This phase is a hard stop. No file is created, modified, or deleted in the project before the user approves the map. The only file written in this phase is the map itself.

1. Write the full map to `dependency_map.md` in the working folder root.
2. For each paper output, render the chain as a tree, for example:

```text
T1A (Table 1, Panel A)
└── code/03_tables/t1a.do
    └── data/clean/analysis.dta
        └── code/01_build/build.do
            ├── data/clean/hh.dta <- code/00_cleaning/clean_hh.do <- data/raw/hh_survey.csv [hhid, weight, region]
            └── data/clean/rain.dta <- code/00_cleaning/clean_rain.do <- data/raw/rainfall.csv [cell_id, precip_mm]
```

3. Include a section listing every raw variable proposed for deletion, grouped by file, with the reason each is unused.
4. Include a section listing anything ambiguous: variables referenced dynamically, scripts that could not be fully traced, outputs in the paper with no producing script found.
5. Present the map to the user and say:

> "This dependency map drives all pruning and restructuring that follows. Please review it, especially the proposed deletions and the ambiguous items. Reply with approval or corrections. I will not modify any file until you approve."

6. Halt and wait. Apply corrections to the map and re-present until the user gives explicit approval. Record the approval in `dependency_map.md` with the date.

## Phase 3: Create the Replication Package Copy

Only after Phase 2 approval:

1. Create `replication_package/` in the working folder root.
2. Copy into it all scripts, all raw data files named in the approved map, the paper outputs needed for verification, and the approved `dependency_map.md`.
3. Do not copy unrelated files, editor artifacts, or `.DS_Store` files.
4. From this point on, every phase operates inside `replication_package/` only. The original files are the untouched reference for any restoration or comparison.

## Phase 4: Create the Data Inventory Document

Place `data_inventory.qmd` in the package root.

Render it with `xelatex` (`pdf-engine: xelatex`). Use fonts that are actually present in the local TeX installation, via absolute fontspec paths, rather than relying on automatic font installation. TeX Gyre Termes (serif), Heros (sans), and Cursor (mono) are reliable choices on a standard TeX Live installation. Verify the actual TeX Live path on the machine before hardcoding it.

Fix table overflow explicitly with `tbl-colwidths`. Every table with a long text column needs explicit percentage widths summing to 100. For landscape dependency matrices, use raw LaTeX with fixed-width columns, reduced `tabcolsep`, and `\footnotesize` so all columns fit the landscape text width.

### Document structure

**Section 1: Paper Output Reference.** A table listing every paper table and figure with a short reference code (T1A, F2, TA3), the full paper label exactly as it appears, and the producing script.

**Section 2: Raw Data Files.** One subsection per raw file: file path, original variable count, retained count, a variable table (name, type or role, required for which outputs using Section 1 codes), a short paragraph on why the file cannot be deleted, and a paragraph listing dropped variables and why. Tag each file as raw or restricted.

**Section 3: Clean Data Files.** One subsection per clean file: file path, producing script, unit of observation, a variable table (name, role, required for), and why it cannot be deleted. Tag each file as clean and, where relevant, pre-computed.

**Section 4: Dependency Matrix.** A landscape cross-reference with paper outputs as rows and clean files as columns, marking each cell where the output requires the file.

**Section 5: Variables Removed and Why.** A table listing every file where variables were deleted, the exact names removed, and the reason. This section must match the approved Phase 2 deletion list exactly.

**Section 6: Key Takeaway Box.** How to reproduce all outputs, which command to run, and whether restricted data access is needed.

Compile the document and confirm `data_inventory.pdf` is produced without LaTeX errors before moving to Phase 5.

## Phase 5: Prune Raw Data Files (In the Copy Only)

Prune raw files inside `replication_package/data/raw/` using the approved map and the inventory as the only authorities.

Rules:

- Delete only the variables on the approved Phase 2 deletion list. Nothing else.
- Never modify a retained variable: no rounding, no recoding, no renaming, no reordering of rows.
- Never add variables to raw data files.
- For CSV files, write a script (Python preferred) that keeps only the required columns by exact name and preserves values safely. Handle non-standard line endings explicitly. Read with `float_precision='round_trip'` in pandas, or `dtype=str` for ID columns, so values survive the round trip unchanged.
- For Excel files, use `openpyxl` with `data_only=True` to read cached values. If formula cells have no cached values, do not prune that file. Mark the dependent clean file as pre-computed and add a skip guard instead.
- For Stata `.dta` files, use `keep varlist` plus `saveold`, or Python `pyreadstat`, keeping only the approved variables.

After pruning:

- Record before and after variable counts in the data inventory.
- Verify that every variable expected by the cleaning scripts still exists in the pruned file.
- If a required variable was dropped accidentally, restore it from the original file in the working folder, which is untouched by design.

## Phase 6: Fix and Standardize All Code

Apply these standards to every Stata, R, and Python script in the package.

### Path discipline

- Every script must use a single project root set by `master.do` (a `$root` global or equivalent) and reference all files as `"$root/..."`.
- No hardcoded absolute paths.
- No relative paths that assume a working directory other than the root.

### Output paths

- All tables are written to `"$root/output/tables/"`. No table may exist only in the console log.
- All figures are exported to `"$root/output/figures/"`.

### Graceful pre-computed skips

Any cleaning script whose raw inputs include restricted-access data must begin, immediately after the root path block, with:

```stata
capture confirm file "$root/data/clean/output_file.dta"
if _rc == 0 {
    di as text "NOTE: Pre-computed file found; skipping."
    exit
}
```

### Defensive drops

If a cleaning script drops variables that may no longer exist after pruning, use `capture drop varlist` so the script does not fail unnecessarily.

## Phase 7: Build `master.do`

Create `master.do` in the package root. It must:

1. set `global root` to the current directory, with a comment showing how to override with an absolute path
2. create `output/tables/` and `output/figures/` if they do not exist
3. call every cleaning script in dependency order, as given by the approved map
4. call the build script that assembles the primary analysis dataset
5. call figure-producing scripts
6. call table-producing scripts
7. include a top comment block with the paper citation, software versions, required packages, and restricted-data notes

## Phase 8: Write the Package README

The package README must contain:

1. paper citation with DOI and journal
2. authors and affiliations
3. software requirements, including versions and package install commands
4. data access details for every raw file: open or restricted, and the registration or download URL for restricted files
5. step-by-step replication instructions: set root, run any pre-processing, run `master.do`
6. output map linking every paper table and figure to its producing script and output file path
7. data provenance note stating that retained raw variables were not modified, only unused variables removed, citing `data_inventory.pdf` and `dependency_map.md`
8. annotated directory structure

Write plainly. A new research assistant should be able to run the package without reverse engineering the codebase. Do not use em-dashes anywhere in the README.

## Phase 9: Verify End to End

1. Run `master.do` inside `replication_package/` from a clean state, with no pre-existing outputs.
2. Confirm every table file appears in `output/tables/`.
3. Confirm every figure file appears in `output/figures/`.
4. Confirm no script errors out.
5. If a script fails because restricted raw data is absent, add a graceful skip guard (Phase 6 rule) rather than weakening the pruning.
6. Re-render `data_inventory.pdf` after any final edits.

## Target Package Structure

```text
replication_package/
├── README.md
├── master.do
├── dependency_map.md           <- approved in Phase 2
├── data_inventory.qmd          <- Phase 4 output
├── data_inventory.pdf
├── code/
│   ├── 00_data_cleaning/
│   ├── 01_build/
│   ├── 02_figures/
│   └── 03_tables/
├── data/
│   ├── raw/                    <- untouched values; only approved unused cols deleted
│   │   └── README.md
│   └── clean/                  <- produced by code, or pre-computed plus skip guard
│       └── README.md
└── output/
    ├── figures/
    └── tables/
```

## Common Pitfalls

| Pitfall | Prevention |
|:---|:---|
| Deleting a variable used only inside a wildcard (`keep b2_*`) | Expand wildcards against the actual column list in Phase 1 |
| Excel formula cells returning empty after pruning | Use `data_only=True`; if no cached values, mark the clean file pre-computed instead of pruning |
| `drop v11-v14` failing after pruning removed those columns | Use `capture drop` |
| Identifier living in a different file than expected (for example `hhid` in the household roster, not the individual file) | Check variable location in Phase 1 before listing deletions |
| Raw values silently changed by a CSV round trip | `float_precision='round_trip'` or `dtype=str` for IDs |
| Hardcoded `cd` breaking on other machines | Only `global root` in `master.do`; `"$root/..."` everywhere else |
| tlmgr remote mismatch blocking font auto-install | Absolute `Path=` in fontspec to bypass tlmgr |
| Pre-computed clean file present but stale | Note the pre-computation date and source machine in the README |
| Pruning before approval | Phase 2 is a hard gate; no project file changes before recorded approval |

## Good Final Reporting

Summarize:

- the package path and what was created or standardized
- that the original project folder was not modified
- whether `data_inventory.pdf` compiled
- what was pruned, by file, against the approved list
- whether `master.do` ran end to end and which outputs were produced
- what restricted-data limitations remain

Be explicit about remaining uncertainty. Do not claim full reproducibility if restricted inputs or missing software still block a clean run.

## Invocation

- Claude: invoke with `/replication-repo` or by asking for a replication package while this skill is installed.
