#!/bin/sh

# Validates the structural and content invariants of this repository:
#   1. required files exist
#   2. every SKILL.md has name/description frontmatter
#   3. the Operating Contract block in every skill matches the canonical copy
#   4. no em-dashes anywhere in skills, contract, brain, or README
#   5. the skill name "ref-audit" does not reappear (renamed to ref-check)
#   6. no Codex remnants (Codex support was removed; this repository is Claude only)
#   7. every shipped pipeline template compiles
#   8. README documents every skill
#   9. the brain block in ./CLAUDE.md matches brain/CLAUDE.md verbatim
#  10. brain/settings.json is valid JSON and still carries the three things that make super-RA
#      supersede rather than merely suggest
#  11. the SessionStart hook parses and is executable
#
# The platform-parity check that used to live here is gone on purpose. It compared the
# Claude and Codex copies of each skill byte for byte. There is no Codex copy any more,
# so there is nothing to compare. Check 6 exists so that the removal stays removed.

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

skills="replication-repo ref-check script-provenance"

# 1. Required files
require_dir ".claude/skills"
require_file "context/OPERATING-CONTRACT.md"
require_file "README.md"
require_file "WORKLOG.md"
require_file "scripts/install_claude_skills.sh"

# The brain. super-RA is not only a skill library: installed into a project, it supersedes the
# user's own global rules. That is a strong claim, so the pieces that make it true are required.
require_file "CLAUDE.md"
require_file "brain/CLAUDE.md"
require_file "brain/README.md"
require_file "brain/settings.json"
require_file "brain/hooks/super_ra_notice.sh"
require_file "scripts/install_super_ra.sh"

for s in $skills; do
  require_file ".claude/skills/$s/SKILL.md"
done

# ref-check ships its method as reference documents and as working pipeline templates.
# The templates are the point. The extraction rules they encode were each learned from a
# real bug that produced a false accusation against a correct bibliography.
require_file ".claude/skills/ref-check/references/extraction-rules.md"
require_file ".claude/skills/ref-check/references/methodology-assistant.md"
require_file ".claude/skills/ref-check/references/methodology-associate.md"
require_file ".claude/skills/ref-check/references/report-schema.md"
for p in 01_extract_citations 02_make_batches 03_collect_assistant \
         04_collect_associate 05_pi_review 06_render bst_render; do
  require_file ".claude/skills/ref-check/references/pipeline/$p.py"
done

require_file ".claude/skills/script-provenance/references/templates.md"
require_file ".claude/skills/script-provenance/references/provenance-system.md"

# The Excel workbook deliverable was retired when ref-check was rewritten.
if [ -f ".claude/skills/ref-check/references/workbook-schema.md" ]; then
  err "workbook-schema.md still present. The Excel workbook was retired; ref-check emits HTML."
fi

# 2. Frontmatter in every SKILL.md
for f in .claude/skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  if ! grep -q "^name:" "$f"; then
    err "skill missing name frontmatter: $f"
  fi
  if ! grep -q "^description:" "$f"; then
    err "skill missing description frontmatter: $f"
  fi
done

# 3. Operating Contract block must match the canonical copy verbatim
extract_contract() {
  awk '/<!-- BEGIN OPERATING CONTRACT -->/{flag=1} flag{print} /<!-- END OPERATING CONTRACT -->/{flag=0}' "$1"
}

canonical=$(extract_contract context/OPERATING-CONTRACT.md)
if [ -z "$canonical" ]; then
  err "context/OPERATING-CONTRACT.md has no marked contract block."
else
  for f in .claude/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    block=$(extract_contract "$f")
    if [ -z "$block" ]; then
      err "skill has no Operating Contract block: $f"
    elif [ "$block" != "$canonical" ]; then
      err "Operating Contract in $f differs from context/OPERATING-CONTRACT.md"
    fi
  done
fi

# 4. No em-dashes in skill content, contract, brain, or README
if grep -Rn -- '—' README.md context .claude/skills CLAUDE.md brain 2>/dev/null; then
  err "em-dash found in the files listed above. The house style forbids em-dashes."
fi

# 5. Retired skill name must not reappear
if grep -Rqn 'ref-audit' README.md context .claude/skills 2>/dev/null; then
  err "retired name 'ref-audit' found. The skill is named ref-check everywhere."
fi

# 6. Codex support was removed. Keep it removed.
#
# This checks for FUNCTIONAL Codex references (paths, installers, invocation syntax), not for the
# word itself. README.md and WORKLOG.md are expected to SAY that Codex was removed and why: a user
# who goes looking for it deserves an answer, and deleting the explanation along with the code
# would just make the absence mysterious.
if [ -d "codex-skills" ]; then
  err "codex-skills/ exists. Codex support was removed; this repository is Claude only."
fi
if [ -f "scripts/install_codex_skills.sh" ]; then
  err "scripts/install_codex_skills.sh exists. Codex support was removed."
fi
# This script names those strings in order to forbid them, so it must exclude itself. Without
# the exclusion the check matches its own source and fails permanently, which looks like a real
# finding and is not.
if grep -RnI --exclude='validate_skills.sh' \
     -e 'codex-skills' -e 'install_codex_skills' -e 'CODEX_HOME' \
     README.md context .claude/skills scripts 2>/dev/null; then
  err "functional Codex reference found above (a path, an installer, or CODEX_HOME)."
fi
# Codex invocation syntax is "$skill-name". No skill should still advertise it.
if grep -RnI '\$ref-check\|\$replication-repo\|\$script-provenance' \
     README.md .claude/skills 2>/dev/null; then
  err "Codex invocation syntax found above. Skills are invoked with /name on Claude."
fi

# 7. Shipped pipeline templates must compile
if command -v python3 >/dev/null 2>&1; then
  for f in .claude/skills/ref-check/references/pipeline/*.py; do
    [ -f "$f" ] || continue
    if ! python3 -m py_compile "$f" 2>/dev/null; then
      err "pipeline template does not compile: $f"
    fi
  done
  find . -path ./.git -prune -o -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
else
  echo "Warning: python3 not found. Skipped the pipeline template compile check." >&2
fi

# 8. README coverage
for s in $skills; do
  require_readme_text "$s"
done
require_readme_text "Claude"
require_readme_text "dependency map"
require_readme_text "install_super_ra.sh"
require_readme_text "brain"

# 9. The brain block must be identical in brain/CLAUDE.md and ./CLAUDE.md.
#    Same discipline as the Operating Contract: one canonical copy, duplicated verbatim, and the
#    duplicate is checked rather than trusted.
extract_brain() {
  awk '/<!-- BEGIN SUPER-RA BRAIN -->/{flag=1} flag{print} /<!-- END SUPER-RA BRAIN -->/{flag=0}' "$1"
}

canonical_brain=$(extract_brain brain/CLAUDE.md)
if [ -z "$canonical_brain" ]; then
  err "brain/CLAUDE.md has no marked brain block."
else
  root_brain=$(extract_brain CLAUDE.md)
  if [ -z "$root_brain" ]; then
    err "./CLAUDE.md has no Super-RA brain block."
  elif [ "$root_brain" != "$canonical_brain" ]; then
    err "the brain block in ./CLAUDE.md differs from brain/CLAUDE.md. Edit brain/ first, then copy."
  fi
fi

# 10. The three things that make super-RA supersede rather than merely suggest. Lose any one of
#     them and the brain still LOOKS installed while doing nothing, which is the worst outcome
#     available: the user believes they are governed when they are not.
#
#     - claudeMdExcludes  : without it, Claude CONCATENATES the user's global CLAUDE.md alongside
#                           the brain instead of replacing it. super-RA becomes one voice among
#                           several. This is the whole mechanism.
#     - permissions.deny  : settings are enforced by the client; CLAUDE.md is only context.
#     - SessionStart hook : a takeover the user is not told about is a trick.
if command -v python3 >/dev/null 2>&1; then
  if ! python3 - <<'PY'
import json, sys
try:
    s = json.load(open("brain/settings.json"))
except Exception as exc:
    print(f"brain/settings.json is not valid JSON: {exc}")
    sys.exit(1)

problems = []
ex = s.get("claudeMdExcludes") or []
if "**/.claude/CLAUDE.md" not in ex:
    problems.append(
        "claudeMdExcludes is missing '**/.claude/CLAUDE.md'. Without it the user's global "
        "CLAUDE.md is CONCATENATED with the brain rather than replaced by it, and super-RA "
        "does not supersede anything."
    )
if not (s.get("permissions") or {}).get("deny"):
    problems.append("permissions.deny is empty. CLAUDE.md is context, not enforcement.")
if not (s.get("hooks") or {}).get("SessionStart"):
    problems.append("no SessionStart hook. The user would never be told super-RA had taken over.")

for p in problems:
    print(p)
sys.exit(1 if problems else 0)
PY
  then
    err "brain/settings.json no longer guarantees supersession (see above)."
  fi
fi

# 11. The hook must parse and be executable, or it fails silently at session start.
if ! sh -n brain/hooks/super_ra_notice.sh 2>/dev/null; then
  err "brain/hooks/super_ra_notice.sh is not valid sh."
fi
if [ ! -x "brain/hooks/super_ra_notice.sh" ]; then
  err "brain/hooks/super_ra_notice.sh is not executable. It would not run at session start."
fi

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
