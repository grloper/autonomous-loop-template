#!/usr/bin/env bash
#
# Install the autonomous-pipeline-agents workflows into the current repository.
#
# Usage:
#   ./install-autonomous-loop.sh            # install, refusing to overwrite
#   ./install-autonomous-loop.sh --force    # overwrite existing files
#
# Piping this into a shell from the network executes whatever the server sends.
# Prefer cloning the repository and running the script from disk, where you can
# read it first.

set -euo pipefail

REPO_URL="https://github.com/grloper/autonomous-pipeline-agents"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "git is not installed."
[[ -d .git ]] || die "not a git repository. Run this from your project root."

TARGET_ROOT=$(pwd)
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

printf 'Fetching %s\n' "$REPO_URL"
git clone --depth 1 --quiet "$REPO_URL" "$TEMP_DIR/src" \
  || die "could not clone $REPO_URL"

FILES=(
  ".github/workflows/gate.yml"
  ".github/workflows/scan.yml"
  ".github/workflows/doctor.yml"
  ".github/workflows/manual-pr-review.yml"
  ".github/scripts/gate.py"
  ".github/scripts/policy.py"
  ".github/scripts/injection.py"
  ".github/scripts/scan.py"
  ".github/scripts/doctor.py"
  ".github/scripts/demo.py"
  ".github/scripts/requirements.txt"
  ".github/agent-policy.yml"
  ".github/copilot-instructions.md"
)

# Check before writing anything, so a refusal leaves the repo untouched.
CONFLICTS=()
for rel in "${FILES[@]}"; do
  [[ -e "$TARGET_ROOT/$rel" ]] && CONFLICTS+=("$rel")
done

if (( ${#CONFLICTS[@]} > 0 && FORCE == 0 )); then
  printf 'These files already exist and would be overwritten:\n' >&2
  printf '  %s\n' "${CONFLICTS[@]}" >&2
  die "nothing was written. Re-run with --force to overwrite, or move them aside."
fi

for rel in "${FILES[@]}"; do
  [[ -f "$TEMP_DIR/src/$rel" ]] || die "missing from the source repository: $rel"
  mkdir -p "$TARGET_ROOT/$(dirname "$rel")"
  cp "$TEMP_DIR/src/$rel" "$TARGET_ROOT/$rel"
  printf '  wrote %s\n' "$rel"
done

cat <<'NEXT'

Installed. Before you commit:

  1. Fill in .github/copilot-instructions.md — it ships as a template, and an
     agent reading unfilled placeholders produces worse changes than one
     reading nothing at all.

  2. Edit protected_paths in .github/agent-policy.yml so it names your
     authentication, payment, migration, and infrastructure directories. Those
     paths will then always require a human reviewer.

  3. Watch the gate decide, offline:

       pip install -r .github/scripts/requirements.txt
       python .github/scripts/demo.py

  4. See what the marker scan would file, without filing anything:

       python .github/scripts/scan.py --dry-run

The gate runs on every pull request. The marker scan runs Mondays at 08:00
UTC; GitHub disables scheduled workflows after 60 days without repository
activity and does not tell you, so check the Actions tab if runs stop.
NEXT
