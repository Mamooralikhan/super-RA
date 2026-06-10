#!/bin/sh

set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source_dir="$repo_root/.claude/skills"
target_root="${CLAUDE_HOME:-$HOME/.claude}"
target_dir="$target_root/skills"

if [ ! -d "$source_dir" ]; then
  echo "Missing source skill directory: $source_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"

for skill_dir in "$source_dir"/*; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  ln -sfn "$skill_dir" "$target_dir/$skill_name"
  echo "Installed Claude skill: $skill_name -> $target_dir/$skill_name"
done

# Warn about stale standalone copies that shadow or duplicate these skills.
# Old versions of this repository were copied into ~/.claude/commands/ by hand.
for stale in "$target_root/commands/ref-audit.md" \
             "$target_root/commands/ref-check.md" \
             "$target_root/commands/replication-repo.md"; do
  if [ -f "$stale" ]; then
    echo "WARNING: stale standalone copy found: $stale" >&2
    echo "         It can drift from the repository version. Remove it with:" >&2
    echo "         rm \"$stale\"" >&2
  fi
done

echo "Claude skills are available in $target_dir"
