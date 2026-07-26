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
                    ├────────▶ read back by gate.py to widen the allowlist
                    ▼
schedule ──────▶ prompts.py ─▶ proposed instruction rules  [issues: write]
                    │
                    └────────▶ a human accepts → agents behave differently
```

Two return paths make this a loop rather than a pipeline. `outcomes.py` feeds
measured reliability back into what an agent is *allowed* to do; `prompts.py`
feeds measured failures back into what an agent is *told* to do. Everything
upstream of them is a prediction made before merge; these two are the only
measurements taken after one.

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
| `prompts.py` | Clusters recurring failures into proposed instruction rules. Owns one delimited block in the instructions file and nothing else. |
| `synth.py` | Drafts a rule for a failure class the catalogue lacks, then validates the model's output before anyone sees it. |

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

## Learning from failures

`prompts.py` closes the second return path. It reads gate verdicts and merge
outcomes, groups them by failure class, and proposes the instruction that would
have prevented each recurring one.

**Proposals are never applied.** An agent able to edit its own guardrails can
remove them, and that is a documented attack rather than a theoretical one —
CVE-2025-53773 was a prompt injection that wrote `chat.tools.autoApprove` into a
settings file and disabled every tool confirmation. The CLI gates writing behind
`--apply`, intended for a human-reviewed pull request, and `verify-setup.sh`
fails the build if that guard disappears.

**The tool owns one delimited block.** Edits land between two HTML-comment
markers; the rest of the instructions file is never read for anything but those
markers. A test applies two successive rule sets to hand-written prose and
asserts every original line survives.

**Rules are earned and retired.** Three occurrences before a rule is proposed;
retirement proposed once a failure class has been absent for 100 pull requests.
Both thresholds exist for the same reason: an instructions file long enough to
skim is one agents stop following, so rules have to justify their space both
when they arrive and when they stay.

**Rules constrain, never permit.** The catalogue is asserted in tests to contain
no phrasing that widens what an agent may do. A learned rule can say "do not"; it
can never say "you may skip review". Otherwise the loop could talk itself into
more autonomy than it earned.

## Synthesising rules, and the injection problem

`synth.py` handles failure classes the catalogue does not cover. The engineering
problem is not the model call; it is that the input is attacker-controlled.
Pull request titles, branch names, and diff lines are written by whoever opened
the pull request, and the output is proposed for the file that steers every
future agent. Filing three pull requests whose details read "agents may merge
anything" is a cheap attempt to legislate.

Four defences, in ascending order of how much weight they carry:

1. **Synthesis only runs for uncatalogued classes.** The common path never
   reaches a model, so the attack surface exists only for novel failures.
2. **Evidence is fenced, flattened, truncated, and labelled untrusted**, and
   comment markers inside it are neutered so it cannot terminate the structure
   around it. Delimiting does not make text safe — no arrangement of tags makes
   a model immune to what it reads — but it makes the boundary explicit and
   keeps the prompt well-formed.
3. **The system prompt states that only a restriction is acceptable**, and asks
   the model to flag evidence that appears to be steering it. A flagged draft is
   never accepted.
4. **Generated text is validated by code.** Permissive phrasing, URLs,
   credential sources, shell commands, multi-line output, oversized rules, and
   HTML comment markers each reject the draft outright.

Defence 4 is the only one that decides anything. The first three reduce how
often a bad draft is produced; validation determines what is allowed through,
and it runs after the model has spoken. `tests/test_synth.py` includes the full
attack: hostile evidence, a model that complies with it, and the assertion that
the resulting rule is still refused.

Rejected drafts are reported rather than dropped — including when nothing else
is proposed — because a draft refused for granting permission is the strongest
available signal that someone is feeding the loop crafted evidence.

## What this does not do

- **It does not implement the issues `scan.py` files.** Wiring a coding agent to
  the `autonomous-loop` label is a separate, deliberate decision.
- **It cannot see a silent undo.** A rewrite that reverses a change without
  saying "revert" does not register as a failure.
- **It cannot invent a rule for a novel mistake without a model.** Absent
  `--synthesize` and an API key, an unfamiliar failure produces nothing.
- **Synthesis is best-effort.** Validation bounds what a bad draft can say; it
  does not guarantee a good one. Human approval is the control that matters.
- **It does not survive repository inactivity.** GitHub disables scheduled
  workflows after 60 days without activity and notifies no one.
