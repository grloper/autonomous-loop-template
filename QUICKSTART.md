# Quick reference

For what each component does and why it is built this way, see
[`.github/ARCHITECTURE.md`](.github/ARCHITECTURE.md).

## Commands

```bash
# See what the scanner would file, without filing anything
python .github/scripts/orchestrator.py --dry-run

# Scan a subdirectory
python .github/scripts/orchestrator.py --root ./services/api --dry-run

# File issues (needs GITHUB_TOKEN and GITHUB_REPOSITORY)
python .github/scripts/orchestrator.py --max-issues 3

# Review a specific PR
python .github/scripts/auto_reviewer.py --repo owner/name --pr-number 42

# Diagnose a failed run
python .github/scripts/workflow_doctor.py --repo owner/name --run-id 123456789

# Trigger from the CLI
gh workflow run orchestrator.yml -f dry_run=true
gh workflow run manual-pr-review.yml -f pr_number=42 -f action=approve-only
```

## Configuration

`.github/autonomous-loop.yml`, all keys optional:

| Key | Default | Effect |
|---|---|---|
| `max_issues_per_run` | `5` | Cap on issues filed per run. Excess findings wait for the next run. |
| `min_score` | `3.0` | Findings scoring below this are dropped. |
| `marker_weights` | see script | `KEYWORD: [impact, urgency, risk]`; score is `impact × urgency ÷ risk`. |
| `exclude_dirs` | `.git`, `node_modules`, … | Matched against path components, not substrings. |
| `include_suffixes` | `.py`, `.ts`, `.go`, … | Only these file types are scanned. |
| `escalations` | see script | Regex → multiplier, applied when it matches the marker's line. |

Merge-gate thresholds live in `.github/scripts/auto_reviewer.py`:
`CRITICAL_PATH_GLOBS`, `AUTO_MERGE_GLOBS`, `DANGEROUS_DIFF_PATTERNS`,
`MAX_AUTO_MERGE_FILES`, `MAX_AUTO_MERGE_LINES`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Scheduled runs stopped appearing | GitHub disables `schedule:` after 60 days of repository inactivity, silently. Re-enable on the Actions tab. |
| No issues filed | Run with `--dry-run`. Findings below `min_score` are dropped, and duplicates of open issues are skipped by design. |
| Scanner misses a directory | Check `include_suffixes` covers the file type and `exclude_dirs` does not name a parent directory. |
| A marker is not detected | Markers only count inside comments, so a keyword in a string literal is ignored on purpose. |
| Nothing ever auto-merges | Intentional unless the PR is documentation-only, small, clean, and CI is green. Read the "why this will not auto-merge" list in the review comment. |
| Reviewer says "diff unavailable" | The file is binary or too large for the API to return a patch, so it cannot be inspected and will not auto-merge. |
| Reviewer errored | It fails closed and requests human review. The error appears in the review comment and the step log. |
| Doctor says `logs_unavailable` | Logs expired, or the workflow lacks `actions: read`. |
| Duplicate issues | Should not happen — issues carry a fingerprint marker. If it does, the marker was edited out of the issue body. |

## Safety properties to preserve when editing

These are load-bearing. Changing any of them re-opens a defect that was fixed:

1. **The reviewer checks out `base.sha`, never the PR head.** A head checkout
   lets a pull request modify `auto_reviewer.py` and approve itself.
2. **PR-controlled text reaches scripts through `env:`**, never `${{ }}`
   interpolation inside a script body, which allows injection via a PR title.
3. **The reviewer fails closed.** Every error path sets `auto_merge` to false.
4. **The doctor never writes to `.github/workflows/`.** Round-tripping workflow
   YAML through a parser turns `on:` into `true:` and disables the workflow.
5. **`exclude_dirs` matches path components.** A substring match on `.git` also
   excludes `.github`, which silently hides that whole tree from the scanner.
