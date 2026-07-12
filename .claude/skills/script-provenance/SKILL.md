---
name: script-provenance
description: Standardize research code scripts so a mixed team can run them without editing paths, and track package versions across the team so silent reproducibility breaks are caught early. Adds a standard header (author, purpose, date, inputs, outputs) to every script, converts file paths to file-anchored form so the script's own location is the origin and no absolute path is hardcoded, and installs a package version provenance system: an offline in-script check that warns only when a version changes, a per-member ledger that records each teammate's environment, and an on-demand reconcile report that shows who is on which version and who is behind. Works for R, Python, and Stata. Use when the user wants clean script headers, portable dynamic paths, package version pinning or drift detection, or cross-team reproducibility of code results.
---

# Script Provenance

Use this skill when a user wants research code scripts (R, Python, Stata) made portable across a team and instrumented so that package version drift, the usual silent cause of results changing after an update, is recorded and surfaced.

The skill does three things to each script and one thing for the project:

1. **Header.** A standard block at the top: author, purpose, created and updated dates, inputs, outputs.
2. **Paths.** File-anchored paths. The script's own location is the origin. Climbing up is done with `..` segments. No absolute path is ever hardcoded, so the same file runs unchanged on any machine and inside any Box or Dropbox mount.
3. **Version check.** A short offline block that records the package versions this run used and warns the user only when a version has changed since their last run or differs from the project baseline.
4. **Provenance system (project level).** A baseline of blessed versions, a per-member ledger that records each teammate's environment, and a reconcile command that shows the whole team who is on which version and who is behind the latest release.

Follow the phases in order. This skill edits user code, so the approval gate in Phase 2 is a hard stop.

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

## What This Skill Honestly Can and Cannot Do

State these limits plainly to the user. Do not overclaim.

- The version check proves a package version **changed**. It does not prove the **results** changed. Always phrase a warning as "this may change results, verify," never as "results changed."
- Full file-anchored self-location works cleanly in Python and, with the `this.path` package, in R. **Stata cannot self-locate a running do-file.** For Stata the skill anchors to the project root through a marker file and a single editable root line, and it says so rather than pretending parity.
- Stata records package versions only partially. Stata does not expose reliable version numbers for user-written ado commands. The skill records the Stata version and best-effort ado information, and points the user to vendoring ado files for true reproducibility.
- The in-script check is a tripwire. The cure for a confirmed drift is the restoration layer (Phase 4): a native lockfile that can reinstall the exact old versions.

## The One Artifact Outside the Project Folder

Member identity is the only thing this system stores outside the working folder, and only optionally. The reason: a team that shares the project through one Box or Dropbox folder shares the same files, so a per-member identity cannot live inside the project. It is read from `~/.config/script-provenance/whoami`, a one-line file each member sets once on their own machine. If it is absent, identity falls back to the operating system username and host.

Per the Operating Contract, the agent writes only inside the working folder during a run. Creating the home-directory identity file is the member's own action. Offer to create it for the invoking user only with their explicit approval, and never write any other teammate's identity file.

## Modes

Confirm which mode the user wants before starting:

1. **Standardize (retrofit).** Apply the header, file-anchored paths, and version check to scripts that already exist, and install the provenance system. This is the common case. It edits user code, so Phase 2 approval is required.
2. **Initialize only.** Install the provenance system and drop language templates, without rewriting existing scripts.
3. **Scaffold.** Generate a new script with the standard header, path anchor, and version block already in place.
4. **Reconcile.** Run the on-demand team report. Read-only over the ledger, plus one optional network call for latest releases.

## Before You Start

Ask the user:

1. Which mode (above).
2. Which languages are in the project (R, Python, Stata, or a mix).
3. The author name to stamp on scripts being created or where author is missing. Never invent an author. Pull from git config only with the user's confirmation that it is correct.
4. For new scripts, the purpose, in one line. For retrofits, infer purpose from the code and present it for the user to confirm. Do not assert an inferred purpose as fact.
5. The project root inside the working folder, and the folder depth of the scripts, so the number of `..` climb segments is correct.

Read the two reference files before generating anything:

- [references/templates.md](references/templates.md): the header, path, and version-check blocks for R, Python, and Stata.
- [references/provenance-system.md](references/provenance-system.md): the directory layout, identity resolution, ledger schema, the runtime helper, the reconcile report, and the restoration layer.

## Phase 1: Inventory and Draft the Plan

1. List every script in the working folder by language.
2. For each script, record what it currently does for paths: hardcoded absolute paths (for example `setwd`, `cd "C:/Users/..."`, `/Users/.../Dropbox/...`, `~/Library/CloudStorage/Box-Box/...`), working-directory assumptions, and any existing header.
3. For each script, list the packages or ado commands it loads.
4. Decide the correct climb depth from each script to the project root.
5. Draft, but do not yet apply, the exact changes per script: the header to add, the path block to insert, the absolute paths to replace and what each becomes, and the version-check call with the package list.

Do not guess paths. If a path is built dynamically or a script's root is ambiguous, list it as an open question for the user rather than rewriting it.

## Phase 2: Approval Gate

This is a hard stop. No user script is edited before approval.

1. Write the plan to `provenance_plan.md` in the working folder root. For each script show: the header to be added, the before and after of every path line, the version-check call, and any open questions.
2. List the project-level files the system will create (the `.provenance/` folder and its contents, see the reference) and confirm none overwrite existing files. If a name collides, flag it and stop.
3. Present the plan and say:

> "This plan rewrites paths inside your code and adds headers and a version check. Please review the before-and-after path changes especially, since a wrong path rewrite can break a pipeline. Reply with approval or corrections. I will not edit any script until you approve."

4. Halt and wait. Apply corrections and re-present until the user approves. Record the approval with the date in `provenance_plan.md`.

## Phase 3: Apply the Standard

Only after Phase 2 approval, and editing one script at a time:

1. Insert the header block. Author from the user, purpose confirmed in Phase 2, created date as the file's existing date if known else today, updated date as today.
2. Insert the path anchor block for the language. Replace every hardcoded absolute path with a path built downward from `ROOT`. Leave the logic of the script otherwise untouched.
3. Add the version-check call after the packages are loaded, listing exactly the packages or ado commands that script uses.
4. Preserve the script's behavior. The only changes are the header, the path mechanism, and the version check. Do not reorder analysis, rename variables, or alter estimation code.

After each file, re-read it to confirm the edit is what the plan specified.

## Phase 4: Install the Provenance System

Create the `.provenance/` folder in the project root with the helper scripts, the empty `.projroot` marker (needed by Stata), the `members/` folder, and the reconcile script, all as specified in [references/provenance-system.md](references/provenance-system.md).

Then establish the baseline and the restoration layer:

1. **Baseline.** Generate `baseline.tsv` from the current environment: the blessed package versions that produced the committed results, stamped with the date and the member who blessed them. Tell the user that changing the baseline later is a deliberate act tied to re-validating results, not a quick way to silence a warning.
2. **Restoration layer.** Generate the native lockfile so the exact versions can be reinstalled later:
   - R: `renv::snapshot()` for a full closure with hashes, or a recorded `groundhog` date for a lightweight in-script alternative.
   - Python: `uv` lockfile if `uv` is present, otherwise a pinned `requirements.txt` from `pip freeze`.
   - Stata: vendor the ado files into `ado/` in the project and set the ado path to it, plus the `version` directive already in each do-file.
3. **Identity.** Explain the one-time `~/.config/script-provenance/whoami` step to the user. Create it for the invoking user only with explicit approval.

## Phase 5: Verify

1. Run one standardized script of each language from a directory other than its own folder, to prove the file-anchored path resolves regardless of working directory. For Stata, run from the project root and confirm the marker assertion passes.
2. Confirm the version check writes the member's ledger file and stays silent when nothing changed.
3. Temporarily simulate a drift (for example point the check at a version string that differs) and confirm it prints exactly one concise warning and continues, then undo the simulation.
4. Run the reconcile script and confirm it produces a dated report under `.provenance/reports/` showing the baseline column, each member column, and the latest-release column.

Report any step that did not pass. Do not claim the system works end to end if a step failed.

## Phase 6: Report

Summarize:

- which scripts were standardized, by language
- the before-and-after of a representative path change
- that script logic was not otherwise altered
- what the provenance system installed: baseline, ledger, reconcile, restoration lockfile
- how a teammate joins: clone or sync, set `whoami` once, run scripts normally, run reconcile when a warning appears
- the honest limits that apply to this project, especially any Stata caveats

## Common Pitfalls

| Pitfall | Prevention |
|:---|:---|
| Rewriting a path wrong and breaking a pipeline silently | Phase 2 shows every before-and-after path line; Phase 5 runs a script to prove resolution |
| Hardcoding the Box or Dropbox prefix, which differs per machine | Anchor to the script file, climb with `..`; the mount prefix is never referenced |
| Wrong number of `..` climb segments after a script moves folders | Confirm climb depth per script in Phase 1; keep the climb only in the path anchor block |
| Treating string inequality as version order | Compare with a version-aware function, not raw string compare |
| Every run phoning CRAN or PyPI and slowing the team down | The in-script check is fully offline; the latest-release lookup lives only in the on-demand reconcile |
| Member identity inside a shared Box folder, so everyone looks identical | Identity is read from the home directory, per machine, not from the project |
| Ledger write conflicts on Box or Dropbox | One file per member, each member writes only their own; reconcile merges |
| Silencing a warning by editing the baseline without rechecking results | The baseline is the blessed provenance record; changing it is a re-validation event |
| Claiming Stata self-locates the do-file | It does not; anchor through the marker file and say so |
| Direct-package check missing a dependency change | The restoration lockfile captures the full transitive closure |

## Invocation

- Claude: invoke with `/script-provenance` or by asking to standardize scripts or track package versions while this skill is installed.
