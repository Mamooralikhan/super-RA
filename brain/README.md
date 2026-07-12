# The super-RA brain

This folder is the brain. `scripts/install_super_ra.sh` copies it into a research project, and from then on every Claude session launched in that project is governed by super-RA instead of by the person's own global rules.

`settings.json` carries no comments because JSON has none and Claude Code may warn on unrecognized keys. The reasoning lives here instead.

## What each piece does

| File | Role |
|---|---|
| `CLAUDE.md` | The constitution. Loaded into every session in a governed project. This is the brain itself. |
| `settings.json` | The enforcement layer. Installed to `<project>/.claude/settings.json`. |
| `hooks/super_ra_notice.sh` | The takeover notice. Installed to `<project>/.claude/hooks/`. |

## Why there are two layers, and why they are not interchangeable

The Claude Code documentation draws the line plainly: "Settings rules are enforced by the client regardless of what Claude decides to do. CLAUDE.md instructions shape Claude's behavior but are not a hard enforcement layer."

So the split is deliberate. Judgement, epistemics, and the approval discipline live in `CLAUDE.md`, because they are things an agent must *reason with*. Anything that must simply never happen lives in `settings.json`, because a rule an agent can reason its way past is not a rule.

## `claudeMdExcludes`: the mechanism that makes "supersede" true

By default Claude Code **concatenates** every `CLAUDE.md` it finds, walking from the filesystem root down to the working directory. It does not override. A project brain, on its own, would simply be appended *underneath* whatever personal rules the user already has, and super-RA would be one voice among several rather than the governing one.

`claudeMdExcludes` is what changes that. It skips instruction files by absolute-path glob, it can be set at the project layer, and it is honored against user-level files. The only file it cannot exclude is a managed-policy `CLAUDE.md` deployed by an organization, which is correct: a company's compliance rules should outrank a research tool.

This was verified empirically, not inferred from the documentation. Two identical throwaway projects were built, differing only in whether `claudeMdExcludes` was set, and a headless session in each was asked to report what it had loaded. The control session named `~/.claude/CLAUDE.md` and could quote a word found only in it. The treatment session could not see it at all, and still carried the project brain. The exclusion works, and the control proves the test was sensitive enough to have caught a failure.

### Why the brain sits at the project root

The brain is installed to `<project>/CLAUDE.md`, **not** to `<project>/.claude/CLAUDE.md`.

That is not a stylistic choice. The exclusion glob is `**/.claude/CLAUDE.md`, which is what reaches `~/.claude/CLAUDE.md` and unloads it. A brain placed under `.claude/` would match its own exclusion rule and delete itself from context, leaving a project governed by nothing at all. **Do not move the brain into `.claude/`.**

### The cost of excluding `.claude/rules/**`

The second glob excludes user-level rules at `~/.claude/rules/`, and it also excludes a governed project's own `.claude/rules/`. That is accepted rather than worked around. A super-RA project keeps its rules in the brain, in one place, where they can be read in full and audited against the canonical copy. Splitting governance across two mechanisms is how governance quietly drifts.

## `permissions.deny`

Four rules, and each one is a line that should never be crossed by an agent:

- `Bash(git commit:*)`, `Bash(git push:*)`, `Bash(git init:*)`. Git history is the maintainer's to write. An agent that commits is an agent that has made a decision about what the record says.
- `Bash(rm -rf:*)`. The single command that turns a recoverable mistake into a loss.

## The notice

A takeover the user is not told about is a trick. The `SessionStart` hook prints, in the transcript, that super-RA is active and that the user's own global instruction file is not loaded.

It prints **plain text, not JSON**, and that is deliberate. For `SessionStart`, plain stdout is both shown to the user and added to the agent's context. One mechanism does both jobs: the user is informed, and the agent is put on the record as having been informed. Emitting JSON instead would be parsed as a hook directive and the user would see nothing.

## Trust

Project hooks and settings do not take effect until the workspace-trust dialog is accepted once in that folder. Until then the brain is inert. The installer says so, because a brain that silently does nothing is worse than no brain: it invites the user to believe they are protected when they are not.
