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
  ".github/workflows/orchestrator.yml"
  ".github/workflows/copilot-automation.yml"
  ".github/workflows/workflow-doctor.yml"
  ".github/workflows/manual-pr-review.yml"
  ".github/scripts/orchestrator.py"
  ".github/scripts/auto_reviewer.py"
  ".github/scripts/workflow_doctor.py"
  ".github/scripts/requirements.txt"
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

  2. Edit CRITICAL_PATH_GLOBS in .github/scripts/auto_reviewer.py so it covers
     your authentication, payment, migration, and infrastructure paths. Those
     paths will then always require a human reviewer.

  3. See what the scanner would file, without filing anything:

       pip install -r .github/scripts/requirements.txt
       python .github/scripts/orchestrator.py --dry-run

  4. Review the workflow permissions. The reviewer runs against the trusted
     base commit and only the merge job holds contents: write.

The orchestrator runs Mondays at 08:00 UTC. GitHub disables scheduled
workflows after 60 days without repository activity and does not tell you, so
check the Actions tab if runs stop appearing.
NEXT
