#!/bin/sh

# super-RA SessionStart hook.
#
# Fires once, when a Claude Code session starts in a super-RA project.
#
# It does two jobs with one mechanism. For SessionStart, plain stdout is BOTH shown to the user
# in the transcript AND added to the agent's context. So this single notice tells the user that
# super-RA has taken over, and tells the agent that it has, in the same breath. The agent cannot
# later claim it did not know.
#
# Keep it plain text. Emitting JSON here would be parsed as a hook directive and the user would
# see nothing.
#
# Keep it ASCII. The house style forbids em-dashes and the validator fails the build on one.

set -eu

cat <<'NOTICE'
================================================================================
  SUPER-RA IS ACTIVE IN THIS PROJECT.

  Your personal instruction file (~/.claude/CLAUDE.md) is NOT loaded here.
  It has been excluded by this project's .claude/settings.json.

  Only the super-RA brain governs this session. It is at ./CLAUDE.md and you
  can read it at any time.

  What that means in practice:
    - Every claim shows its source, and the source is a link you can click.
      A file and line for your project; the paper itself for the literature.
    - No source, no claim. If it cannot be checked, you will be told so
      plainly, and asked where the truth is, rather than given a guess.
    - Reading and looking things up are free. Every write, edit, command,
      or deletion is asked for first.
    - Data and coding work start with an agreed pipeline, not with code.
    - Deliverables are signed, and the use of Claude Code is disclosed.

  super-RA: https://github.com/Mamooralikhan/super-RA
================================================================================
NOTICE
