# Autonomous Pipeline Agents

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GitHub Actions workflows that scan a repository for actionable work, file
deduplicated issues about what they find, and review pull requests against a
conservative merge gate.

## What it actually does

| Component | Behaviour |
|---|---|
| **Orchestrator** (`orchestrator.py`) | Walks source files, finds `TODO` / `FIXME` / `HACK` / `XXX` / `BUG` comments, scores each by `impact × urgency ÷ risk`, and files an issue for the highest-scoring findings. Re-runs update rather than duplicate. |
| **Auto-reviewer** (`auto_reviewer.py`) | Reads the PR diff, flags dangerous patterns in added and removed lines, and decides `APPROVE` / `COMMENT` / `REQUEST_CHANGES`. Auto-merge requires documentation-only paths, a small diff, a clean patch, and green CI. |
| **Workflow doctor** (`workflow_doctor.py`) | Downloads the logs of a failed run, matches them against known failure signatures, and files one issue per (workflow, failure type) with a log excerpt and remediation steps. |

## What it does not do

Being clear about this up front, because the previous version of this README
was not:

- **It does not write code.** It files issues. Something else — you, or a
  coding agent you have separately configured — has to implement them.
- **It does not run unattended forever.** GitHub disables a `schedule:` trigger
  after 60 days without repository activity, silently. Check the Actions tab if
  runs stop.
- **It does not repair workflows.** The doctor diagnoses and reports. An earlier
  version rewrote workflow YAML and corrupted the `on:` trigger in the process;
  that behaviour is gone deliberately.
- **It does not measure whether its own suggestions were good.** No component
  tracks whether a filed issue was useful or a merged change was correct. If you
  want that signal, you have to build it.

## Install

```bash
git clone https://github.com/grloper/autonomous-pipeline-agents
cp -r autonomous-pipeline-agents/.github/scripts   .github/
cp -r autonomous-pipeline-agents/.github/workflows .github/
cp    autonomous-pipeline-agents/.github/copilot-instructions.md .github/
```

Then, before committing:

1. **Fill in `.github/copilot-instructions.md`.** It ships as a template. An
   agent reading unfilled placeholders produces worse changes than one reading
   nothing.
2. **Edit `CRITICAL_PATH_GLOBS` in `.github/scripts/auto_reviewer.py`** to cover
   your authentication, payment, migration, and infrastructure paths.
3. **Dry-run the scanner** to see what it would file:
   ```bash
   pip install -r .github/scripts/requirements.txt
   python .github/scripts/orchestrator.py --dry-run
   ```

## Configuration

Optional `.github/autonomous-loop.yml`, merged over the defaults:

```yaml
max_issues_per_run: 5      # cap on issues filed per run
min_score: 3.0             # findings below this are dropped
exclude_dirs: [".git", "node_modules", "vendor"]
include_suffixes: [".py", ".ts", ".go"]
marker_weights:
  FIXME: [7, 8, 3]         # [impact, urgency, risk] -> score = i * u / r
  TODO:  [5, 4, 3]
```

Anything you omit keeps its default. An unreadable or malformed file logs a
warning and falls back to defaults rather than failing the run.

## The merge gate

`auto_merge` is only true when **all** of these hold:

- every changed path matches `AUTO_MERGE_GLOBS` (documentation and plain text)
- no changed path matches `CRITICAL_PATH_GLOBS`
- ≤ 5 files and ≤ 150 changed lines
- no `DANGEROUS_DIFF_PATTERNS` match on any added or removed line
- CI is green — pending, absent, and unreadable all count as not green

Any error inside the reviewer produces "a human must review this". There is no
path where a failure results in a merge.

## Security

These workflows hold write access to your repository. The design constraints
that follow from that:

- **The reviewer never runs code from the PR it is reviewing.** It checks out
  `base.sha`, not the PR head. Otherwise a pull request could modify
  `auto_reviewer.py` and approve itself.
- **PR-controlled text reaches scripts through `env:`, never through `${{ }}`
  interpolation inside a script body**, which would allow injection via a
  crafted PR title.
- **`contents: write` is scoped to the one job that merges.** Scanning and
  diagnosis run with read access.
- **Repository content is untrusted input to any agent.** Issue bodies, PR
  descriptions, and README text have been used to redirect coding agents into
  exfiltrating credentials. Pin actions to full commit SHAs if you tighten
  this further; tag rewrites have been used to compromise Actions consumers.

## Limitations worth knowing before you rely on this

- Marker scanning finds comments developers wrote. It does not find bugs nobody
  labelled, and the score is a heuristic over keywords, not an assessment.
- `DANGEROUS_DIFF_PATTERNS` is a regex list. It catches careless changes and
  known-bad idioms; it will not stop a determined author.
- The auto-merge allowlist is documentation-only by design. Widening it moves
  risk onto the pattern list, which is the weaker of the two controls.

## License

MIT.
