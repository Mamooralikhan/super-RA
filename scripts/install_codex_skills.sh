#!/bin/sh

set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source_dir="$repo_root/codex-skills"
target_root="${CODEX_HOME:-$HOME/.codex}"
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
  echo "Installed Codex skill: $skill_name -> $target_dir/$skill_name"
done

echo "Codex skills are available in $target_dir"
