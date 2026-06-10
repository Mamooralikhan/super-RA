#!/bin/sh

# Validates the structural and content invariants of this repository:
#   1. required files exist for both platforms
#   2. every SKILL.md has name/description frontmatter
#   3. paired Claude and Codex skill files are byte-identical (platform parity)
#   4. the Operating Contract block in every skill matches the canonical copy
#   5. no em-dashes anywhere in skills, contract, or README
#   6. the skill name "ref-audit" does not reappear (renamed to ref-check)
#   7. README documents every skill and both platforms

set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$repo_root"

fail=0

err() {
  echo "FAIL: $1" >&2
  fail=1
}

require_file() {
  if [ ! -f "$1" ]; then
    err "missing required file: $1"
  fi
}

require_dir() {
  if [ ! -d "$1" ]; then
    err "missing required directory: $1"
  fi
}

require_readme_text() {
  if ! grep -q "$1" README.md; then
    err "README is missing expected text: $1"
  fi
}

skills="replication-repo ref-check"

# 1. Required files
require_dir ".claude/skills"
require_dir "codex-skills"
require_file "context/OPERATING-CONTRACT.md"
require_file "WORKLOG.md"
require_file "scripts/install_claude_skills.sh"
require_file "scripts/install_codex_skills.sh"

for s in $skills; do
  require_file ".claude/skills/$s/SKILL.md"
  require_file "codex-skills/$s/SKILL.md"
  require_file "codex-skills/$s/agents/openai.yaml"
done
require_file ".claude/skills/ref-check/references/workbook-schema.md"
require_file "codex-skills/ref-check/references/workbook-schema.md"

# 2. Frontmatter in every SKILL.md
for f in .claude/skills/*/SKILL.md codex-skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  if ! grep -q "^name:" "$f"; then
    err "skill missing name frontmatter: $f"
  fi
  if ! grep -q "^description:" "$f"; then
    err "skill missing description frontmatter: $f"
  fi
done

# 3. Platform parity: paired skill bodies must be byte-identical
for s in $skills; do
  a=".claude/skills/$s/SKILL.md"
  b="codex-skills/$s/SKILL.md"
  if [ -f "$a" ] && [ -f "$b" ] && ! cmp -s "$a" "$b"; then
    err "platform drift: $a and $b differ. Edit one, copy to the other."
  fi
done
if [ -f ".claude/skills/ref-check/references/workbook-schema.md" ] && \
   [ -f "codex-skills/ref-check/references/workbook-schema.md" ] && \
   ! cmp -s ".claude/skills/ref-check/references/workbook-schema.md" \
            "codex-skills/ref-check/references/workbook-schema.md"; then
  err "platform drift: workbook-schema.md differs between Claude and Codex copies."
fi

# 4. Operating Contract block must match the canonical copy verbatim
extract_contract() {
  awk '/<!-- BEGIN OPERATING CONTRACT -->/{flag=1} flag{print} /<!-- END OPERATING CONTRACT -->/{flag=0}' "$1"
}

canonical=$(extract_contract context/OPERATING-CONTRACT.md)
if [ -z "$canonical" ]; then
  err "context/OPERATING-CONTRACT.md has no marked contract block."
else
  for f in .claude/skills/*/SKILL.md codex-skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    block=$(extract_contract "$f")
    if [ -z "$block" ]; then
      err "skill has no Operating Contract block: $f"
    elif [ "$block" != "$canonical" ]; then
      err "Operating Contract in $f differs from context/OPERATING-CONTRACT.md"
    fi
  done
fi

# 5. No em-dashes in skill content, contract, or README
if grep -Rn -- '—' README.md context .claude/skills codex-skills 2>/dev/null; then
  err "em-dash found in the files listed above. The house style forbids em-dashes."
fi

# 6. Retired skill name must not reappear
if grep -Rqn 'ref-audit' README.md context .claude/skills codex-skills 2>/dev/null; then
  err "retired name 'ref-audit' found. The skill is named ref-check everywhere."
fi

# 7. README coverage
for s in $skills; do
  require_readme_text "$s"
done
require_readme_text "Claude"
require_readme_text "Codex"
require_readme_text "browser"
require_readme_text "dependency map"

# Housekeeping warning only
if find . -path './.git' -prune -o -name '.DS_Store' -print | grep -q .; then
  echo "Warning: .DS_Store files present outside .git/. Clean before publishing:" >&2
  find . -path './.git' -prune -o -name '.DS_Store' -print >&2
fi

if [ "$fail" -ne 0 ]; then
  echo "Skill repository validation FAILED." >&2
  exit 1
fi

echo "Skill repository validation passed."
