#!/usr/bin/env python3
"""
Auto-Reviewer - decides whether a pull request may merge without a human.

Design rules, in order of importance:

1. Fail closed. Any error, any uncertainty, any unrecognised input produces
   "a human must look at this". There is no code path where a failure results
   in a merge.
2. Read the diff, not the filename. A decision made from the file extension
   alone cannot see what the change actually does.
3. Auto-merge is opt-in and narrow. It requires every check to pass: safe
   paths, small size, clean diff content, and green CI.
"""

import argparse
import fnmatch
import os
import re
import sys
from dataclasses import dataclass, field

# Paths that always require a human, matched as glob patterns against the
# full path. Anything touching CI, dependencies, or infrastructure is here
# because those files change what runs, not just what ships.
CRITICAL_PATH_GLOBS = [
    ".github/**", "**/.github/**",
    "**/Dockerfile*", "**/docker-compose*.y*ml", "**/action.y*ml",
    "**/*.tf", "**/*.tfvars", "**/k8s/**", "**/helm/**", "**/charts/**",
    "**/requirements*.txt", "**/package.json", "**/package-lock.json",
    "**/pnpm-lock.yaml", "**/yarn.lock", "**/Gemfile*", "**/go.mod",
    "**/go.sum", "**/Cargo.toml", "**/Cargo.lock", "**/pyproject.toml",
    "**/*auth*", "**/*secret*", "**/*credential*", "**/security/**",
    "**/.env*", "**/Makefile", "**/*.sh",
]

# Only these may ever auto-merge. Documentation and plain text, nothing else.
# .yml is deliberately absent: a YAML file is usually configuration that
# changes behaviour, and telling CI config apart from data by extension alone
# is not something this tool can do reliably.
AUTO_MERGE_GLOBS = ["**/*.md", "**/*.markdown", "**/*.txt", "**/*.rst", "docs/**"]

# Substrings that, when they appear on an ADDED or REMOVED diff line, always
# require a human. These are matched against diff content, not the PR title.
DANGEROUS_DIFF_PATTERNS = [
    (r"\beval\s*\(", "uses eval()"),
    (r"\bexec\s*\(", "uses exec()"),
    (r"subprocess\.\w+\([^)]*shell\s*=\s*True", "shell=True subprocess call"),
    (r"\bos\.system\s*\(", "uses os.system()"),
    (r"curl[^\n|]*\|\s*(ba)?sh", "pipes a download into a shell"),
    (r"(?i)\b(api[_-]?key|secret|password|token|private[_-]?key)\b\s*[=:]\s*['\"][^'\"]{8,}",
     "looks like a hardcoded credential"),
    (r"(?i)verify\s*=\s*False", "disables TLS verification"),
    (r"(?i)rejectUnauthorized\s*:\s*false", "disables TLS verification"),
    (r"(?i)\b(disable|bypass|skip|remove)\w*[_\s-]*(auth|security|validation|verification|check)",
     "disables a security control"),
    (r"(?i)--no-verify\b", "bypasses git hooks"),
    (r"(?i)permissions:\s*write-all", "grants write-all permissions"),
    (r"\bchmod\s+(-R\s+)?777\b", "world-writable permissions"),
    (r"(?i)\bDROP\s+(TABLE|DATABASE)\b", "destructive SQL"),
    (r"(?i)\brm\s+-rf\s+/", "recursive delete from root"),
]

MAX_AUTO_MERGE_FILES = 5
MAX_AUTO_MERGE_LINES = 150


@dataclass
class Review:
    verdict: str = "COMMENT"          # APPROVE | REQUEST_CHANGES | COMMENT
    auto_merge: bool = False
    summary: str = ""
    blockers: list = field(default_factory=list)   # prevent auto-merge
    concerns: list = field(default_factory=list)   # require changes
    critical_files: list = field(default_factory=list)


def matches_any(path: str, globs) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(f"/{path}", g) for g in globs)


def scan_diff(patch: str, filename: str):
    """Return dangerous patterns found on added/removed lines of a patch."""
    hits = []
    if not patch:
        # No patch means binary, too large, or unavailable. Never auto-merge
        # something whose contents we could not read.
        return [f"`{filename}`: diff unavailable (binary or too large) — cannot inspect"]
    for line in patch.splitlines():
        if not line or line[0] not in "+-" or line.startswith(("+++", "---")):
            continue
        for pattern, description in DANGEROUS_DIFF_PATTERNS:
            if re.search(pattern, line):
                hits.append(f"`{filename}`: {description} — `{line.strip()[:120]}`")
                break
    return hits


def ci_is_green(repo, pr):
    """(passing, detail). Unknown or pending counts as not passing."""
    try:
        commit = repo.get_commit(pr.head.sha)
        state = commit.get_combined_status().state  # success | pending | failure
        runs = list(commit.get_check_runs())
    except Exception as exc:  # noqa: BLE001 - unknown CI state must not merge
        return False, f"could not read CI status ({exc})"

    failed = [r.name for r in runs if r.conclusion in ("failure", "timed_out", "cancelled")]
    pending = [r.name for r in runs if r.status != "completed"]
    if failed:
        return False, f"failing checks: {', '.join(failed[:5])}"
    if pending:
        return False, f"checks still running: {', '.join(pending[:5])}"
    if state == "failure":
        return False, "combined commit status is failure"
    if not runs and state == "pending":
        # No checks configured at all. Treat as unknown, not as success.
        return False, "no CI checks reported for this commit"
    return True, "all checks passing"


def analyze(repo, pr) -> Review:
    review = Review()

    if pr.draft:
        review.summary = "Pull request is a draft. Skipping review."
        return review

    files = list(pr.get_files())
    if not files:
        review.blockers.append("PR reports no changed files")
        review.summary = "No changed files could be read. A human should check this."
        return review

    total_lines = sum((f.additions or 0) + (f.deletions or 0) for f in files)

    for f in files:
        if matches_any(f.filename, CRITICAL_PATH_GLOBS):
            review.critical_files.append(f.filename)
            review.blockers.append(f"`{f.filename}` is on the critical-path list")
        elif not matches_any(f.filename, AUTO_MERGE_GLOBS):
            review.blockers.append(f"`{f.filename}` is not on the auto-merge allowlist")
        review.concerns.extend(scan_diff(f.patch, f.filename))

    if len(files) > MAX_AUTO_MERGE_FILES:
        review.blockers.append(f"{len(files)} files changed (limit {MAX_AUTO_MERGE_FILES})")
    if total_lines > MAX_AUTO_MERGE_LINES:
        review.blockers.append(f"{total_lines} lines changed (limit {MAX_AUTO_MERGE_LINES})")

    ci_ok, ci_detail = ci_is_green(repo, pr)
    if not ci_ok:
        review.blockers.append(f"CI not green: {ci_detail}")

    if review.concerns:
        review.verdict = "REQUEST_CHANGES"
        review.auto_merge = False
        review.summary = (
            f"Found {len(review.concerns)} change(s) in the diff that need a human "
            f"decision. This PR will not be auto-merged."
        )
    elif review.blockers:
        review.verdict = "COMMENT"
        review.auto_merge = False
        review.summary = (
            f"No dangerous patterns found in the diff, but {len(review.blockers)} "
            f"condition(s) prevent auto-merge. Review and merge manually."
        )
    else:
        review.verdict = "APPROVE"
        review.auto_merge = True
        review.summary = (
            f"{len(files)} documentation file(s), {total_lines} lines, clean diff, "
            f"CI green. Approved for auto-merge."
        )
    return review


def write_outputs(review: Review) -> None:
    """Write to $GITHUB_OUTPUT using heredocs so newlines cannot break parsing."""
    fields = {
        "verdict": review.verdict,
        "auto_merge": str(review.auto_merge).lower(),
        "summary": review.summary,
        "blockers": "\n".join(f"- {b}" for b in review.blockers) or "None",
        "concerns": "\n".join(f"- {c}" for c in review.concerns) or "None",
        "critical_files": "\n".join(f"- `{f}`" for f in review.critical_files) or "None",
    }
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in fields.items():
                delimiter = f"EOF_{key}_{os.urandom(8).hex()}"
                fh.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
    for key, value in fields.items():
        print(f"{key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide whether a PR may auto-merge.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", required=True, type=int)
    args = parser.parse_args()

    review = Review()
    try:
        from github import Github

        token = os.environ["GITHUB_TOKEN"]
        repo = Github(token).get_repo(args.repo)
        pr = repo.get_pull(args.pr_number)
        print(f"Reviewing PR #{args.pr_number}: {pr.title}")
        review = analyze(repo, pr)
    except Exception as exc:  # noqa: BLE001 - fail closed, never fail open
        review = Review(
            verdict="COMMENT",
            auto_merge=False,
            summary=f"Review could not be completed ({exc}). A human must review this PR.",
            blockers=[f"reviewer error: {exc}"],
        )

    write_outputs(review)
    # Exit 0 even on internal error: the workflow reads the verdict from the
    # outputs. A non-zero exit would skip the "needs human review" comment and
    # leave the PR silently unreviewed.
    return 0


if __name__ == "__main__":
    sys.exit(main())
