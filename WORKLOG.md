# Work Log

Running log of structural work on this repository. Newest entry first. Each entry records what changed, why, the decisions taken, and what remains open, so work can be resumed without re-deriving context.

Conventions: dates are absolute (YYYY-MM-DD). Decisions are numbered per entry so later entries can reference them, for example D2026-06-10.3.

---

## 2026-06-10: Operating contract, approval gate, browser briefing, format overhaul

### Problems identified (review of the repo as of commit 7a66edf)

1. No shared operating context. No skill stated the research-associate role, the no-hallucination rule, the ask-first-when-vague rule, or folder scoping. The replication skill even asked for paths outside the invocation folder.
2. The replication skill built its dependency map internally and then pruned raw data in place with no user approval between mapping and deletion. Cross-script dependency chains were not explicitly required in the map.
3. Claude skills were flat `.md` files without YAML frontmatter, so they registered with weak fallback descriptions and triggered unreliably. Codex versions had proper frontmatter, so the platforms were not at parity.
4. Drifting duplicates existed on the maintainer machine: `~/.claude/commands/ref-audit.md` and `~/.claude/commands/replication-repo.md`, with a different name (`ref-audit`) than the repo (`ref-check`).
5. The em-dash ban was violated by the repo's own skill files, and nothing enforced the ban on generated artifacts.
6. `ref-check` had no user briefing before driving the user's browser: no tooling pre-flight, no VPN/login confirmation, no expectation-setting about verification gates and open tabs.
7. The validator only checked file existence and README strings.

### Changes made

- Created `context/OPERATING-CONTRACT.md` with a marked contract block (role, evidence rule, vague-scope rule, folder scope, approval before irreversible actions, no em-dashes). The block is embedded verbatim in all four skill files.
- Converted Claude skills to the proper format: `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter. Deleted the old flat files. Added `references/workbook-schema.md` to the Claude ref-check skill for parity.
- Rewrote `replication-repo` (both platforms, identical files):
  - Phase 1 now requires per-output dependency chains crossing scripts, not just per-script traces.
  - New Phase 2 is a hard approval gate: the map is written to `dependency_map.md`, shown as trees with the proposed deletion list and all ambiguities, and nothing is modified until the user approves. Approval is recorded with a date.
  - New Phase 3 copies the project into `replication_package/` inside the invocation folder. All later phases operate on the copy. The original project is never modified.
  - Renumbered phases 1 through 9. Removed all em-dashes. Removed the invitation to accept project paths outside the invocation folder.
- Rewrote `ref-check` (both platforms, identical files):
  - New Step 0: user briefing (what will happen in their browser, expected tab volume, their mid-run duties) plus browser tooling pre-flight (Claude in Chrome extension on Claude, browser tool on Codex) plus access confirmation (VPN or proxy, publisher logins) plus explicit go-ahead.
  - Added explicit rule that the agent never enters credentials or clicks through verification gates itself.
  - Stated that the skill never edits the `.bib` or the paper; the workbook is the deliverable.
- Added `scripts/install_claude_skills.sh`: symlinks `.claude/skills/*` into `~/.claude/skills/` and warns about the stale `~/.claude/commands/` copies.
- Rewrote `scripts/validate_skills.sh` to enforce: required files, frontmatter, byte-identical platform pairs, contract block identical to canonical, no em-dashes, retired name `ref-audit` absent, README coverage.
- Rewrote `README.md` as a guided document: contract summary, quick start per platform, a walkthrough of each skill (what it does, what you need, how a run unfolds, what you get), and an In Development section.
- Updated `codex-skills/*/agents/openai.yaml` default prompts to reflect the approval gate and the browser briefing.

### Decisions

1. **Copy model over in-place pruning.** The replication package is built in `replication_package/` inside the project folder. Rationale: the original files remain the restoration reference, and the prior in-place model contradicted its own "restore from the original" instruction. Cost: doubled disk use for large raw data. Revisit if a user hits disk limits; the alternative is mandatory per-file backups before in-place pruning.
2. **Skill name is `ref-check` everywhere.** `ref-audit` is retired; the validator fails if it reappears in the repo.
3. **Parity by byte-identical files.** Claude and Codex `SKILL.md` for the same skill are kept identical, with platform notes inline. Enforced with `cmp` in the validator. Edit one, copy to the other.
4. **Contract duplication over inclusion.** Skills cannot reliably follow external includes, so the contract is pasted into each skill and the validator diffs every copy against `context/OPERATING-CONTRACT.md`.
5. **Folder scope wording permits browsing only where a step requires it**, so ref-check's web verification remains compatible with the scoping rule.

### Open items

- [x] 2026-06-10: Maintainer confirmed the In Development list (`data-audit`, `pap-check`, `lit-table`) as the working roadmap.
- [x] 2026-06-10: Removed the stale `~/.claude/commands/ref-audit.md` and `~/.claude/commands/replication-repo.md` and installed the repo skills via `scripts/install_claude_skills.sh`. The repo is now the single source of truth on the maintainer machine.
- [ ] Consider a CI workflow (GitHub Actions) that runs `scripts/validate_skills.sh` on every push. Note: the validator uses plain `grep`, so a default ubuntu runner suffices.
- [ ] When the first new skill from the roadmap is drafted, decide whether the workbook-schema pattern (a `references/` folder per skill) becomes the standard for all skills.

---

## Earlier history

See git log before 2026-06-10: initial skill drafts, Codex ports, install and validation scripts, Required Files checks (commits 1ed470a through 7a66edf).
