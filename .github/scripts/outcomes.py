#!/usr/bin/env python3
"""
Outcome tracking: did merged changes actually survive?

Every other signal in this repository is a prediction made before merge. This
one is the only measurement made after, and it is the only thing that can tell
you whether the predictions were any good.

For each merged pull request it asks two questions:

  Was it reverted?          A revert is the clearest admission that a change
                            should not have merged.
  Did it break the branch?  The default branch going red shortly after a merge,
                            having been green before it, is the next clearest.

Those answers aggregate into a survival rate per author identity, which is what
lets policy grant autonomy to agents that have earned it instead of to agents
whose vendor markets well.

Small samples are the trap here. An agent with one clean merge is not 100%
reliable, so scores use the lower bound of a Wilson interval: confidence has to
be earned with volume, not asserted from a single success.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import policy as policy_mod  # noqa: E402

# "Revert "original subject"" is what both GitHub and `git revert` produce.
REVERT_SUBJECT = re.compile(r'^\s*Revert\s+"(?P<subject>.+)"', re.IGNORECASE)
# GitHub's revert PRs also reference the original number.
REVERT_REFERENCE = re.compile(r"(?i)\brevert(?:s|ing)?\b[^\n]{0,40}#(?P<number>\d+)")


@dataclass
class MergedChange:
    number: int
    title: str
    author: str
    branch: str = ""
    merged_at: str = ""
    merge_sha: str = ""
    paths: list = field(default_factory=list)


@dataclass
class RevertEvent:
    """A commit or PR that undoes an earlier change."""
    subject: str = ""
    references: int | None = None
    at: str = ""


@dataclass
class BranchBreak:
    """The default branch failing CI at a commit."""
    sha: str
    at: str = ""


@dataclass
class Outcome:
    number: int
    identity: str
    is_agent: bool
    survived: bool
    reverted: bool = False
    broke_branch: bool = False
    reason: str = ""


@dataclass
class TrustScore:
    identity: str
    is_agent: bool
    merges: int = 0
    reverts: int = 0
    breaks: int = 0

    @property
    def failures(self) -> int:
        return self.reverts + self.breaks

    @property
    def survivals(self) -> int:
        return max(self.merges - self.failures, 0)

    @property
    def raw_rate(self) -> float:
        return self.survivals / self.merges if self.merges else 0.0

    @property
    def confidence(self) -> float:
        """Wilson score lower bound at ~95%.

        This is the number policy should act on. It answers "what survival rate
        can I be confident this identity is at least achieving", so one lucky
        merge cannot buy autonomy — the bound only approaches the raw rate as
        the sample grows.
        """
        n = self.merges
        if n == 0:
            return 0.0
        z = 1.96
        p = self.raw_rate
        denominator = 1 + z * z / n
        centre = p + z * z / (2 * n)
        margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
        return max(0.0, (centre - margin) / denominator)

    def verdict(self, thresholds: dict) -> str:
        if self.merges < int(thresholds.get("min_sample", 20)):
            return "insufficient-data"
        if self.confidence >= float(thresholds.get("trusted", 0.95)):
            return "trusted"
        if self.confidence >= float(thresholds.get("watch", 0.80)):
            return "watch"
        return "untrusted"


# --- Pure analysis -----------------------------------------------------------

def _normalise(subject: str) -> str:
    """Strip a trailing '(#123)' so a squash-merge subject matches its revert."""
    return re.sub(r"\s*\(#\d+\)\s*$", "", subject or "").strip().lower()


def detect_reverts(changes, reverts) -> dict:
    """Map PR number -> RevertEvent for every change that was undone.

    Matches on an explicit `#number` reference first, since that is
    unambiguous, and falls back to subject matching for hand-written reverts
    that only quote the original commit message.
    """
    by_number = {c.number: c for c in changes}
    by_subject = {_normalise(c.title): c for c in changes}
    found: dict = {}

    for event in reverts:
        if event.references and event.references in by_number:
            found.setdefault(event.references, event)
            continue
        match = REVERT_SUBJECT.match(event.subject or "")
        if not match:
            continue
        change = by_subject.get(_normalise(match.group("subject")))
        if change:
            found.setdefault(change.number, event)
    return found


def detect_branch_breaks(changes, breaks) -> dict:
    """Map PR number -> BranchBreak where the merge commit itself went red.

    Deliberately narrow: only the merge commit's own result counts. Blaming a
    merge for a later failure would attribute flaky infrastructure and
    unrelated commits to whoever merged most recently.
    """
    by_sha = {c.merge_sha: c for c in changes if c.merge_sha}
    found: dict = {}
    for event in breaks:
        change = by_sha.get(event.sha)
        if change:
            found.setdefault(change.number, event)
    return found


def build_outcomes(pol, changes, reverts, breaks) -> list:
    reverted = detect_reverts(changes, reverts)
    broken = detect_branch_breaks(changes, breaks)
    outcomes = []
    for change in changes:
        is_agent, _ = policy_mod.looks_like_agent(
            pol, change.author, change.branch, change.title)
        was_reverted = change.number in reverted
        did_break = change.number in broken
        reasons = []
        if was_reverted:
            reasons.append("reverted")
        if did_break:
            reasons.append("broke the default branch")
        outcomes.append(Outcome(
            number=change.number,
            identity=change.author or "unknown",
            is_agent=is_agent,
            survived=not (was_reverted or did_break),
            reverted=was_reverted,
            broke_branch=did_break,
            reason=", ".join(reasons) or "survived",
        ))
    return outcomes


def score(outcomes) -> dict:
    """Aggregate outcomes into a TrustScore per author identity."""
    scores: dict = {}
    for o in outcomes:
        s = scores.setdefault(o.identity, TrustScore(o.identity, o.is_agent))
        s.merges += 1
        if o.reverted:
            s.reverts += 1
        if o.broke_branch:
            s.breaks += 1
    return scores


def render_scoreboard(scores: dict, thresholds: dict) -> str:
    """Markdown table, agents first, worst confidence first within each group."""
    if not scores:
        return "No merged pull requests found in the window.\n"

    def sort_key(s):
        return (not s.is_agent, s.confidence, -s.merges)

    lines = [
        "| author | kind | merges | reverts | breaks | survival | confidence | verdict |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in sorted(scores.values(), key=sort_key):
        lines.append(
            f"| `{s.identity}` | {'agent' if s.is_agent else 'human'} | {s.merges} | "
            f"{s.reverts} | {s.breaks} | {s.raw_rate:.0%} | {s.confidence:.0%} | "
            f"{s.verdict(thresholds)} |")
    lines += [
        "",
        "`confidence` is the lower bound of a 95% Wilson interval on the survival "
        "rate. It is deliberately pessimistic on small samples: an identity needs "
        f"at least {thresholds.get('min_sample', 20)} merges before it can be rated "
        "at all, so autonomy is earned with volume rather than granted on a lucky "
        "first result.",
    ]
    return "\n".join(lines)


def load_ledger(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Could not read {path}: {exc}")
        return {}


def save_ledger(path: Path, scores: dict, thresholds: dict) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "thresholds": thresholds,
        "identities": {
            name: {**asdict(s), "survival_rate": round(s.raw_rate, 4),
                   "confidence": round(s.confidence, 4),
                   "verdict": s.verdict(thresholds)}
            for name, s in scores.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def trusted_identities(ledger: dict) -> set:
    return {name for name, entry in (ledger.get("identities") or {}).items()
            if entry.get("verdict") == "trusted"}


# --- GitHub adapter ----------------------------------------------------------

def collect_from_github(repo, days: int):
    """Gather merged PRs, revert events, and branch breaks from the API."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    changes, reverts, breaks = [], [], []

    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if not pr.merged_at:
            continue
        merged_at = pr.merged_at.replace(tzinfo=timezone.utc)
        if merged_at < since:
            break
        changes.append(MergedChange(
            number=pr.number,
            title=pr.title or "",
            author=(pr.user.login if pr.user else "unknown"),
            branch=(pr.head.ref if pr.head else ""),
            merged_at=merged_at.isoformat(),
            merge_sha=pr.merge_commit_sha or "",
        ))
        body = pr.body or ""
        reference = REVERT_REFERENCE.search(f"{pr.title}\n{body}")
        if REVERT_SUBJECT.match(pr.title or "") or reference:
            reverts.append(RevertEvent(
                subject=pr.title or "",
                references=int(reference.group("number")) if reference else None,
                at=merged_at.isoformat(),
            ))

    default_branch = repo.default_branch
    for commit in repo.get_commits(sha=default_branch, since=since):
        message = commit.commit.message.splitlines()[0] if commit.commit.message else ""
        reference = REVERT_REFERENCE.search(commit.commit.message or "")
        if REVERT_SUBJECT.match(message) or reference:
            reverts.append(RevertEvent(
                subject=message,
                references=int(reference.group("number")) if reference else None,
            ))
        try:
            if commit.get_combined_status().state == "failure":
                breaks.append(BranchBreak(sha=commit.sha))
        except Exception:  # noqa: BLE001 - a missing status is not a failure
            pass

    return changes, reverts, breaks


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure whether merged changes survived.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--days", type=int, default=90, help="window to analyse")
    parser.add_argument("--root", default=".", help="repo root, for policy lookup")
    parser.add_argument("--ledger", default=None,
                        help="ledger path; defaults to the policy's trust.ledger")
    parser.add_argument("--write", action="store_true", help="update the ledger file")
    args = parser.parse_args()

    pol = policy_mod.load_policy(args.root)
    thresholds = pol.trust or {"min_sample": 20, "trusted": 0.95, "watch": 0.80}

    if not args.repo or not os.environ.get("GITHUB_TOKEN"):
        print("::error::--repo and $GITHUB_TOKEN are required.")
        return 1

    from github import Github

    repo = Github(os.environ["GITHUB_TOKEN"]).get_repo(args.repo)
    changes, reverts, breaks = collect_from_github(repo, args.days)
    print(f"{len(changes)} merged PRs, {len(reverts)} revert events, "
          f"{len(breaks)} failing commits in the last {args.days} days.")

    outcomes = build_outcomes(pol, changes, reverts, breaks)
    scores = score(outcomes)
    board = render_scoreboard(scores, thresholds)
    print("\n" + board)

    if args.write:
        ledger = args.ledger or pol.trust.get("ledger", ".github/agent-trust.json")
        save_ledger(Path(args.root) / ledger, scores, thresholds)
        print(f"\nWrote {ledger}")

    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## Agent trust — last {args.days} days\n\n{board}\n")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as fh:
            delim = f"EOF_{os.urandom(8).hex()}"
            fh.write(f"scoreboard<<{delim}\n{board}\n{delim}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
