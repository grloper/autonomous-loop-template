#!/usr/bin/env bash
#
# Check that the automation is installed correctly and safely configured.
#
# Beyond checking files exist, this asserts the safety properties that were
# defects in earlier versions of this template. Exits non-zero if any fail.

set -uo pipefail

PASS=0; WARN=0; FAIL=0
ok()   { printf '  ok    %s\n' "$1"; PASS=$((PASS+1)); }
warn() { printf '  warn  %s\n' "$1"; WARN=$((WARN+1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL+1)); }

printf '\nRequired files\n'
for f in \
  ".github/workflows/scan.yml" \
  ".github/workflows/gate.yml" \
  ".github/workflows/doctor.yml" \
  ".github/workflows/ci.yml" \
  ".github/scripts/scan.py" \
  ".github/scripts/gate.py" \
  ".github/scripts/doctor.py" \
  ".github/scripts/policy.py" \
  ".github/scripts/injection.py" \
  ".github/scripts/requirements.txt"
do
  [[ -f "$f" ]] && ok "$f" || bad "$f is missing"
done

printf '\nProject context\n'
if [[ -f ".github/copilot-instructions.md" ]]; then
  if grep -qiE '\(two or three sentences|\(list only rules|\(work an agent should' .github/copilot-instructions.md; then
    warn ".github/copilot-instructions.md still has unfilled template sections"
  else
    ok ".github/copilot-instructions.md is filled in"
  fi
else
  warn ".github/copilot-instructions.md not found"
fi

printf '\nSafety properties\n'

# 1. The reviewer must not run code supplied by the PR it is reviewing.
if grep -q 'pull_request\.head\.\(ref\|sha\)' .github/workflows/gate.yml 2>/dev/null; then
  bad "the gate checks out the PR head — a PR could modify the reviewer and self-approve"
elif grep -q 'base\.sha' .github/workflows/gate.yml 2>/dev/null; then
  ok "the gate checks out the trusted base commit"
else
  warn "could not determine which ref the gate checks out"
fi

# 2. The doctor must never rewrite workflow YAML ('on:' becomes 'true:').
if grep -qE '^\s*(import|from)[[:space:]]+yaml' .github/scripts/doctor.py 2>/dev/null; then
  bad "doctor.py imports yaml — a round trip rewrites 'on:' as 'true:'"
else
  ok "doctor.py does not parse or rewrite workflow YAML"
fi

# 3. The reviewer must fail closed.
if grep -q 'auto_merge=False' .github/scripts/gate.py 2>/dev/null &&
   grep -q 'except Exception' .github/scripts/gate.py 2>/dev/null; then
  ok "gate.py has a fail-closed error path"
else
  warn "could not confirm gate.py fails closed on error"
fi

# 4. Workflow-level contents: write is broader than any of these jobs needs.
for wf in .github/workflows/scan.yml .github/workflows/doctor.yml; do
  [[ -f "$wf" ]] || continue
  if awk '/^permissions:/{p=1;next} /^[^[:space:]#]/{p=0} p&&/contents:[[:space:]]*write/{f=1} END{exit !f}' "$wf"; then
    bad "$(basename "$wf") grants workflow-level contents: write — scope it to the job that needs it"
  else
    ok "$(basename "$wf") does not grant workflow-level contents: write"
  fi
done

# 5. Untrusted text must reach scripts via env:, not ${{ }} interpolation.
if grep -qE '\$\{\{[[:space:]]*github\.event\.(pull_request|issue)\.(title|body)' .github/workflows/*.yml 2>/dev/null; then
  bad "a workflow interpolates a PR/issue title or body into a script — pass it via env:"
else
  ok "no PR/issue text is interpolated directly into script bodies"
fi

# 6. The scanner must exclude by path component, not substring.
if grep -q "'.git' in str(" .github/scripts/scan.py 2>/dev/null; then
  bad "scan.py excludes by substring — '.git' also matches '.github', hiding that tree"
else
  ok "scan.py excludes by path component"
fi

printf '\nSyntax\n'
for f in .github/scripts/*.py; do
  python3 -m py_compile "$f" 2>/dev/null && ok "$(basename "$f") parses" \
    || bad "$(basename "$f") has a syntax error"
done
if python3 -c 'import yaml' 2>/dev/null; then
  for f in .github/workflows/*.yml; do
    python3 -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1]))' "$f" 2>/dev/null \
      && ok "$(basename "$f") parses" || bad "$(basename "$f") is not valid YAML"
    grep -q '^on:' "$f" || bad "$(basename "$f") has no top-level 'on:' trigger"
  done
else
  warn "pyyaml not installed locally — skipped workflow YAML validation"
fi

printf '\nPolicy and demo\n'
if python3 -c 'import sys; sys.path.insert(0,".github/scripts"); import policy; p=policy.load_policy("."); sys.exit(1 if p.warnings else 0)' 2>/dev/null; then
  ok "agent-policy.yml loads cleanly"
else
  bad "agent-policy.yml could not be loaded — the gate falls back to strict defaults"
fi
if python3 .github/scripts/demo.py --no-color >/dev/null 2>&1; then
  ok "all demo scenarios behave as documented"
else
  bad "a demo scenario did not behave as documented — the README may be wrong"
fi

printf '\nDry run\n'
if python3 .github/scripts/scan.py --dry-run >/dev/null 2>&1; then
  ok "scan --dry-run completes"
else
  warn "scan --dry-run failed — run it directly to see the error"
fi

printf '\n%d ok, %d warnings, %d failures\n\n' "$PASS" "$WARN" "$FAIL"
if (( FAIL > 0 )); then
  printf 'Fix the failures above before enabling these workflows.\n\n'
  exit 1
fi
exit 0
