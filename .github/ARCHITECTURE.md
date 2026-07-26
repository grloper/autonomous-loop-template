# Architecture

Three independent components. They share a repository and a set of labels;
none of them calls another. That is deliberate — a chain where each stage
assumes the previous one succeeded fails silently at the first broken link.

```
schedule / manual ──▶ Orchestrator ──▶ issues labelled `autonomous-loop`
                          (read-only, issues: write)

pull_request ──▶ Auto-reviewer ──▶ review + verdict
                  (base.sha checkout, contents: read)
                          │
                          └─ verdict APPROVE and auto_merge ──▶ merge job
                                                                (contents: write)

workflow_run: failure ──▶ Workflow doctor ──▶ one issue per (workflow, failure type)
                           (actions: read, issues: write)
```

## Orchestrator

Walks files matching `include_suffixes`, skipping any path whose components
appear in `exclude_dirs`. For each line that contains a comment introducer, it
looks for a marker keyword after the comment starts — so `TODO` inside a string
literal or a configuration table is not a finding.

Each marker becomes a `Finding` scored `impact × urgency ÷ risk`, with a
multiplier applied when the line also matches an escalation pattern. Risk
divides: a high-risk change ranks lower than an equally impactful safe one.

Findings below `min_score` are dropped. The rest are sorted by score and filed
up to `max_issues_per_run`.

**Deduplication.** Every issue body ends with a hidden marker:

```
<!-- autonomous-loop:fingerprint:a1b2c3d4e5f6a7b8 -->
```

The fingerprint hashes file path, keyword, and note text — deliberately not the
line number, so an unrelated edit that shifts lines does not produce a second
issue for the same marker. Before filing, the orchestrator reads every open
issue labelled `autonomous-loop` and skips fingerprints it already sees.

Without this, a weekly schedule files the same issues every week forever. That
is not hypothetical: this repository accumulated 33 identical issues across 11
scheduled runs before deduplication existed.

## Auto-reviewer

Decides whether a pull request may merge with no human involved. The bar is
deliberately high, and the failure mode is deliberately conservative.

**It reads the diff.** For every changed file it walks the patch and inspects
lines beginning with `+` or `-` against `DANGEROUS_DIFF_PATTERNS`. A decision
made from the filename alone cannot see what a change does — a `README.md`
containing a hardcoded credential is not a safe documentation change.

**A missing patch is a blocker, not a pass.** Binary files and files too large
for the API return no patch. Something that cannot be inspected does not
auto-merge.

**Auto-merge requires every one of:**

| Condition | Why |
|---|---|
| all paths in `AUTO_MERGE_GLOBS` | documentation and plain text only |
| no path in `CRITICAL_PATH_GLOBS` | CI, dependencies, infra, auth always need a human |
| ≤ `MAX_AUTO_MERGE_FILES` files | a wide change is a design change |
| ≤ `MAX_AUTO_MERGE_LINES` lines | keeps the reviewable surface small |
| no dangerous pattern in the diff | content check, not extension check |
| CI green | pending, absent, and unreadable all count as not green |

`.yml` is absent from `AUTO_MERGE_GLOBS` on purpose. A YAML file is usually
configuration that changes behaviour, and telling CI config from data by
extension alone is not something this tool can do reliably.

**It fails closed.** The top-level handler in `main()` catches everything and
produces a "human must review" verdict. There is no path where an error results
in a merge. It exits 0 even on internal error, so the workflow still posts the
comment rather than skipping the step.

## Workflow doctor

Downloads the failed run's log archive, unzips it, and matches the real log text
against `FAILURE_SIGNATURES`. When nothing matches it reports `unknown` and
includes the most relevant excerpt rather than inventing a diagnosis.

**It does not edit workflow files.** An earlier version "fixed" permissions by
loading a workflow with `yaml.safe_load` and writing it back with `yaml.dump`.
Under YAML 1.1, the key `on` parses as the boolean `true`, so the round trip
rewrote `on:` as `true:` and stripped every comment. The workflow it repaired
became permanently un-runnable. `workflow_doctor.py` no longer imports `yaml`,
and its only file writes are appends to `$GITHUB_OUTPUT` and
`$GITHUB_STEP_SUMMARY`.

**One issue per (workflow, failure type).** Repeat failures add a comment to the
existing issue. A workflow failing every hour otherwise generates an issue every
hour.

## Security model

These workflows hold write access to the repository, which makes a few
constraints non-negotiable.

**The reviewer never executes code from the PR it reviews.** It checks out
`github.event.pull_request.base.sha` — the trusted target branch. With a head
checkout, a pull request could rewrite `auto_reviewer.py` and have its own
modified reviewer approve it, using the workflow's write token.

**Untrusted text goes through `env:`.** PR titles, bodies, branch names, and
log excerpts are passed to `github-script` as environment variables and read via
`process.env`. Interpolating them directly into a script body with `${{ }}`
allows a crafted PR title to execute as JavaScript.

**Permissions are per-job.** Scanning and diagnosis run with read access.
`contents: write` exists only on the merge job, gated on an `APPROVE` verdict.

**Repository content is untrusted input to any agent.** Issue bodies, PR
descriptions, code comments, and README text have been used to redirect coding
agents into exfiltrating credentials; the pattern has assigned CVEs, and filing
a public issue has been sufficient to trigger it. Never give a workflow that
ingests untrusted text both `id-token: write` and `contents: write`.

**Actions are referenced by major-version tag.** Pinning to full commit SHAs is
stronger for a workflow holding write access, since tag rewrites have been used
to compromise Actions consumers at scale.

## What this system does not do

- **It does not close the loop.** The orchestrator files issues; nothing here
  implements them. Wiring a coding agent to the `autonomous-loop` label is a
  separate, deliberate decision.
- **It does not measure outcome quality.** No component tracks whether a filed
  issue was useful or a merged change was correct. Run counts and issue counts
  measure activity, not value. If you want that signal, you have to build it —
  and it is the most valuable thing missing.
- **It does not survive repository inactivity.** GitHub disables scheduled
  workflows after 60 days without activity and does not notify anyone.
