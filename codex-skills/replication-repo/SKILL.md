---
name: replication-repo
description: Build a clean, self-contained replication repository for an academic paper by reading all code, mapping every raw-to-clean-to-output dependency, documenting data provenance, pruning only unused raw variables, standardizing paths and outputs, creating a master entry point, and verifying end-to-end reproducibility. Use when the user wants a reproducible replication package, a data inventory, standardized project structure, or a careful replication-repository conversion.
---

# Replication Repo

Use this skill when the user wants an existing empirical project converted into a clean replication repository with explicit safeguards, documented dependencies, and a single reproducible entry point.

This skill is intentionally strict. It should preserve the exact logic of the source project while making the repository portable, documented, and reproducible. Follow the phases in order. Do not skip a phase. Do not move to the next phase until the current one is complete and verified.

## Before You Start

Ask the user for:

1. The path to the existing code directory, or confirm the current working directory contains the repo
2. The paper title and journal, for the README and `data_inventory` header
3. Whether any data files are restricted-access, such as DHS, MICS, or IPUMS

Then begin Phase 1.

If you encounter a decision that requires user judgment, such as a variable that appears in one table but might be derivable from another, pause and ask before proceeding.

## Absolute Rules

Raw data integrity is inviolable.

- Raw data files may have variables removed, but only variables confirmed unused by every script.
- The values of a retained raw variable must never be modified, even by rounding, recoding, or reordering.
- The name of a retained raw variable must never be changed.
- All transformations, renaming, recoding, and construction of analysis variables happen in cleaning scripts that write to `data/clean/`.
- Clean data is produced by code. Pre-computed clean files are allowed only when the required raw data cannot be distributed. In that case, the cleaning script must include a graceful skip guard so the repository does not fail on machines without the restricted source.
- Regression tables and figures must read from `data/clean/`, not from `data/raw/` directly.

## Phase 1: Read All Code and Build the Variable Map

Before touching any data file, read every script in the repository.

For each script, trace:

1. which raw file or files it reads
2. which variables it uses from each raw file
3. which variables it creates or transforms
4. which clean file or files it writes
5. which clean file or files the analysis scripts read
6. which specific paper tables and figures each clean variable feeds

Record this as a complete map:

`raw file -> variable -> clean variable -> paper output`

Do not guess. Read the actual code. If a variable appears inside a wildcard such as `keep b2_* b4_*`, expand the wildcard against the actual raw columns and identify every retained variable.

## Phase 2: Create the Data Inventory Document

Place `data_inventory.qmd` in the repository root.

Render it with `xelatex`. Use local fonts that are actually available in the environment rather than relying on automatic font installation. Fix table overflow explicitly with `tbl-colwidths`. For landscape dependency matrices, use a layout that fits within the rendered page width.

The document should contain:

### Section 1: Paper Output Reference

A table listing every paper table and figure with:

- short reference code
- full paper label exactly as shown in the paper
- producing script

### Section 2: Raw Data Files

One subsection per raw file with:

- file path
- original variable count
- retained variable count
- variable table with variable name, type or role, and required outputs
- a short paragraph explaining why the file cannot be deleted
- a paragraph listing dropped variables and why they were removed

Tag each file as raw or restricted where relevant.

### Section 3: Clean Data Files

One subsection per clean file with:

- file path
- producing script
- unit of observation or structure
- variable table with variable name, role, and required outputs
- a short paragraph explaining why the file cannot be deleted

Tag each file as clean and, where relevant, pre-computed.

### Section 4: Dependency Matrix

A landscape cross-reference showing which clean files feed which paper outputs.

### Section 5: Variables Removed and Why

A table listing every file where variables were deleted, the exact variable names removed, and the reason.

### Section 6: Key Takeaway Box

A short summary of:

- how to reproduce the outputs
- which command to run
- whether restricted data access is needed

Compile the document and confirm `data_inventory.pdf` is produced without LaTeX errors before moving to Phase 3.

## Phase 3: Prune Raw Data Files

Use the Phase 1 map and Phase 2 inventory as the authoritative guides.

Rules:

- delete only variables that do not appear in the Phase 1 map for that file
- never modify a retained variable
- never add variables to raw data files

Format-specific guidance:

- For CSV files, use a script that keeps only the required columns by exact name and preserves values safely.
- For Excel files, use cached values only. If formulas have no cached values, do not prune the file. Mark the dependent clean file as pre-computed instead.
- For Stata files, use a Stata or Python workflow that keeps only the required variables.

After pruning:

- record before and after variable counts in the inventory
- verify that every variable expected by the cleaning scripts still exists
- if a required variable was dropped accidentally, restore it from the original

## Phase 4: Fix and Standardize All Code

Apply these standards to every Stata, R, and Python script.

### Path Discipline

- Use a single project root set by `master.do`.
- Remove hardcoded absolute paths.
- Remove fragile relative paths that assume a specific working directory.

### Output Paths

- Write tables to `output/tables/`.
- Write figures to `output/figures/`.
- Do not leave key outputs available only in the console.

### Graceful Pre-Computed Skips

If a cleaning script depends on restricted raw data and the repository ships a pre-computed clean file, add a skip guard near the top of the script so the workflow does not fail when the restricted source is missing.

### Defensive Drops

If a cleaning script drops variables that may no longer exist after pruning, use defensive drop logic so the script does not fail unnecessarily.

## Phase 5: Build `master.do`

Create `master.do` in the repository root.

It must:

1. set the project root
2. create `output/tables/` and `output/figures/` if needed
3. call every cleaning script in dependency order
4. call the build script that assembles the analysis dataset
5. call figure-producing scripts
6. call table-producing scripts
7. include a top comment block with the paper citation, software versions, required packages, and restricted-data notes

## Phase 6: Write the Target Repository README

The replication repository README must contain:

1. paper citation
2. authors and affiliations
3. software requirements
4. data access details for each raw file
5. replication instructions
6. output map linking paper outputs to scripts and files
7. data provenance note stating that retained raw variables were not modified
8. annotated directory structure

Write plainly. A new RA should be able to understand how to run the repository without reverse engineering the codebase.

## Phase 7: Verify End to End

1. run `master.do` from a clean state
2. confirm every table appears in `output/tables/`
3. confirm every figure appears in `output/figures/`
4. confirm no script errors out
5. if restricted-data pruning breaks a script, add a graceful skip guard rather than undoing the pruning rule
6. re-render `data_inventory.pdf` after final edits

## Target Repository Structure

```text
repo_root/
├── README.md
├── master.do
├── data_inventory.qmd
├── data_inventory.pdf
├── code/
│   ├── 00_data_cleaning/
│   ├── 01_build/
│   ├── 02_figures/
│   └── 03_tables/
├── data/
│   ├── raw/
│   │   └── README.md
│   └── clean/
│       └── README.md
└── output/
    ├── figures/
    └── tables/
```

## Common Pitfalls

- deleting a variable that is only referenced through a wildcard keep list
- pruning Excel sources whose formulas do not have cached values
- letting path fixes introduce hidden machine-specific assumptions
- silently changing raw values during CSV round-trips
- reverting pruning when a skip guard would solve the restricted-data case more honestly

## Good Final Reporting

Summarize:

- what files were created or standardized
- whether `data_inventory.pdf` compiled
- whether raw data were pruned and how
- whether `master.do` ran successfully
- what restricted-data limitations remain

Be explicit about remaining uncertainty. Do not claim full reproducibility if restricted inputs or missing software still block a clean run.
