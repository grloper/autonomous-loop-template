#!/usr/bin/env python3
"""
The merge gate: decides whether a pull request may merge without a human.

Structure: `evaluate()` is a pure function over plain data. Everything that
touches GitHub lives in `facts_from_github()`. That split is why the gate can
be tested and demonstrated offline, and why the decision logic is readable
without knowing the PyGithub API.

Two rules govern every decision:

  Fail closed.  Any error, any unreadable input, any unknown state produces
  "a human must look at this". There is no path where a failure merges.

  Read the content.  Filenames say nothing about what a change does. A
  `README.md` holding a credential is not a safe documentation change.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import re  # noqa: E402

import injection  # noqa: E402
import policy as policy_mod  # noqa: E402


def changed_text(patch: str) -> str:
    """Added and removed lines, normalised so a construct split across lines
    is still visible to a single-line rule.

    Adversarial testing found that every content rule could be evaded simply by
    inserting a newline:

        +api_key = (
        +    "sk-live-abcdef123456"
        +)

    Each line on its own matches nothing. Rules are still applied per line as
    well — this is an additional view, not a replacement, because the per-line
    form gives better error messages when it does match.
    """
    body = "\n".join(
        line[1:] for line in (patch or "").splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )
    # Join string literals split by concatenation, drop line continuations and
    # grouping punctuation, then collapse all whitespace to single spaces.
    body = re.sub(r"\\\s*\n", " ", body)
    body = re.sub(r"['\"]\s*\+\s*['\"]", "", body)
    body = re.sub(r"[()\[\]{}]", " ", body)
    return re.sub(r"\s+", " ", body).strip()


@dataclass
class ChangedFile:
    filename: str
    patch: str | None = ""
    additions: int = 0
    deletions: int = 0

    @property
    def churn(self) -> int:
        return (self.additions or 0) + (self.deletions or 0)


@dataclass
class PullRequestFacts:
    """Everything the gate needs, with no GitHub types involved."""
    number: int = 0
    title: str = ""
    body: str = ""
    actor: str = ""
    branch: str = ""
    draft: bool = False
    files: list = field(default_factory=list)
    ci_state: str = "unknown"      # passing | failing | pending | none | unknown
    ci_detail: str = ""


@dataclass
class Decision:
    verdict: str = "COMMENT"          # APPROVE | REQUEST_CHANGES | COMMENT
    auto_merge: bool = False
    is_agent: bool = False
    provenance_reason: str = ""
    blockers: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    injection_signals: list = field(default_factory=list)
    protected_paths: list = field(default_factory=list)
    policy_warnings: list = field(default_factory=list)
    trusted: bool = False
    summary: str = ""


def evaluate(pol: policy_mod.Policy, pr: PullRequestFacts,
             trusted: frozenset = frozenset()) -> Decision:
    """Pure decision function. No I/O, no network, no GitHub objects.

    `trusted` is the set of author identities that outcomes.py has rated
    `trusted`. It only ever widens the allowlist, and only for paths the policy
    explicitly names in `trust.trusted_auto_merge_paths` — a good track record
    never unlocks a protected path, and never relaxes any other check.
    """
    d = Decision(policy_warnings=list(pol.warnings))
    d.is_agent, d.provenance_reason = policy_mod.looks_like_agent(
        pol, pr.actor, pr.branch, pr.title)
    profile = pol.profile_for(d.is_agent)

    allowed_paths = list(profile.auto_merge_paths)
    if pol.trust_enabled and pr.actor in trusted:
        earned = list(pol.trust.get("trusted_auto_merge_paths") or [])
        if earned:
            allowed_paths += earned
            d.trusted = True
            d.provenance_reason += (
                f"; rated trusted by measured outcomes, so "
                f"{len(earned)} additional path pattern(s) may auto-merge")

    if pr.draft:
        d.summary = "Draft pull request — not reviewed."
        return d

    if not pr.files:
        d.blockers.append("no changed files could be read")
        d.summary = "The changed-file list was empty or unreadable."
        return d

    # 1. Injection signals in the fields an attacker controls.
    d.injection_signals = injection.scan_pull_request(pr.title, pr.body, pr.branch)

    # 2. Per-file path and content checks.
    total_churn = 0
    for f in pr.files:
        total_churn += f.churn

        if policy_mod.path_is_suspicious(f.filename):
            d.blockers.append(f"`{f.filename}` escapes the repository root")
            d.protected_paths.append(f.filename)
        if pol.is_protected(f.filename):
            d.protected_paths.append(f.filename)
            d.blockers.append(f"`{f.filename}` is a protected path")
        elif not policy_mod.match_any(f.filename, allowed_paths):
            d.blockers.append(f"`{f.filename}` is outside the auto-merge allowlist")

        if f.patch is None or f.patch == "":
            # Binary, too large, or unavailable. Something we cannot read
            # cannot be judged safe.
            d.blockers.append(f"`{f.filename}`: diff unavailable, so it cannot be inspected")
            continue

        matched_rules = set()
        for line in f.patch.splitlines():
            if not line or line[0] not in "+-" or line.startswith(("+++", "---")):
                continue
            for rule in pol.diff_rules:
                if rule.id in matched_rules or not rule.matches(line):
                    continue
                matched_rules.add(rule.id)
                entry = f"`{f.filename}`: {rule.message} — `{line.strip()[:110]}`"
                if rule.severity == "block":
                    d.findings.append(entry)
                else:
                    d.blockers.append(f"{entry} (warning)")

        # Second pass over the normalised whole-hunk view, catching constructs
        # a newline would otherwise hide from the per-line pass.
        joined = changed_text(f.patch)
        for rule in pol.diff_rules:
            if rule.id in matched_rules or not rule.matches(joined):
                continue
            matched_rules.add(rule.id)
            entry = (f"`{f.filename}`: {rule.message} — split across lines, "
                     f"matched after normalising")
            if rule.severity == "block":
                d.findings.append(entry)
            else:
                d.blockers.append(f"{entry} (warning)")

        d.injection_signals.extend(injection.scan_diff(f.patch, f.filename))

    # 3. Size limits.
    if profile.max_files and len(pr.files) > profile.max_files:
        d.blockers.append(f"{len(pr.files)} files changed (limit {profile.max_files})")
    if profile.max_lines and total_churn > profile.max_lines:
        d.blockers.append(f"{total_churn} lines changed (limit {profile.max_lines})")
    if not allowed_paths:
        d.blockers.append(
            f"the '{'agent' if d.is_agent else 'human'}' profile has auto-merge disabled")

    # 4. CI. Anything other than a confirmed pass blocks.
    if profile.require_ci and pr.ci_state != "passing":
        d.blockers.append(f"CI is not green ({pr.ci_state}: {pr.ci_detail or 'no detail'})")

    # 5. Policy problems block auto-merge — a policy we could not read is not a
    #    policy we can enforce.
    if d.policy_warnings:
        d.blockers.append("policy could not be loaded cleanly")

    # 6. Injection signals. `critical` (secret access, exfiltration, guardrail
    #    escalation) requests changes. `high` (hidden text, instruction
    #    override) blocks auto-merge without asserting intent — concealed text
    #    is not always an attack, but it is never safe to merge unread.
    critical_injection = [s for s in d.injection_signals if s.severity == "critical"]
    high_injection = [s for s in d.injection_signals if s.severity == "high"]
    if high_injection and not critical_injection:
        d.blockers.append(
            f"{len(high_injection)} prompt-injection signal(s) need a human to read them")

    # Verdict.
    if d.findings or critical_injection:
        d.verdict = "REQUEST_CHANGES"
        d.auto_merge = False
        parts = []
        if d.findings:
            parts.append(f"{len(d.findings)} policy violation(s) in the diff")
        if critical_injection:
            parts.append(f"{len(critical_injection)} prompt-injection signal(s)")
        d.summary = " and ".join(parts) + ". This will not be merged automatically."
    elif d.blockers:
        d.verdict = "COMMENT"
        d.auto_merge = False
        d.summary = (f"Diff is clean, but {len(d.blockers)} condition(s) block "
                     f"auto-merge. Review and merge manually.")
    else:
        d.verdict = "APPROVE"
        d.auto_merge = True
        d.summary = (f"{len(pr.files)} file(s), {total_churn} lines, clean diff, "
                     f"CI green. Approved for auto-merge.")
    return d


def render(d: Decision, pr: PullRequestFacts) -> str:
    """Human-readable review body."""
    header = f"**Merge gate: {d.verdict}**"
    if pr.number:
        header += f" (PR #{pr.number})"
    lines = [
        header,
        "",
        d.summary,
        "",
        f"Author profile: **{'agent' if d.is_agent else 'human'}** — {d.provenance_reason}",
    ]
    if d.injection_signals:
        lines += ["", "### Prompt-injection signals", "",
                  "Text in this pull request is shaped like an attempt to give "
                  "instructions to an agent reading it."]
        lines += [f"- {s}" for s in d.injection_signals[:10]]
    if d.findings:
        lines += ["", "### Policy violations in the diff"]
        lines += [f"- {f}" for f in d.findings[:15]]
    if d.protected_paths:
        lines += ["", "### Protected paths touched"]
        lines += [f"- `{p}`" for p in d.protected_paths[:15]]
    if d.blockers:
        lines += ["", "### Why this will not auto-merge"]
        lines += [f"- {b}" for b in d.blockers[:15]]
    if d.policy_warnings:
        lines += ["", "### Policy warnings"]
        lines += [f"- {w}" for w in d.policy_warnings]
    lines += ["", "---", "_Merge gate — see `.github/agent-policy.yml` to change these rules._"]
    return "\n".join(lines)


# --- GitHub adapter ----------------------------------------------------------

def read_ci_state(repo, sha: str) -> tuple:
    try:
        commit = repo.get_commit(sha)
        runs = list(commit.get_check_runs())
        state = commit.get_combined_status().state
    except Exception as exc:  # noqa: BLE001
        return "unknown", f"could not read CI status ({exc})"

    failed = [r.name for r in runs if r.conclusion in ("failure", "timed_out", "cancelled")]
    pending = [r.name for r in runs if r.status != "completed"]
    if failed:
        return "failing", ", ".join(failed[:5])
    if pending:
        return "pending", ", ".join(pending[:5])
    if state == "failure":
        return "failing", "combined commit status is failure"
    if not runs and state == "pending":
        return "none", "no checks reported for this commit"
    return "passing", "all checks passing"


def facts_from_github(repo, pr) -> PullRequestFacts:
    ci_state, ci_detail = read_ci_state(repo, pr.head.sha)
    return PullRequestFacts(
        number=pr.number,
        title=pr.title or "",
        body=pr.body or "",
        actor=(pr.user.login if pr.user else ""),
        branch=(pr.head.ref if pr.head else ""),
        draft=bool(pr.draft),
        files=[ChangedFile(f.filename, f.patch, f.additions, f.deletions)
               for f in pr.get_files()],
        ci_state=ci_state,
        ci_detail=ci_detail,
    )


def write_outputs(d: Decision, body: str) -> None:
    fields = {
        "verdict": d.verdict,
        "auto_merge": str(d.auto_merge).lower(),
        "is_agent": str(d.is_agent).lower(),
        "trusted": str(d.trusted).lower(),
        "summary": d.summary,
        "body": body,
    }
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in fields.items():
                delim = f"EOF_{key}_{os.urandom(8).hex()}"
                fh.write(f"{key}<<{delim}\n{value}\n{delim}\n")
    print(f"verdict={d.verdict} auto_merge={d.auto_merge} agent={d.is_agent}")
    print(d.summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide whether a PR may auto-merge.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--root", default=".", help="repo root, for policy lookup")
    args = parser.parse_args()

    try:
        from github import Auth, Github

        pol = policy_mod.load_policy(args.root)
        trusted: frozenset = frozenset()
        if pol.trust_enabled:
            import outcomes

            ledger_path = Path(args.root) / pol.trust.get(
                "ledger", ".github/agent-trust.json")
            trusted = frozenset(outcomes.trusted_identities(
                outcomes.load_ledger(ledger_path)))

        gh_repo = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"])).get_repo(args.repo)
        pr = gh_repo.get_pull(args.pr_number)
        facts = facts_from_github(gh_repo, pr)
        decision = evaluate(pol, facts, trusted)
        body = render(decision, facts)
    except Exception as exc:  # noqa: BLE001 - fail closed
        decision = Decision(
            verdict="COMMENT", auto_merge=False,
            summary=f"The merge gate could not complete ({exc}). A human must review this.",
            blockers=[f"gate error: {exc}"],
        )
        body = f"**Merge gate: error**\n\n{decision.summary}"

    write_outputs(decision, body)
    # Always exit 0: the workflow reads the verdict from outputs, and a
    # non-zero exit would skip the step that posts the review.
    return 0


if __name__ == "__main__":
    sys.exit(main())
