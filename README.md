# Merge gate for AI-authored pull requests

[![CI](https://github.com/grloper/autonomous-pipeline-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/grloper/autonomous-pipeline-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Coding agents open pull requests now. Copilot, Claude, Devin, Cursor — they all
push branches and ask to merge. Branch protection asks *"did a human approve
this?"* and CI asks *"do the tests pass?"* Neither asks the question that
actually matters:

> **Should a machine-authored change merge without anyone reading it?**

This is a policy engine that answers that. It reads the diff, checks who wrote
it, scans for text trying to hijack the *next* agent, and refuses to merge
anything it could not fully inspect.

## Demo

No token, no network, no setup:

```console
$ python .github/scripts/demo.py

Merge gate — policy: .github/agent-policy.yml

scenario                                     author  verdict          auto-merge
────────────────────────────────────────────────────────────────────────────────────
agent fixes a typo in the docs               agent   APPROVE          yes
                                             └─ —
agent edits a CI workflow                    agent   COMMENT          no
                                             └─ `.github/workflows/ci.yml` is a protected path
agent adds a credential to a README          agent   REQUEST_CHANGES  no
                                             └─ `README.md`: looks like a hardcoded credential
agent PR whose body targets the next agent   agent   REQUEST_CHANGES  no
                                             └─ [high] PR body: instructs a reader to ignore previous instructions
agent hides instructions in an HTML comment  agent   COMMENT          no
                                             └─ [high] README.md: HTML comment contains instructions addressed to a reader
agent adds docker-compose.yml                agent   COMMENT          no
                                             └─ `docker-compose.yml` is a protected path
agent doc fix, but CI is red                 agent   COMMENT          no
                                             └─ CI is not green (failing: unit-tests)
agent submits a binary file                  agent   COMMENT          no
                                             └─ `docs/arch.md`: diff unavailable, so it cannot be inspected
agent rewrites 400 lines of docs             agent   COMMENT          no
                                             └─ 400 lines changed (limit 150)
human fixes a typo in the docs               human   COMMENT          no
                                             └─ `docs/install.md` is outside the auto-merge allowlist

All 10 scenarios behaved as documented.
```

Add `--verbose` to see the full review body the gate posts. Change
`.github/agent-policy.yml`, re-run, and watch the verdicts move — that is the
whole feedback loop for tuning policy.

These same ten scenarios run in CI as tests, so this output cannot drift from
what the code does.

## What makes it different

**It reads the diff, not the filename.** A `README.md` containing a live API
key is not a safe documentation change. Extension-based rules cannot see that;
this catches it.

**It knows who wrote the PR.** Bot accounts, known agent branch prefixes, and
agent title markers select a stricter profile. Unknown authorship is treated as
agent-authored — being wrong in the strict direction costs one human review;
being wrong the other way merges unread machine output.

**It scans for prompt injection.** Your agents read issue bodies, PR
descriptions, and code comments. Anything they read, an attacker can write —
this is a live attack class with assigned CVEs across multiple vendors, and in
the disclosed `claude-code-action` compromise an *issue title alone* carried the
payload. The gate flags text shaped like an attempt to give your agent orders:
instruction overrides, credential-read paths like `/proc/self/environ`,
exfiltration to a URL, guardrail-disabling flags, zero-width characters, bidi
overrides, and instructions concealed in HTML comments.

**It fails closed.** Unreadable diff, unknown CI state, unparseable policy, an
exception anywhere — every one of them blocks the merge. There is no code path
where a failure results in a merge.

**Policy is a file, not a fork.** Everything lives in
`.github/agent-policy.yml`. Tuning the gate is a reviewable pull request, not a
patch to someone else's Python.

## Install

```bash
git clone https://github.com/grloper/autonomous-pipeline-agents /tmp/gate
cp -r /tmp/gate/.github/scripts .github/
cp    /tmp/gate/.github/workflows/gate.yml .github/workflows/
cp    /tmp/gate/.github/agent-policy.yml   .github/
```

Then edit `protected_paths` in `.github/agent-policy.yml` to name your auth,
payments, migration, and infrastructure directories, and run the demo to
confirm the policy behaves the way you meant.

## Policy

```yaml
version: 1

provenance:
  actors: [copilot-swe-agent[bot], claude[bot], devin-ai-integration[bot]]
  branch_prefixes: [copilot/, claude/, agent/]

protected_paths:          # always a human, whoever wrote it
  - ".github/**"
  - "**/*auth*"
  - "**/migrations/**"
  - "**/package-lock.json"

profiles:
  agent:                  # machine-authored
    auto_merge_paths: ["**/*.md", "docs/**"]
    max_files: 5
    max_lines: 150
    require_ci: true
  human:                  # people merge their own work
    auto_merge_paths: []

diff_rules:
  - id: hardcoded-secret
    pattern: '(?i)\b(api[_-]?key|secret|token)\b\s*[=:]\s*[''"][^''"]{8,}'
    severity: block       # block -> REQUEST_CHANGES, warn -> blocks auto-merge only
    message: looks like a hardcoded credential
```

Omitted keys keep their defaults. A policy file that cannot be parsed falls back
to the strict built-ins **and** blocks auto-merge until it is fixed.

## Auto-merge requires all of these

| Condition | Why |
|---|---|
| every path in the profile's `auto_merge_paths` | documentation only, by default |
| no path in `protected_paths` | CI, deps, auth, infra always need a human |
| within `max_files` and `max_lines` | a wide change is a design change |
| no `block` rule matches the diff | content check, not extension check |
| no critical injection signal | in the PR text or the added lines |
| CI green | pending, absent, and unreadable all count as not green |
| policy loaded cleanly | a policy you can't read isn't enforceable |

## Also included

Two smaller tools that share the same repository:

- **`scan.py`** — finds `TODO`/`FIXME`/`HACK`/`XXX`/`BUG` comments, scores them
  `impact × urgency ÷ risk`, and files deduplicated issues. Markers only count
  inside comments, so config tables and string literals don't trip it.
- **`doctor.py`** — downloads a failed run's logs, matches them against known
  failure signatures, and files one issue per (workflow, failure type). It
  diagnoses only; it never edits workflow files.

## Security

This workflow holds write access to your repository, so:

- **The gate never runs code from the PR it reviews.** It checks out `base.sha`.
  With a head checkout, a pull request could rewrite `gate.py` and have its own
  modified gate approve it.
- **Author-controlled text reaches scripts via `env:`**, never `${{ }}`
  interpolation inside a script body, which would let a crafted PR title execute
  as JavaScript.
- **`contents: write` exists only on the merge job.**
- **Pin actions to full commit SHAs** if you want to go further; tag rewrites
  have been used to compromise Actions consumers at scale.

`scripts/verify-setup.sh` asserts each of these and fails the build if one
regresses.

## Limits

Worth knowing before you rely on it:

- `diff_rules` is a regex list. It catches careless changes and known-bad
  idioms; it will not stop a determined author.
- Injection detection is heuristic. It is tuned for precision over recall — a
  scanner that fires on every README gets muted, and a muted scanner detects
  nothing. It will miss novel phrasings.
- The auto-merge allowlist is documentation-only by default. Widening it shifts
  risk onto the pattern list, which is the weaker of the two controls.
- **Nothing here measures whether a merged change was correct.** Revert rate and
  post-merge CI breakage are the signals that would close that loop, and they
  are not implemented.

## Development

```bash
pip install -r .github/scripts/requirements.txt pyyaml
python -m unittest discover -s tests -v   # 79 tests
python .github/scripts/demo.py            # 10 scenarios
bash scripts/verify-setup.sh              # 31 checks
```

## License

MIT.
