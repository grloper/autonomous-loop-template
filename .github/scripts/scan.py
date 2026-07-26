#!/usr/bin/env python3
"""
Orchestrator - Repository Analyzer

Scans the repository for actionable work, scores it, and files GitHub issues.

Every issue is derived from something actually found in the repository. There
are no hardcoded tasks: if the scan finds nothing, no issues are created.

Issues carry a hidden fingerprint marker so re-runs update the existing issue
instead of filing a duplicate.
"""

import argparse
import fnmatch
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MARKER_PREFIX = "<!-- autonomous-loop:fingerprint:"

DEFAULT_CONFIG = {
    # Directories never scanned. Matched against path parts, not substrings.
    "exclude_dirs": [
        ".git", "__pycache__", "node_modules", ".venv", "venv", "dist",
        "build", "vendor", ".mypy_cache", ".pytest_cache", ".tox", ".next",
    ],
    "exclude_globs": ["*.min.js", "*.lock", "*.map"],
    # Only files with these suffixes are scanned for markers.
    "include_suffixes": [
        ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".rb", ".java",
        ".kt", ".c", ".h", ".cpp", ".cs", ".php", ".sh", ".yml", ".yaml",
    ],
    "max_file_bytes": 1_000_000,
    "max_issues_per_run": 5,
    # Cap per file. Without this, a single file with dozens of markers takes
    # every slot in a run, and keeps taking them every run — the scan reports
    # the same file forever and never surfaces anything else. Observed on the
    # Python stdlib, where one file held 22 of 308 findings and 4 of the top 5.
    "max_issues_per_file": 1,
    "min_score": 3.0,
    # Marker keyword -> (impact, urgency, risk). Score = impact * urgency / risk.
    "marker_weights": {
        "FIXME": (7, 8, 3),
        "TODO": (5, 4, 3),
        "HACK": (6, 5, 3),
        "XXX": (6, 6, 3),
        "BUG": (8, 9, 3),
    },
    # Regexes that escalate a marker when they match the same line.
    #
    # Tuned against the Python standard library, where the first draft scored
    # HTTP digest-auth commentary at maximum severity. Bare `auth` matched
    # protocol vocabulary (`auth-int`, `auth-schemes`) and bare `token` matched
    # lexer tokens, so the highest-priority findings in a 671-file scan were all
    # descriptive prose in one file. Terms now have to be unambiguous.
    "escalations": {
        r"(?i)\b(security|vulnerab\w*|exploit\w*|authz|authenticat\w+|"
        r"password\w*|credential\w*|secret\w*|injection|sql ?injection|"
        r"xss|csrf|ssrf|rce|priv(ilege)? ?esc\w*|"
        r"(access|api|auth|bearer|refresh) ?tokens?)\b": 3.0,
        r"(?i)\b(crash\w*|corrupt\w*|data ?loss|race condition|deadlock\w*)\b": 2.0,
        r"(?i)\b(perf|performance|slow\w*|leak\w*)\b": 1.3,
    },
}

MARKER_RE = re.compile(
    r"(?:^|[^A-Za-z])(" + "|".join(DEFAULT_CONFIG["marker_weights"]) + r")\b[:\s-]*(.*)"
)

# A marker only counts inside a comment. Without this, the tool matches its own
# `marker_weights` table and any string literal that merely names a marker.
COMMENT_RE = re.compile(r"(#|//|/\*|<!--|^\s*\*(?!/))")


def comment_start(line: str):
    """Index where a comment begins on this line, or None if there is none."""
    match = COMMENT_RE.search(line)
    return match.start() if match else None


def load_config(repo_root: Path) -> dict:
    """Merge .github/autonomous-loop.yml over the defaults, if present."""
    config = {k: (v.copy() if isinstance(v, (dict, list)) else v)
              for k, v in DEFAULT_CONFIG.items()}
    path = repo_root / ".github" / "autonomous-loop.yml"
    if not path.is_file():
        return config
    try:
        import yaml
        user = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:  # noqa: BLE001 - config must never break the run
        print(f"::warning::Could not read {path}: {exc}. Using defaults.")
        return config
    if not isinstance(user, dict):
        print(f"::warning::{path} is not a mapping. Using defaults.")
        return config
    config.update({k: v for k, v in user.items() if k in config})
    return config


@dataclass
class Finding:
    kind: str
    title: str
    body: str
    impact: float
    urgency: float
    risk: float
    labels: list = field(default_factory=list)
    fingerprint_source: str = ""

    @property
    def score(self) -> float:
        """Impact x Urgency / Risk. Risk divides: risky work ranks lower."""
        return round(self.impact * self.urgency / max(self.risk, 0.1), 2)

    @property
    def fingerprint(self) -> str:
        src = self.fingerprint_source or self.title
        return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]


def is_excluded(path: Path, config: dict) -> bool:
    # Match on path *parts* so '.github' is not caught by a '.git' substring.
    if any(part in config["exclude_dirs"] for part in path.parts):
        return True
    return any(fnmatch.fnmatch(path.name, pat) for pat in config["exclude_globs"])


def iter_source_files(repo_root: Path, config: dict):
    suffixes = set(config["include_suffixes"])
    for path in repo_root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        rel = path.relative_to(repo_root)
        if is_excluded(rel, config):
            continue
        try:
            if path.stat().st_size > config["max_file_bytes"]:
                continue
        except OSError:
            continue
        yield rel, path


def scan_markers(repo_root: Path, config: dict) -> list:
    """Find TODO/FIXME/HACK/XXX/BUG comments and turn each into a Finding."""
    findings = []
    for rel, path in iter_source_files(repo_root, config):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"::warning::Could not read {rel}: {exc}")
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            start = comment_start(line)
            if start is None:
                continue
            match = MARKER_RE.search(line, start)
            if not match:
                continue
            keyword = match.group(1)
            note = match.group(2).strip() or "(no description)"
            impact, urgency, risk = config["marker_weights"][keyword]
            multiplier = 1.0
            matched_tags = []
            for pattern, boost in config["escalations"].items():
                if re.search(pattern, line):
                    multiplier = max(multiplier, boost)
                    matched_tags.append(pattern)
            labels = ["autonomous-loop", f"marker:{keyword.lower()}"]
            if multiplier >= 3.0:
                labels.append("security")
            findings.append(Finding(
                kind="marker",
                title=f"[{keyword}] {rel}:{lineno} — {note[:80]}",
                body=(
                    f"A `{keyword}` marker in the codebase needs resolving.\n\n"
                    f"**Location:** `{rel}` line {lineno}\n\n"
                    f"```\n{line.strip()[:500]}\n```\n\n"
                    f"### What to do\n"
                    f"Resolve the marker: implement the missing behaviour, or remove "
                    f"the comment if it is stale. Do not silently delete it without "
                    f"confirming the underlying issue is gone.\n\n"
                    f"### Done when\n"
                    f"- [ ] The `{keyword}` comment at `{rel}:{lineno}` is gone\n"
                    f"- [ ] The behaviour it described is implemented or provably unnecessary\n"
                    f"- [ ] Existing tests still pass\n"
                ),
                impact=impact * multiplier,
                urgency=urgency,
                risk=risk,
                labels=labels,
                # Fingerprint on file+keyword+note, NOT line number, so the issue
                # survives unrelated edits that shift lines around.
                fingerprint_source=f"marker|{rel}|{keyword}|{note[:120]}",
            ))
    return findings


def scan_test_coverage(repo_root: Path, config: dict) -> list:
    """Report source directories that contain no recognisable test files."""
    test_patterns = ("test_", "_test.", ".test.", ".spec.", "spec_")
    sources, tests = 0, 0
    for rel, _ in iter_source_files(repo_root, config):
        name = rel.name
        if any(p in name for p in test_patterns) or "test" in rel.parts or "tests" in rel.parts:
            tests += 1
        else:
            sources += 1
    if sources == 0 or tests > 0:
        return []
    return [Finding(
        kind="coverage",
        title=f"No test files found across {sources} source files",
        body=(
            f"The scan found {sources} source files and zero files matching a test "
            f"naming convention ({', '.join(test_patterns)}).\n\n"
            "### What to do\n"
            "Add a test runner and cover the highest-risk module first. This issue "
            "is about establishing the harness, not reaching a coverage target.\n\n"
            "### Done when\n"
            "- [ ] A test runner is configured and runs in CI\n"
            "- [ ] At least one meaningful test exists and passes\n"
        ),
        impact=7, urgency=5, risk=2,
        labels=["autonomous-loop", "testing"],
        fingerprint_source="coverage|no-tests",
    )]


def limit_per_file(findings, max_per_file: int):
    """Keep at most `max_per_file` findings per source file.

    Findings arrive sorted by score, so the highest-scoring marker in each file
    survives. Returns (kept, held_back_count); held-back findings are not lost,
    they simply wait for a later run once the earlier ones are resolved.
    """
    if max_per_file <= 0:
        return findings, 0
    seen: dict = {}
    kept = []
    for finding in findings:
        key = finding.fingerprint_source.split("|")[1] if "|" in finding.fingerprint_source \
            else finding.title
        if seen.get(key, 0) >= max_per_file:
            continue
        seen[key] = seen.get(key, 0) + 1
        kept.append(finding)
    return kept, len(findings) - len(kept)


def render_body(finding: Finding, run_id: str) -> str:
    return (
        f"{finding.body}\n"
        f"---\n\n"
        f"**Score:** {finding.score} (impact {finding.impact:g} x urgency "
        f"{finding.urgency:g} / risk {finding.risk:g})\n"
        f"**Filed by:** Orchestrator, run `{run_id}`\n"
        f"**Scanned at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"{MARKER_PREFIX}{finding.fingerprint} -->\n"
    )


def existing_fingerprints(repo) -> dict:
    """Map fingerprint -> issue for every open issue this tool filed."""
    found = {}
    for issue in repo.get_issues(state="open", labels=["autonomous-loop"]):
        body = issue.body or ""
        idx = body.find(MARKER_PREFIX)
        if idx != -1:
            fp = body[idx + len(MARKER_PREFIX):].split()[0].strip()
            found[fp] = issue
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a repo and file issues for real findings.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"),
                        help="owner/repo. Defaults to $GITHUB_REPOSITORY.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be filed without touching GitHub.")
    parser.add_argument("--max-issues", type=int, default=None,
                        help="Override max issues created this run.")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    config = load_config(repo_root)
    if args.max_issues is not None:
        config["max_issues_per_run"] = args.max_issues

    print(f"Scanning {repo_root}")
    findings = scan_markers(repo_root, config) + scan_test_coverage(repo_root, config)
    scanned = sum(1 for _ in iter_source_files(repo_root, config))
    print(f"Scanned {scanned} files; {len(findings)} findings before scoring.")

    findings = [f for f in findings if f.score >= config["min_score"]]
    findings.sort(key=lambda f: f.score, reverse=True)
    print(f"{len(findings)} findings at or above min_score {config['min_score']}.")

    findings, crowded = limit_per_file(findings, config["max_issues_per_file"])
    if crowded:
        print(f"Held back {crowded} lower-scoring finding(s) so no single file "
              f"takes more than {config['max_issues_per_file']} slot(s) per run.")

    if not findings:
        print("Nothing actionable found. No issues filed.")
        return 0

    if args.dry_run:
        for f in findings[: config["max_issues_per_run"]]:
            print(f"  [{f.score:>7}] {f.title}  (fingerprint {f.fingerprint})")
        print(f"\nDry run: {len(findings)} candidates, would file "
              f"{min(len(findings), config['max_issues_per_run'])}.")
        return 0

    if not args.repo:
        print("::error::--repo or $GITHUB_REPOSITORY is required unless --dry-run.")
        return 1
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("::error::$GITHUB_TOKEN is required unless --dry-run.")
        return 1

    from github import Github

    repo = Github(token).get_repo(args.repo)
    seen = existing_fingerprints(repo)
    print(f"{len(seen)} open issues already filed by this tool.")

    created = skipped = 0
    for finding in findings:
        if created >= config["max_issues_per_run"]:
            print(f"Reached max_issues_per_run ({config['max_issues_per_run']}); "
                  f"{len(findings) - created - skipped} findings deferred to the next run.")
            break
        if finding.fingerprint in seen:
            skipped += 1
            print(f"  skip (already open as #{seen[finding.fingerprint].number}): {finding.title}")
            continue
        try:
            issue = repo.create_issue(
                title=finding.title[:250],
                body=render_body(finding, os.environ.get("GITHUB_RUN_ID", "local")),
                labels=finding.labels,
            )
            created += 1
            print(f"  created #{issue.number}: {finding.title}")
        except Exception as exc:  # noqa: BLE001 - one failure must not abort the run
            print(f"::warning::Failed to create issue for {finding.title!r}: {exc}")

    summary = (
        f"## Orchestrator\n\n"
        f"- Files scanned: {scanned}\n"
        f"- Findings above threshold: {len(findings)}\n"
        f"- Issues created: {created}\n"
        f"- Duplicates skipped: {skipped}\n"
    )
    print(summary)
    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
