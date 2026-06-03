#!/bin/sh

set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

require_dir() {
  if [ ! -d "$1" ]; then
    echo "Missing required directory: $1" >&2
    exit 1
  fi
}

require_readme_text() {
  if ! rg -q "$1" README.md; then
    echo "README is missing expected text: $1" >&2
    exit 1
  fi
}

require_dir ".claude/skills"
require_dir "codex-skills"

require_file ".claude/skills/replication-repo.md"
require_file ".claude/skills/ref-check.md"
require_file "codex-skills/replication-repo/SKILL.md"
require_file "codex-skills/replication-repo/agents/openai.yaml"
require_file "codex-skills/ref-check/SKILL.md"
require_file "codex-skills/ref-check/agents/openai.yaml"
require_file "codex-skills/ref-check/references/workbook-schema.md"
require_file "scripts/install_codex_skills.sh"

require_readme_text "replication-repo"
require_readme_text "ref-check"
require_readme_text "Claude"
require_readme_text "Codex"
require_readme_text "browser session"

for skill in codex-skills/*/SKILL.md; do
  if ! rg -q "^name:" "$skill"; then
    echo "Codex skill missing name frontmatter: $skill" >&2
    exit 1
  fi
  if ! rg -q "^description:" "$skill"; then
    echo "Codex skill missing description frontmatter: $skill" >&2
    exit 1
  fi
done

if find . -path './.git' -prune -o -name '.DS_Store' -print | grep -q .; then
  echo "Warning: repository contains .DS_Store files outside .git/. They are ignored by .gitignore but should be cleaned before publishing." >&2
  find . -path './.git' -prune -o -name '.DS_Store' -print >&2
fi

echo "Skill repository validation passed."
