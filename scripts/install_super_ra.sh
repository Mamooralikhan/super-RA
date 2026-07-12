#!/bin/sh

# Install super-RA INTO a research project.
#
#   sh scripts/install_super_ra.sh /path/to/ProjectA [--copy]
#
# After this runs, every Claude Code session launched in ProjectA is governed by the super-RA
# brain instead of by the person's own global rules. Their ~/.claude/CLAUDE.md is not loaded
# there; the brain replaces it; and a SessionStart hook tells them so.
#
# What lands in the project:
#
#   ProjectA/CLAUDE.md                     the brain. AT THE ROOT. See the warning below.
#   ProjectA/.claude/settings.json         claudeMdExcludes + permissions.deny + the hook
#   ProjectA/.claude/hooks/super_ra_notice.sh
#   ProjectA/.claude/skills/<skill>        symlinked to this repo, or copied with --copy
#
# THE BRAIN GOES AT THE ROOT, NOT UNDER .claude/. The exclusion glob is "**/.claude/CLAUDE.md",
# which is what reaches ~/.claude/CLAUDE.md and unloads it. A brain placed under .claude/ would
# match its own exclusion rule, delete itself from context, and leave the project governed by
# nothing at all while appearing to be governed by super-RA. That is worse than not installing.
#
# ON COLLISION THIS SCRIPT REFUSES AND CHANGES NOTHING. A research project's existing CLAUDE.md
# is somebody's work. Overwriting it, or "helpfully" backing it up and swapping the project's
# behaviour out from under them, is exactly the class of surprise the Operating Contract exists
# to prevent. Report, and let the human decide.

set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
brain_dir="$repo_root/brain"
skills_dir="$repo_root/.claude/skills"

mode="symlink"
target=""

for arg in "$@"; do
  case "$arg" in
    --copy) mode="copy" ;;
    -*) echo "Unknown option: $arg" >&2; exit 2 ;;
    *)  target="$arg" ;;
  esac
done

if [ -z "$target" ]; then
  echo "Usage: sh scripts/install_super_ra.sh /path/to/project [--copy]" >&2
  echo "" >&2
  echo "  --copy   copy the skills instead of symlinking them, for a self-contained project" >&2
  exit 2
fi

if [ ! -d "$target" ]; then
  echo "FATAL: not a directory: $target" >&2
  echo "Create the project folder first. This script does not create it for you, because a typo" >&2
  echo "in a path should not silently produce an empty project." >&2
  exit 1
fi

target_root=$(CDPATH= cd -- "$target" && pwd)

if [ "$target_root" = "$repo_root" ]; then
  echo "FATAL: that is the super-RA repository itself." >&2
  echo "It already carries the brain at ./CLAUDE.md. Nothing to install." >&2
  exit 1
fi

for f in "$brain_dir/CLAUDE.md" "$brain_dir/settings.json" "$brain_dir/hooks/super_ra_notice.sh"; do
  if [ ! -f "$f" ]; then
    echo "FATAL: the brain is incomplete. Missing: $f" >&2
    exit 1
  fi
done

# ---------------------------------------------------------------------------------------------
# Collision check. This runs BEFORE anything is written, and it is the whole reason this script
# is safe to hand to someone else.
# ---------------------------------------------------------------------------------------------
collisions=""
[ -e "$target_root/CLAUDE.md" ]              && collisions="$collisions  $target_root/CLAUDE.md
"
[ -e "$target_root/.claude/settings.json" ]  && collisions="$collisions  $target_root/.claude/settings.json
"
[ -e "$target_root/.claude/hooks/super_ra_notice.sh" ] && collisions="$collisions  $target_root/.claude/hooks/super_ra_notice.sh
"

if [ -n "$collisions" ]; then
  echo "REFUSING TO INSTALL. These files already exist in the target project:" >&2
  echo "" >&2
  printf '%s' "$collisions" >&2
  echo "" >&2
  echo "Nothing has been changed. Not one byte." >&2
  echo "" >&2
  echo "super-RA would have written:" >&2
  echo "  $target_root/CLAUDE.md                          <- the brain" >&2
  echo "  $target_root/.claude/settings.json              <- exclusions, deny rules, the hook" >&2
  echo "  $target_root/.claude/hooks/super_ra_notice.sh   <- the takeover notice" >&2
  echo "" >&2
  echo "Those files are yours and they may be load-bearing. Read them, decide what you want to" >&2
  echo "keep, move them aside yourself, and run this again. super-RA does not overwrite a" >&2
  echo "project's existing governance, and it does not quietly rename it either." >&2
  exit 1
fi

# ---------------------------------------------------------------------------------------------
# Install.
# ---------------------------------------------------------------------------------------------
mkdir -p "$target_root/.claude/hooks" "$target_root/.claude/skills"

cp "$brain_dir/CLAUDE.md"                 "$target_root/CLAUDE.md"
cp "$brain_dir/settings.json"             "$target_root/.claude/settings.json"
cp "$brain_dir/hooks/super_ra_notice.sh"  "$target_root/.claude/hooks/super_ra_notice.sh"
chmod +x "$target_root/.claude/hooks/super_ra_notice.sh"

echo "Installed the brain:"
echo "  CLAUDE.md                        (root, so it survives its own exclusion glob)"
echo "  .claude/settings.json"
echo "  .claude/hooks/super_ra_notice.sh"
echo ""

for skill_dir in "$skills_dir"/*; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  rm -rf "$target_root/.claude/skills/$skill_name"
  if [ "$mode" = "copy" ]; then
    cp -R "$skill_dir" "$target_root/.claude/skills/$skill_name"
    echo "Installed skill (copy)   : $skill_name"
  else
    ln -sfn "$skill_dir" "$target_root/.claude/skills/$skill_name"
    echo "Installed skill (symlink): $skill_name -> $skill_dir"
  fi
done

echo ""
echo "================================================================================"
echo "  super-RA is installed in: $target_root"
echo ""
echo "  ONE THING REMAINS, AND WITHOUT IT NONE OF THIS IS ACTIVE:"
echo ""
echo "  Start Claude Code in that folder and ACCEPT THE WORKSPACE TRUST DIALOG."
echo "  Project settings and hooks are trust-gated. Until you accept, the brain is"
echo "  inert: the global rules still load, the deny rules do not apply, and no"
echo "  notice is printed. A brain that silently does nothing is worse than none,"
echo "  because it invites you to believe you are governed when you are not."
echo ""
echo "  To confirm it took effect, run /memory in that project. You should see"
echo "  CLAUDE.md listed, and you should NOT see ~/.claude/CLAUDE.md."
echo "================================================================================"
