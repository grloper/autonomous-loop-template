# Architecture

Three tools. They share a repository and a label namespace; none calls another.
A chain where each stage assumes the previous one succeeded fails silently at
the first broken link, and that is exactly how the earlier version of this repo
died — the scanner ran weekly for eleven weeks while nothing downstream of it
ever executed, and every run reported success.

```
pull_request ──▶ gate.py ──▶ review + verdict            [contents: read]
                    │         (policy + provenance +
                    │          diff rules + injection)
                    └─ auto_merge ──▶ merge job          [contents: write]

schedule ──────▶ scan.py ──▶ deduplicated issues         [issues: write]

workflow_run ──▶ doctor.py ─▶ one issue per failure type [actions: read]

schedule ──────▶ outcomes.py ▶ trust ledger + scoreboard [pull-requests: read]
                    │
                    └────────▶ read back by gate.py to widen the allowlist
```

The loop closes at `outcomes.py`. Everything else in this repository is a
prediction made before merge; that module is the only measurement taken after
one, and therefore the only thing that can tell you whether the predictions
were any good.

## Module layout

| File | Responsibility |
|---|---|
| `policy.py` | Loads `.github/agent-policy.yml`, merges over strict defaults, classifies authorship. No I/O beyond reading that one file. |
| `injection.py` | Detects text shaped like an attempt to instruct an agent. Pure functions over strings. |
| `gate.py` | `evaluate()` is a pure function over `PullRequestFacts`. Everything touching GitHub lives in `facts_from_github()`. |
| `demo.py` | Runs `evaluate()` over built-in scenarios. No network. |
| `scan.py` | Marker scanning and issue filing. |
| `doctor.py` | Failed-run log diagnosis. |
| `outcomes.py` | Revert and branch-break detection, Wilson-bounded trust scoring. Pure analysis plus a GitHub collector, same split as `gate.py`. |

The pure-core / thin-adapter split in `gate.py` is the load-bearing design
decision. It is why the gate can be demonstrated offline, why the tests need no
GitHub mocking beyond plain dataclasses, and why the decision logic is readable
without knowing the PyGithub API.

## The gate

`evaluate(policy, facts) -> Decision`. Ordering matters:

1. **Provenance.** `looks_like_agent()` checks the author against known agent
   accounts, any `[bot]` suffix, branch prefixes, and title markers. Unknown
   authorship resolves to *agent*, the stricter profile.
2. **Injection scan** of title, body, and branch — the fields an attacker
   controls without any repository permission.
3. **Per-file checks.** Protected path? Outside the allowlist? Patch readable?
   Then every added and removed line against the policy's `diff_rules`, plus an
   injection scan of added lines only (removing a payload is a fix).
4. **Size limits** from the active profile.
5. **CI state.** Only a confirmed pass counts. Pending, absent, and unreadable
   are all "not green".
6. **Severity resolution.** `critical` injection signals (secret access,
   exfiltration, guardrail escalation) request changes. `high` signals (hidden
   text, instruction override) block auto-merge without asserting intent —
   concealed text is not always an attack, but it is never safe to merge unread.

A missing patch is a blocker, not a pass. Binary files and oversized diffs
return no patch from the API; something that cannot be inspected cannot be
judged safe.

## Why policy is a file

Constants inside the enforcing tool mean every consumer maintains a fork, and a
threshold change is invisible in review. A YAML file makes tuning a diff someone
signs off on.

The failure mode is chosen deliberately: an unparseable policy falls back to
strict defaults **and** adds a blocker. Relaxing enforcement because a config
file broke is the wrong direction to fail.

## Injection detection, and why precision beats recall

Rules are grouped into four categories: instruction override, secret access,
exfiltration, and self-escalation. Three of the four require a corroborating
*imperative* on the same text — an instruction aimed at a reader — because
documentation that merely discusses secrets is not an attack. Only instruction
override fires alone, since it is definitionally an instruction.

Concealment is detected separately: zero-width characters, bidi overrides
(Trojan Source), and HTML comments containing instructions. The HTML-comment
rule additionally requires either direct address ("you", "agent") or a payload
match, because `<!-- generated file, do not edit -->` is an imperative and is
entirely benign. That false positive was caught by the demo during development.

A scanner that fires on ordinary READMEs gets switched off within a week, and a
switched-off scanner detects nothing. Test coverage includes explicit
false-positive cases for this reason.

## Security model

**The gate never executes code from the PR it reviews.** `gate.yml` checks out
`github.event.pull_request.base.sha`. With a head checkout, a PR could rewrite
`gate.py` and have its own modified gate approve it using the workflow's token.

**Untrusted text goes through `env:`.** PR titles, bodies, branch names, and log
excerpts reach `github-script` as environment variables read via `process.env`.
Interpolating them into a script body with `${{ }}` lets a crafted PR title
execute as JavaScript.

**Permissions are per-job.** `contents: write` exists only on the merge job.

**Repository content is untrusted input to any agent.** Never give a workflow
that ingests untrusted text both `id-token: write` and `contents: write` — the
policy ships a `diff_rules` entry that flags exactly that combination.

`scripts/verify-setup.sh` asserts each property and fails the build on
regression.

## Earned autonomy

`outcomes.py` answers two questions per merged pull request — was it reverted,
did it break the default branch — and aggregates the answers per author.

Both detectors are deliberately conservative. Revert matching prefers an
explicit `#number` reference and falls back to subject matching; break
attribution counts only the merge commit's own CI result, because blaming a
merge for a later failure would attribute flaky infrastructure to whoever
merged most recently. Under-counting failures is the safer error: it makes
trust harder to earn, not easier.

Scores use the lower bound of a 95% Wilson interval rather than the raw survival
rate. One clean merge yields 20.7% confidence, twenty yields 83.9%, a hundred
yields 96.3%. Without that, a single lucky merge reads as certainty and the
mechanism becomes a way to launder luck into permission.

Trust only widens `auto_merge_paths`, and only to patterns the policy names in
`trust.trusted_auto_merge_paths`. It cannot unlock a protected path or relax CI,
size, diff, or injection checks — `tests/test_outcomes.py` asserts each of those
independently. It ships disabled.

## What this does not do

- **It does not implement the issues `scan.py` files.** Wiring a coding agent to
  the `autonomous-loop` label is a separate, deliberate decision.
- **It cannot see a silent undo.** A rewrite that reverses a change without
  saying "revert" does not register as a failure.
- **It does not survive repository inactivity.** GitHub disables scheduled
  workflows after 60 days without activity and notifies no one.
