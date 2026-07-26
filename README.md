# Agent Gate

**Which of your coding agents can you actually trust to merge?**

[![CI](https://github.com/grloper/autonomous-pipeline-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/grloper/autonomous-pipeline-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Your repo has Copilot, Claude, Devin, and Cursor opening pull requests. You have
no idea which one's code survives contact with production, because nobody
measures it. Branch protection asks *"did a human click approve?"* CI asks *"do
the tests pass?"* Neither asks the question you actually care about.

Agent Gate does two things:

1. **Blocks** machine-authored changes that shouldn't merge unread — by reading
   the diff, not the filename, and by catching text designed to hijack the *next*
   agent that reads your repo.
2. **Measures** what happened after every merge — reverts, branch breakage — and
   turns that into a per-agent survival score. Agents that earn a track record
   get more autonomy. Agents that don't, don't.

The second part is the one nobody else does.

## See it in 5 seconds

No token, no network, no signup:

```console
$ python .github/scripts/demo.py

Merge gate — policy: .github/agent-policy.yml

scenario                                     author  verdict          auto-merge
────────────────────────────────────────────────────────────────────────────────────
agent fixes a typo in the docs               agent   APPROVE          yes
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

Earned autonomy (trust.enabled: true, trusted_auto_merge_paths: [tests/**])
────────────────────────────────────────────────────────────────────────────────────
new agent, no track record                   agent   COMMENT          no
                                             └─ `tests/test_parser.py` is outside the auto-merge allowlist
same PR, agent rated trusted                 agent   APPROVE          yes
                                             └─ trusted: tests/** is unlocked

All 12 scenarios behaved as documented.
```

Look at the last two rows. **Same pull request. Different answer.** The only
thing that changed is that one agent has a measured track record and the other
doesn't.

These scenarios run as tests in CI, so this output can't drift from the code.

## Earned autonomy

`outcomes.py` walks your merge history and asks two questions per merged PR:
was it reverted, and did it break the default branch? That produces a scoreboard:

| author | kind | merges | reverts | breaks | survival | confidence | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `some-new-tool[bot]` | agent | 34 | 6 | 2 | 76% | 60% | untrusted |
| `copilot-swe-agent[bot]` | agent | 212 | 3 | 1 | 98% | 95% | trusted |
| `alice` | human | 88 | 2 | 0 | 98% | 92% | watch |

`confidence` is the **lower bound of a 95% Wilson interval**, not the raw rate.
That distinction is the whole mechanism:

```
   1 merge,  0 failures -> raw 100%  confidence 20.7%  insufficient-data
  20 merges, 0 failures -> raw 100%  confidence 83.9%  watch
 100 merges, 0 failures -> raw 100%  confidence 96.3%  trusted
```

One lucky merge cannot buy autonomy. Confidence is earned with volume, and a
single revert visibly costs an agent ground. Without this, trust scoring is just
a way to launder luck into permission.

Trust only ever **widens** the allowlist, and only for paths you explicitly
name. It never unlocks a protected path and never relaxes CI, size, diff, or
injection checks — there are tests asserting each of those.

Ships **disabled**. Turning it on is a decision you make.

## Why the blocking half is better than it looks

**It reads the diff, not the filename.** A `README.md` with a live API key is not
a safe documentation change. Extension-based rules can't see that.

**It knows who wrote the PR.** Bot accounts, agent branch prefixes, and title
markers select a stricter profile. Unknown authorship is treated as
agent-authored — being wrong strictly costs one review; being wrong permissively
merges unread machine output.

**It scans for prompt injection.** Your agents read issue bodies, PR
descriptions, and code comments. Anything they read, an attacker can write. This
is a live attack class with assigned CVEs across multiple vendors, and in the
disclosed `claude-code-action` compromise an *issue title alone* carried the
payload. Agent Gate flags instruction overrides, credential paths like
`/proc/self/environ`, exfiltration to a URL, guardrail-disabling flags,
zero-width characters, bidi overrides, and instructions hidden in HTML comments.

**It fails closed.** Unreadable diff, unknown CI, unparseable policy, an
exception anywhere — all block. No failure path merges.

## Install

```bash
git clone https://github.com/grloper/autonomous-pipeline-agents /tmp/gate
cp -r /tmp/gate/.github/scripts .github/
cp    /tmp/gate/.github/workflows/{gate,outcomes}.yml .github/workflows/
cp    /tmp/gate/.github/agent-policy.yml .github/
```

Edit `protected_paths` in `.github/agent-policy.yml` to name your auth, payments,
migration, and infrastructure directories. Run the demo to confirm the policy
does what you meant.

## Policy

```yaml
version: 1

provenance:
  actors: [copilot-swe-agent[bot], claude[bot], devin-ai-integration[bot]]
  branch_prefixes: [copilot/, claude/, agent/]

protected_paths:              # always a human, whoever wrote it
  - ".github/**"
  - "**/*auth*"
  - "**/migrations/**"

profiles:
  agent:
    auto_merge_paths: ["**/*.md", "docs/**"]
    max_files: 5
    max_lines: 150
    require_ci: true
  human:
    auto_merge_paths: []      # people merge their own work

trust:                        # earned autonomy — off by default
  enabled: false
  min_sample: 20
  trusted: 0.95
  trusted_auto_merge_paths: ["tests/**"]

diff_rules:
  - id: hardcoded-secret
    pattern: '(?i)\b(api[_-]?key|secret|token)\b\s*[=:]\s*[''"][^''"]{8,}'
    severity: block
    message: looks like a hardcoded credential
```

Omitted keys keep their defaults. A policy that can't be parsed falls back to
strict built-ins **and** blocks auto-merge until you fix it.

## Auto-merge requires all of these

| Condition | Why |
|---|---|
| path in the profile's allowlist (or a trust-earned one) | documentation only, by default |
| no path in `protected_paths` | CI, deps, auth, infra always need a human |
| within `max_files` / `max_lines` | a wide change is a design change |
| no `block` rule matches the diff | content check, not extension check |
| no critical injection signal | in PR text or added lines |
| CI green | pending, absent, unreadable all count as not green |
| policy loaded cleanly | a policy you can't read isn't enforceable |

## Also included

- **`scan.py`** — finds `TODO`/`FIXME`/`HACK`/`XXX`/`BUG`, scores them
  `impact × urgency ÷ risk`, files deduplicated issues. Markers only count inside
  comments, so config tables don't trip it.
- **`doctor.py`** — downloads a failed run's logs, matches known failure
  signatures, files one issue per (workflow, failure type). Diagnoses only; never
  edits workflow files.

## Security

This holds write access to your repo, so:

- **The gate never runs code from the PR it reviews.** It checks out `base.sha`.
  With a head checkout, a PR could rewrite `gate.py` and approve itself.
- **Author-controlled text reaches scripts via `env:`**, never `${{ }}`
  interpolation inside a script body.
- **`contents: write` exists only on the merge job.**

`scripts/verify-setup.sh` asserts each and fails the build on regression.

## Honest limits

- `diff_rules` is a regex list. It catches carelessness and known-bad idioms; it
  will not stop a determined author.
- Injection detection is heuristic, tuned for precision over recall. A scanner
  that fires on every README gets muted, and a muted scanner detects nothing. It
  will miss novel phrasings.
- Revert detection matches revert commits and PRs. A silent rewrite that undoes a
  change without saying "revert" is invisible to it.
- Branch-break attribution is deliberately narrow — only the merge commit's own
  CI result counts, so flaky infrastructure isn't blamed on whoever merged last.
- Trust scores need volume. Below `min_sample` merges, an author is
  `insufficient-data` no matter how clean the record.

## Development

```bash
pip install -r .github/scripts/requirements.txt pyyaml
python -m unittest discover -s tests -v   # 114 tests
python .github/scripts/demo.py            # 12 scenarios
bash scripts/verify-setup.sh              # 35 checks
```

## License

MIT.
