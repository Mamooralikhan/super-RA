# Script Templates

Copy-paste heads for each language. Every standardized script gets, in this order: the header, the path anchor, the packages, the version check, then the analysis. Replace the example names with the real ones. Stamp real dates in `YYYY-MM-DD`.

The climb to `ROOT` uses `..` segments. Set the number of segments to the depth of the script below the project root. A script at `code/01_clean/clean.R` is two levels down, so it climbs `.., ..`.

## R

R has no clean way to find a running script's own path in base R across every run mode. This skill uses the `this.path` package, which resolves the path correctly under `source()`, `Rscript`, RStudio, and `knitr`. This is the one package dependency, and it is not the `here` package.

```r
# ============================================================
# Author:   Sara Khan
# Purpose:  Clean the household survey and build the analysis panel
# Created:  2026-06-17    Updated: 2026-06-17
# Inputs:   data/raw/hh_survey.csv
# Outputs:  data/clean/analysis.rds
# ============================================================

# --- Path anchor: this file's own location is the origin ----
library(this.path)
SCRIPT_DIR <- this.path::this.dir()
ROOT       <- normalizePath(file.path(SCRIPT_DIR, "..", ".."))   # climb to project root
# Reference everything downward from ROOT, never an absolute path:
#   file.path(ROOT, "data", "raw", "hh_survey.csv")

# --- Packages -----------------------------------------------
library(data.table)
library(fixest)

# --- Provenance check (offline, speaks only on change) ------
source(file.path(ROOT, ".provenance", "provenance.R"))
prov_check(c("data.table", "fixest"))
# To halt instead of warn on a baseline mismatch in a final results script:
#   options(PROV_STRICT = TRUE)

# --- Analysis begins ----------------------------------------
hh <- data.table::fread(file.path(ROOT, "data", "raw", "hh_survey.csv"))
```

## Python

`Path(__file__)` gives the script's own location for a normal `.py` run. In a notebook or REPL `__file__` is undefined, so the template falls back to the current directory.

```python
# ============================================================
# Author:   Sara Khan
# Purpose:  Clean the household survey and build the analysis panel
# Created:  2026-06-17    Updated: 2026-06-17
# Inputs:   data/raw/hh_survey.csv
# Outputs:  data/clean/analysis.parquet
# ============================================================

# --- Path anchor: this file's own location is the origin ----
from pathlib import Path
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:                 # notebook or interactive session
    SCRIPT_DIR = Path.cwd()
ROOT = SCRIPT_DIR.parents[1]      # climb to project root; change the index to match depth
# Reference downward from ROOT, never an absolute path:
#   ROOT / "data" / "raw" / "hh_survey.csv"

# --- Packages -----------------------------------------------
import pandas as pd

# --- Provenance check (offline, speaks only on change) ------
import sys
sys.path.insert(0, str(ROOT / ".provenance"))
from provenance import prov_check
prov_check(["pandas", "numpy"])   # pass strict=True to halt on a baseline mismatch

# --- Analysis begins ----------------------------------------
hh = pd.read_csv(ROOT / "data" / "raw" / "hh_survey.csv")
```

## Stata

Stata cannot self-locate a running do-file. The honest options are to run the do-file from the project root, so `c(pwd)` is the root, or to edit the single `global ROOT` line once. The marker assertion below fails loudly if the anchor is wrong, so a misrun do-file stops instead of writing to the wrong place. The `version` directive pins core-command behavior to one Stata version, which is Stata's built-in reproducibility control.

```stata
* ============================================================
* Author:   Sara Khan
* Purpose:  Clean the household survey and build the analysis panel
* Created:  2026-06-17    Updated: 2026-06-17
* Inputs:   data/raw/hh_survey.csv
* Outputs:  data/clean/analysis.dta
* ============================================================

version 18.0   // pin core-command behavior to this Stata version

* --- Path anchor: Stata cannot self-locate a do-file --------
* Run this do-file from the project root, or set ROOT by hand once.
global ROOT "`c(pwd)'"
capture confirm file "${ROOT}/.provenance/.projroot"
if _rc {
    di as error "Not at project root: ${ROOT}."
    di as error "Run this do-file from the root, or set: global ROOT \"<absolute path>\""
    exit 601
}
* Reference downward from ROOT, never an absolute path:
*   "${ROOT}/data/raw/hh_survey.csv"

* --- Provenance check (offline, partial on Stata) -----------
do "${ROOT}/.provenance/provenance.do"   // declares the prov_check program
prov_check reghdfe estout                 // ado commands to record (versions are partial)

* --- Analysis begins ----------------------------------------
import delimited "${ROOT}/data/raw/hh_survey.csv", clear
```

## Header fields

| Field | Rule |
|:---|:---|
| Author | From the user, or git config with the user's confirmation. Never invented. |
| Purpose | One line. For a new script, from the user. For a retrofit, inferred from code and confirmed by the user before it is written. |
| Created | The file's existing creation date if known, otherwise today. |
| Updated | Today, on every standardization or material edit. |
| Inputs | Project-relative paths the script reads, for example `data/raw/...`. |
| Outputs | Project-relative paths the script writes, for example `data/clean/...`. |

## Path rules, all languages

- The script's own file location is the only anchor. Climb up with `..` segments to reach `ROOT`.
- Build every other path downward from `ROOT`. Never hardcode an absolute path.
- Never reference the Box, Dropbox, OneDrive, or home prefix. Those differ per machine and are exactly what file-anchoring removes.
- Use the language's path join (`file.path`, `Path` division, Stata forward slashes), not hand-concatenated separators, so Windows and macOS both work.
- Quote paths that may contain spaces or parentheses, common in Box and Dropbox folder names.
