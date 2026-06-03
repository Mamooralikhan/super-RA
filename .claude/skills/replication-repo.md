# Skill: Build a Replication Repository

Use this skill when the user wants an existing empirical project converted into a clean replication repository with explicit safeguards, documented dependencies, and a single reproducible entry point.

This skill is intentionally strict. It should preserve the exact logic of the source project while making the repository portable, documented, and reproducible. The agent must follow the phases in order, verify each one before continuing, and stop for user judgment when the evidence is ambiguous.

You are building a clean, self-contained replication repository for an academic paper. Work through the phases below in strict order. Do not skip a phase. Do not move to the next phase until the current one is complete and verified.

---

## Absolute Rules (Enforce Throughout)

**Raw data integrity is inviolable.**

- Raw data files may have variables (columns) deleted entirely — but only variables that are confirmed unused by any script.
- A variable's values must never be modified by any amount, including rounding, reordering, or recoding.
- A variable's name must never be changed in raw data files.
- All transformation, renaming, recoding, and construction of analysis variables happens in cleaning scripts that write to `data/clean/`.
- Clean data is always produced by code (`.do`, `.R`, `.py`) running on raw data. Pre-computed clean files are allowed only when the cleaning script depends on restricted data that cannot be distributed; in that case the script must include a graceful skip guard (`capture confirm file ... if _rc == 0 { exit }`) so it does not fail on machines that lack the restricted source.
- All regression tables and figures must read from `data/clean/`, never from `data/raw/` directly.

---

## Phase 1 — Read All Code and Build the Variable Map

Before touching any data file, read every script in the repository.

For each script, trace:
1. Which raw file(s) it reads
2. Which variables it uses from each raw file (exact column/variable names)
3. Which variables it creates or transforms
4. Which clean file(s) it writes
5. Which clean file(s) the analysis scripts read
6. Which specific paper table(s) and figure(s) each clean variable feeds

Record this as a complete map: `raw file → variable → clean variable → paper output`.

Do not guess. Read the actual code. If a variable appears in a wildcard (`keep b2_* b4_*`), expand the wildcard against the actual columns in the raw file to identify every variable that gets retained.

---

## Phase 2 — Create the Data Inventory Document (`data_inventory.qmd`)

Place this file in the repository root (outside `data/` and `code/`).

Render it with **xelatex** (`pdf-engine: xelatex`). Use fonts available in the local TeX Live installation via absolute fontspec paths — do not rely on tlmgr auto-install. TeX Gyre Termes (serif), Heros (sans), and Cursor (mono) are reliable choices if the system has a TeX Live 2025 installation:

```latex
\setmainfont[
  Path=/usr/local/texlive/2025/texmf-dist/fonts/opentype/public/tex-gyre/,
  BoldFont=texgyretermes-bold.otf,
  ItalicFont=texgyretermes-italic.otf,
  BoldItalicFont=texgyretermes-bolditalic.otf
]{texgyretermes-regular.otf}
\setsansfont[
  Path=/usr/local/texlive/2025/texmf-dist/fonts/opentype/public/tex-gyre/,
  BoldFont=texgyreheros-bold.otf,
  ItalicFont=texgyreheros-italic.otf
]{texgyreheros-regular.otf}
\setmonofont[Scale=0.85,
  Path=/usr/local/texlive/2025/texmf-dist/fonts/opentype/public/tex-gyre/,
  BoldFont=texgyrecursor-bold.otf
]{texgyrecursor-regular.otf}
```

Fix column overflow in all pipe tables using `tbl-colwidths`. Every table that has a "Required for" or long text column must have explicit percentage widths summing to 100, e.g.:

```markdown
: Caption. {#tbl-id tbl-colwidths="[20,45,35]"}
```

For landscape dependency matrices, use raw LaTeX with `p{Xcm}` columns, `\setlength{\tabcolsep}{2pt}`, and `\footnotesize` so all columns fit within the landscape text width (~22 cm for standard letter paper with 1.1-inch margins).

### Document structure

**Section 1 — Paper Output Reference**
A table listing every paper table and figure with:
- Short reference code (T1A, T2B, TA3, F1, FCP, etc.)
- Full paper label (exact name and number as it appears in the paper)
- Producing script

**Section 2 — Raw Data Files**
One subsection per raw file. For each file:
- File path, original column/variable count, retained count
- A variable table: variable name | type/role | Required for (using the reference codes from Section 1)
- "Why it cannot be deleted" paragraph
- "Variables/columns removed" paragraph with exact names of what was dropped and why

Tag each file as `\rawtag` (raw input) or `\restricttag` (restricted access, registration required).

**Section 3 — Clean Data Files**
One subsection per clean file. For each file:
- File path, producing script, structure (unit of observation)
- A variable table: variable name | role | Required for
- "Why it cannot be deleted" paragraph

Tag each file as `\cleantag` and, where applicable, `\pretag` (pre-computed).

**Section 4 — Dependency Matrix (landscape)**
A longtable with paper outputs as rows and clean data files as columns. Mark each cell where the output requires the file. This is the master cross-reference for the repository.

**Section 5 — Variables Removed and Why**
A table listing every file where variables were deleted, the variable names removed, and the reason (not referenced by any script / GIS metadata not consumed / documentation-only column / etc.).

**Section 6 — Key Takeaway Box**
A tcolorbox summarising: how to reproduce all outputs, which command to run, and whether any restricted data access is needed.

Compile the document and confirm `data_inventory.pdf` is produced without LaTeX errors before proceeding to Phase 3.

---

## Phase 3 — Prune Raw Data Files

Using the variable map from Phase 1 and the inventory from Phase 2 as authoritative references, prune every raw data file to its minimum necessary set.

### Rules
- **Delete entire variables** that do not appear in the Phase 1 variable map for that file. Nothing else.
- **Never modify a retained variable**: no rounding, no recoding, no renaming, no reordering of rows.
- **Never add variables** to raw data files.
- For CSV files: write a script (Python preferred) that reads the file, keeps only the required columns by exact name, and writes the result back. Handle non-standard line endings (old Mac `\r`, Windows `\r\n`) explicitly.
- For Excel files: use `openpyxl` with `data_only=True` to read cached values. If cells contain formulas with no cached values, do not prune that file — instead mark the corresponding clean file as pre-computed and add a graceful skip guard to the cleaning script.
- For Stata `.dta` files: write a Stata script (`keep varlist`, `saveold`) or use Python `pyreadstat`. Keep only the variables from the Phase 1 list.
- After pruning, record the before/after column counts in the data inventory document.

### Verification
After pruning, check that every column name in the original `keep` lists in the cleaning scripts still exists in the pruned file. If a variable was accidentally dropped, restore it from the original.

---

## Phase 4 — Fix and Standardise All Code

Apply these changes to every do-file, R script, and Python script in the repository.

### Path discipline
- Every script must set `$root` from a global (set by `master.do`) and use `"$root/..."` for all file paths.
- No hardcoded absolute paths (no `cd "/Users/someone/Dropbox/..."`).
- No relative paths that assume a working directory other than `$root`.

### Output paths
- All tables must be written to `"$root/output/tables/"` using `estout ... using "..."` or equivalent. No table may print only to the console.
- All figures must be exported to `"$root/output/figures/"` using `graph export "$root/output/figures/filename.ext", replace` or equivalent.

### Graceful pre-computed skips
Any cleaning script whose raw inputs include restricted-access data must begin with:

```stata
capture confirm file "$root/data/clean/output_file.dta"
if _rc == 0 {
    di as text "NOTE: Pre-computed file found; skipping."
    exit
}
```

Place this immediately after the root path block, before any `use` or `insheet` commands.

### Defensive drops
If a cleaning script drops variables that may no longer exist after raw data pruning, use `capture drop varlist` to suppress r(111) errors.

---

## Phase 5 — Build `master.do`

Create `master.do` in the repository root. It must:

1. Set `global root` to `.` (current directory) with a comment showing how to override with an absolute path.
2. Create `output/tables/` and `output/figures/` directories if they do not exist (`capture mkdir`).
3. Call every cleaning script in dependency order.
4. Call the build script (`fcr_build.do` or equivalent) that assembles the primary analysis dataset from clean inputs.
5. Call figure-producing scripts.
6. Call table-producing scripts.
7. Include a comment block at the top listing: paper citation, software versions required, required Stata packages, and notes on restricted data.

---

## Phase 6 — Write `README.md`

The README must contain:

1. **Paper citation** — full reference with DOI and journal
2. **Authors and affiliations**
3. **Software requirements** — Stata version, R version, required packages (with install commands)
4. **Data access** — table listing every raw data file, whether it is open or restricted, and registration/download URL for restricted files
5. **Replication instructions** — step-by-step: set root path, run any pre-processing scripts (e.g. R raster extraction), run `master.do`
6. **Output map** — table linking every paper table and figure to the script that produces it and the output file path
7. **Data provenance note** — statement that raw data variables have not been modified, only unused variables removed, citing the data inventory document
8. **Directory structure** — annotated tree of the repository

---

## Phase 7 — Verify End-to-End

1. Run `master.do` from a clean state (no pre-existing outputs).
2. Confirm every table file appears in `output/tables/`.
3. Confirm every figure file appears in `output/figures/`.
4. Check that no script errors out.
5. If a script fails because a restricted raw file was pruned in a way that breaks the cleaning script, add a graceful skip guard (Phase 4 rule) rather than reverting the pruning.
6. Re-render `data_inventory.pdf` to confirm it still compiles after any final edits.

---

## Repository Directory Structure (Target)

```
repo_root/
├── README.md
├── master.do
├── data_inventory.qmd          ← Phase 2 output
├── data_inventory.pdf          ← compiled from above
├── code/
│   ├── 00_data_cleaning/       ← one script per raw → clean transformation
│   ├── 01_build/               ← assembles primary analysis dataset
│   ├── 02_figures/             ← figure-only scripts
│   └── 03_tables/              ← table-producing scripts
├── data/
│   ├── raw/                    ← untouched values; only unused cols deleted
│   │   └── README.md           ← lists every file and what was pruned
│   └── clean/                  ← produced by code, or pre-computed + skip guard
│       └── README.md           ← lists every file, producing script, and paper outputs
└── output/
    ├── figures/
    └── tables/
```

---

## Common Pitfalls to Avoid

| Pitfall | Prevention |
|:--------|:-----------|
| Deleting a variable used inside a wildcard (`keep b2_*`) | Expand wildcards against actual column list before pruning |
| Excel formula cells returning `None` after pruning with openpyxl | Use `data_only=True`; if cells have no cached value, mark clean file pre-computed |
| Stata `drop v11-v14` fails after CSV pruning removed those columns | Use `capture drop v11-v14` |
| `hhid not found` in DHS individual file | `hhid` lives in the household roster, not the individual file; check variable location before pruning |
| tlmgr remote mismatch blocking xelatex font auto-install | Use absolute `Path=` in fontspec `\setmainfont` to bypass tlmgr |
| Hardcoded working directory in `cd` command breaks on other machines | Set only `global root` in `master.do`; use `cd "$root"` everywhere else |
| Raw file values silently changed by CSV round-trip | Read with `float_precision='round_trip'` in pandas, or use `dtype=str` for ID columns |
| Pre-computed clean file present but stale (different from what code would produce) | Add a comment in the README noting the pre-computation date and source machine |

---

## Invocation

When this skill is invoked, ask the user for:
1. The path to the existing code directory (or confirm the current working directory contains the repo)
2. The paper title and journal (for README and data_inventory header)
3. Whether any data files are restricted-access (DHS, MICS, IPUMS, etc.)

Then begin Phase 1. Report completion of each phase before starting the next. If you encounter a decision that requires user judgement (e.g. a variable that appears in one table but might be derivable from another), pause and ask before proceeding.
