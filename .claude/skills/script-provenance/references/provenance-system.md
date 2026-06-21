# Provenance System

This is the project-level layer that turns the in-script version check into a cross-team record. It is offline by default. The only network call is the optional latest-release lookup inside the on-demand reconcile.

## Directory layout

All of it lives inside the project root, under one folder, so it travels with the project through git or Box or Dropbox:

```text
<ROOT>/.provenance/
├── .projroot              <- empty marker; lets Stata assert it is at the root
├── provenance.R           <- R runtime helper (base R only)
├── provenance.py          <- Python runtime helper (standard library only)
├── provenance.do          <- Stata runtime helper (partial)
├── baseline.tsv           <- blessed versions that produced the committed results
├── reconcile.R            <- on-demand team report (R; one Python variant is fine too)
├── members/
│   ├── sara_macbook.tsv         <- one file per member, current state, overwritten each run
│   ├── sara_macbook.history.tsv <- append-only log of detected changes
│   └── ahmed_thinkpad.tsv
└── reports/
    └── 2026-06-17_provenance.md <- dated reconcile output
```

Why one file per member: on a shared Box or Dropbox folder there is no merge, so a single shared ledger would clobber or spawn conflicted copies. Each member writing only their own file removes the contention. Reconcile merges them.

## Identity resolution

Identity is per machine, not per project, because a shared Box folder gives every member the same files. Resolution order:

1. `~/.config/script-provenance/whoami`, a one-line readable label the member sets once, for example `Sara, MacBook`.
2. Fallback: operating system username joined with the host name, for example `skhan24@host`.

Each member must be unique. Reconcile warns if two ledger files resolve to the same label. The member filename is the label with non-alphanumeric characters replaced by underscores.

## Ledger schema

Tab-separated, so every language reads and writes it with no extra package. One row per package observed on the most recent run.

| Column | Meaning |
|:---|:---|
| `package` | Package or ado name |
| `version` | Exact installed version string |
| `language` | `R`, `python`, or `stata` |
| `lang_version` | R, Python, or Stata version |
| `member` | Identity label |
| `date` | `YYYY-MM-DD` of this run |

`baseline.tsv` uses the same columns plus `blessed_by` and `blessed_date`.

## Runtime behavior

On each run the helper:

1. Resolves identity and reads the package versions actually loaded.
2. Reads the member's own previous `members/<member>.tsv` (their last run) and `baseline.tsv` (blessed versions).
3. Compares with a version-aware comparison, not raw string order.
4. If nothing changed since the last run and nothing differs from baseline, it stays silent.
5. Otherwise it prints one concise block listing each changed package as `old -> new` and each baseline difference, says the change may affect results, and tells the user to run reconcile. It does not stop, unless strict mode is on and a baseline difference exists.
6. Overwrites `members/<member>.tsv` with the current state and appends any change to `members/<member>.history.tsv`.

No network. No per-package spam in steady state.

## R helper (base R only)

```r
# .provenance/provenance.R  -- offline, base R only, no extra packages.

.prov_member <- function() {
  cfg <- path.expand("~/.config/script-provenance/whoami")
  if (file.exists(cfg)) {
    id <- trimws(readLines(cfg, n = 1, warn = FALSE))
    if (length(id) && nzchar(id)) return(id)
  }
  paste0(Sys.info()[["user"]], "@", Sys.info()[["nodename"]])
}

prov_check <- function(packages, strict = isTRUE(getOption("PROV_STRICT"))) {
  pdir   <- file.path(ROOT, ".provenance")
  member <- .prov_member()
  safe   <- gsub("[^A-Za-z0-9._-]", "_", member)
  cur <- data.frame(
    package      = packages,
    version      = vapply(packages, function(p) as.character(packageVersion(p)), character(1)),
    language     = "R",
    lang_version = paste(R.version$major, R.version$minor, sep = "."),
    member       = member,
    date         = as.character(Sys.Date()),
    stringsAsFactors = FALSE
  )
  mdir  <- file.path(pdir, "members"); if (!dir.exists(mdir)) dir.create(mdir, recursive = TRUE)
  mfile <- file.path(mdir, paste0(safe, ".tsv"))
  prev  <- if (file.exists(mfile))                  read.delim(mfile, stringsAsFactors = FALSE) else NULL
  base  <- if (file.exists(file.path(pdir, "baseline.tsv"))) read.delim(file.path(pdir, "baseline.tsv"), stringsAsFactors = FALSE) else NULL

  msgs <- character(0)
  for (i in seq_len(nrow(cur))) {
    p <- cur$package[i]; v <- cur$version[i]
    if (!is.null(prev)) { pv <- prev$version[prev$package == p]
      if (length(pv) == 1 && compareVersion(pv, v) != 0)
        msgs <- c(msgs, sprintf("  %s changed since your last run: %s -> %s", p, pv, v)) }
    if (!is.null(base)) { bv <- base$version[base$package == p]
      if (length(bv) == 1 && compareVersion(bv, v) != 0)
        msgs <- c(msgs, sprintf("  %s differs from baseline: you %s, blessed %s", p, v, bv)) }
  }

  write.table(cur, mfile, sep = "\t", row.names = FALSE, quote = FALSE)
  if (length(msgs)) {
    hfile <- file.path(mdir, paste0(safe, ".history.tsv"))
    hist  <- data.frame(date = cur$date[1], member = member, event = msgs, stringsAsFactors = FALSE)
    write.table(hist, hfile, sep = "\t", append = file.exists(hfile),
                col.names = !file.exists(hfile), row.names = FALSE, quote = FALSE)
    message("[provenance] environment change for ", member, ":")
    for (m in msgs) message(m)
    message("[provenance] this may change results. Run .provenance/reconcile.R for the team picture.")
    if (strict && any(grepl("differs from baseline", msgs)))
      stop("[provenance] PROV_STRICT: halting on baseline mismatch.")
  }
  invisible(cur)
}
```

## Python helper (standard library only)

```python
# .provenance/provenance.py  -- offline, standard library only.
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import csv, os, sys, getpass, socket, datetime

def _member():
    cfg = Path.home() / ".config" / "script-provenance" / "whoami"
    if cfg.exists():
        first = cfg.read_text().splitlines()
        if first and first[0].strip():
            return first[0].strip()
    return f"{getpass.getuser()}@{socket.gethostname()}"

def _read_tsv(path):
    if not path.exists():
        return {}
    with path.open() as f:
        return {r["package"]: r["version"] for r in csv.DictReader(f, delimiter="\t")}

def prov_check(packages, strict=False, root=None):
    root = Path(root or os.environ.get("PROV_ROOT") or Path(__file__).resolve().parents[1])
    pdir, member = root / ".provenance", _member()
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in member)
    cur = {}
    for p in packages:
        try:    cur[p] = version(p)
        except PackageNotFoundError: cur[p] = "MISSING"
    mdir = pdir / "members"; mdir.mkdir(parents=True, exist_ok=True)
    mfile = mdir / f"{safe}.tsv"
    prev, base = _read_tsv(mfile), _read_tsv(pdir / "baseline.tsv")
    today, lv = datetime.date.today().isoformat(), ".".join(map(str, sys.version_info[:3]))

    msgs = []
    for p, v in cur.items():
        if p in prev and prev[p] != v: msgs.append(f"  {p} changed since your last run: {prev[p]} -> {v}")
        if p in base and base[p] != v: msgs.append(f"  {p} differs from baseline: you {v}, blessed {base[p]}")

    with mfile.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["package","version","language","lang_version","member","date"])
        for p, v in cur.items(): w.writerow([p, v, "python", lv, member, today])

    if msgs:
        hist = mdir / f"{safe}.history.tsv"; new = not hist.exists()
        with hist.open("a", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            if new: w.writerow(["date","member","event"])
            for m in msgs: w.writerow([today, member, m.strip()])
        print(f"[provenance] environment change for {member}:", file=sys.stderr)
        for m in msgs: print(m, file=sys.stderr)
        print("[provenance] this may change results. Run .provenance/reconcile.R for the team picture.", file=sys.stderr)
        if strict and any("differs from baseline" in m for m in msgs):
            raise SystemExit("[provenance] strict: halting on baseline mismatch.")
```

Compare with `packaging.version.parse` if available for strict version ordering. The string compare above is enough to detect any change, which is the goal.

## Stata helper (partial, best effort)

Stata does not expose reliable versions for user-written ado commands, so this records the Stata version in full and the ado names with a best-effort version, and says so.

```stata
* .provenance/provenance.do  -- offline, partial.
capture program drop prov_check
program define prov_check
    syntax [anything(name=ados)]
    local member : env PROV_MEMBER
    if "`member'" == "" local member "`c(username)'"
    local safe = subinstr("`member'", " ", "_", .)
    capture mkdir "${ROOT}/.provenance/members"
    tempname fh
    file open `fh' using "${ROOT}/.provenance/members/`safe'.tsv", write replace
    file write `fh' "package" _tab "version" _tab "language" _tab "lang_version" _tab "member" _tab "date" _n
    file write `fh' "stata-core" _tab "`c(stata_version)'" _tab "stata" _tab "`c(version)'" _tab "`member'" _tab "`c(current_date)'" _n
    foreach a of local ados {
        capture which `a'
        local ver = cond(_rc, "MISSING", "installed")
        file write `fh' "`a'" _tab "`ver'" _tab "stata" _tab "`c(version)'" _tab "`member'" _tab "`c(current_date)'" _n
    }
    file close `fh'
    di as text "[provenance] recorded environment for `member'. Stata ado versions are partial; vendor ado files for true reproducibility."
end
```

## Reconcile (on demand)

A script the team runs when a warning appears, or before trusting a result. It is the only piece allowed a network call, and only for the latest-release lookup the user asked for.

Algorithm:

1. Read `baseline.tsv` and every `members/*.tsv`.
2. Build a table with one row per package and one column per source: baseline, then each member.
3. Mark every cell that differs from baseline, and flag any package where two members disagree.
4. Latest-release lookup (network, optional): CRAN via `available.packages()` for R packages, PyPI via `https://pypi.org/pypi/<pkg>/json` for Python packages. Stata SSC has no clean version API, so mark Stata rows as not checked. Add a `latest` column and flag who is behind.
5. Write a dated report to `.provenance/reports/YYYY-MM-DD_provenance.md`, and print a short summary: how many packages diverge, which members are behind, and the single largest gap.

Report row shape:

```text
package      baseline   Sara,MacBook   Ahmed,ThinkPad   latest    note
data.table   1.14.8     1.14.8         1.15.0           1.15.0    Ahmed ahead of baseline; Sara on baseline
fixest       0.11.2     0.11.2         0.11.2           0.12.1    whole team behind latest
```

The report states divergence, not result effects. Whether a divergence changed a result is for the user to verify by rerunning under the baseline through the restoration layer.

## Restoration layer

The baseline records what was blessed. The lockfile is what actually reinstalls it.

- **R.** `renv::snapshot()` writes `renv.lock` with the full dependency closure and hashes; `renv::restore()` brings it back. For a lighter, in-script option, record a `groundhog` date and load packages with `groundhog.library`, which installs the versions as of that date.
- **Python.** `uv` with `uv.lock` if present, otherwise `pip freeze > requirements.txt` for a pinned set. A virtual environment is the real isolation.
- **Stata.** Vendor the exact ado files into `<ROOT>/ado/`, set `adopath ++ "${ROOT}/ado"` at the top of `master.do`, and keep the `version` directive in each do-file. This is the most reliable Stata reproducibility path, since ado version tracking is otherwise weak.

The in-script check tells the team the environment moved. The restoration layer is how they move it back.
