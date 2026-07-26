# Quick reference

Design notes: [`.github/ARCHITECTURE.md`](.github/ARCHITECTURE.md).

## Commands

```bash
# See the gate decide, offline — no token, no network
python .github/scripts/demo.py
python .github/scripts/demo.py --verbose      # full review bodies

# Run the gate against a real PR
python .github/scripts/gate.py --repo owner/name --pr-number 42

# Scan for markers without filing anything
python .github/scripts/scan.py --dry-run
python .github/scripts/scan.py --root ./services/api --dry-run

# Diagnose a failed run
python .github/scripts/doctor.py --repo owner/name --run-id 123456789

# Checks
python -m unittest discover -s tests -v
bash scripts/verify-setup.sh
```

## Tuning the policy

Edit `.github/agent-policy.yml`, then `python .github/scripts/demo.py` to see
what moved. Omitted keys keep their defaults.

| Key | Effect |
|---|---|
| `provenance.actors` / `branch_prefixes` / `title_markers` | How an agent PR is recognised. Unknown authorship defaults to agent. |
| `protected_paths` | Always a human, whoever wrote it. **The most valuable thing to customise.** |
| `profiles.agent` / `profiles.human` | `auto_merge_paths`, `max_files`, `max_lines`, `require_ci`. |
| `diff_rules` | `severity: block` → REQUEST_CHANGES; `warn` → blocks auto-merge only. |

Scanner settings live in `.github/autonomous-loop.yml`: `max_issues_per_run`,
`min_score`, `marker_weights`, `exclude_dirs`, `include_suffixes`, `escalations`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Nothing auto-merges | Intended unless the PR is docs-only, small, clean, agent-authored, and CI is green. The review comment lists every blocker. |
| A human's PR never auto-merges | By design — `profiles.human.auto_merge_paths` is empty. People merge their own work. |
| "diff unavailable" | Binary or too large for the API to return a patch, so it cannot be inspected. |
| "policy could not be loaded cleanly" | `agent-policy.yml` is malformed. The gate fell back to strict defaults and blocked. |
| Injection false positive | Open an issue with the text. Rules are tuned for precision; a noisy rule is a bug. |
| Scheduled scans stopped | GitHub disables `schedule:` after 60 days of repository inactivity, silently. Re-enable on the Actions tab. |
| Scanner misses a file | Check `include_suffixes` covers the type and `exclude_dirs` names no parent directory. |
| A marker isn't detected | Markers only count inside comments — a keyword in a string literal is ignored on purpose. |
| Doctor says `logs_unavailable` | Logs expired, or the workflow lacks `actions: read`. |

## Invariants — do not break these

Each corresponds to a defect that shipped once. `verify-setup.sh` enforces them.

1. **The gate checks out `base.sha`, never the PR head.** A head checkout lets a
   PR modify `gate.py` and approve itself.
2. **Author-controlled text reaches scripts via `env:`**, never `${{ }}`
   interpolation inside a script body.
3. **The gate fails closed.** Every error path sets `auto_merge` false.
4. **`doctor.py` never imports `yaml`.** Round-tripping a workflow turns `on:`
   into `true:` and permanently disables it.
5. **`scan.py` excludes by path component.** A substring match on `.git` also
   excludes `.github`.
6. **`contents: write` stays on the merge job only.**
