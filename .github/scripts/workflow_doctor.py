#!/usr/bin/env python3
"""
Workflow Doctor - diagnoses failed GitHub Actions runs.

This tool reads the real log text of a failed run, matches it against known
failure signatures, and reports a diagnosis with concrete remediation steps.

It deliberately does NOT edit workflow files. The previous version rewrote them
with `yaml.safe_load` followed by `yaml.dump`, which silently converted the
`on:` trigger key to `true:` (YAML 1.1 treats `on` as a boolean) and stripped
every comment. That "repair" left the workflow permanently un-runnable. A
diagnosis a human can act on is worth more than an edit that destroys the file.
"""

import argparse
import io
import os
import re
import sys
import zipfile

# Signature -> (label, whether a human must change repo settings, guidance).
FAILURE_SIGNATURES = [
    (
        r"Resource not accessible by integration|"
        r"403.*(?:permission|forbidden)|"
        r"x-accepted-github-permissions",
        "permissions",
        "The workflow's GITHUB_TOKEN lacks a scope it needs.",
        [
            "Add the missing scope to the workflow's `permissions:` block.",
            "Grant only what the job needs (for example `issues: write`).",
            "Check Settings > Actions > General > Workflow permissions is not read-only.",
            "Do not use `permissions: write-all`.",
        ],
    ),
    (
        r"ModuleNotFoundError|No module named|cannot import name|"
        r"npm ERR!.*(?:404|ENOENT)|Could not find a version that satisfies",
        "dependency",
        "A dependency the job imports is not installed in the runner.",
        [
            "Confirm the package is listed in requirements.txt / package.json.",
            "Confirm the workflow installs it before use.",
            "Pin the version so the runner and local environments agree.",
        ],
    ),
    (
        r"Invalid workflow file|yaml.*(?:syntax|parse) error|"
        r"mapping values are not allowed|did not find expected key",
        "syntax",
        "The workflow YAML is invalid, so the run never started properly.",
        [
            "Validate the file with `actionlint` or a YAML linter.",
            "Check indentation and quoting around `${{ }}` expressions.",
            "If a tool rewrote this file, check whether `on:` became `true:`.",
        ],
    ),
    (
        r"(?:Secret|secrets\.\w+).*not found|"
        r"Input required and not supplied|"
        r"Bad credentials|401 Unauthorized",
        "missing_secret",
        "A required secret or credential is missing or invalid.",
        [
            "Add the secret under Settings > Secrets and variables > Actions.",
            "Confirm the name matches exactly, including case.",
            "Secrets are not exposed to workflows triggered from forks.",
        ],
    ),
    (
        r"exceeded the maximum execution time|"
        r"The operation was canceled|The job running on runner .* has exceeded",
        "timeout",
        "The job ran past its time limit and was cancelled.",
        [
            "Set an explicit `timeout-minutes:` on the job.",
            "Cache dependencies to cut setup time.",
            "Split long jobs so a failure surfaces sooner.",
        ],
    ),
    (
        r"no space left on device|ENOSPC",
        "disk_space",
        "The runner ran out of disk space.",
        [
            "Remove build artifacts and caches before the failing step.",
            "Use `docker system prune -af` on container-heavy jobs.",
        ],
    ),
    (
        r"rate limit exceeded|API rate limit|429 Too Many Requests",
        "rate_limit",
        "A GitHub or third-party API rate limit was hit.",
        [
            "Batch API calls or add backoff between them.",
            "Reduce how often the workflow runs on a schedule.",
        ],
    ),
]


def fetch_logs(repo, run_id: int) -> str:
    """Download and extract the run's logs. Returns '' if unavailable."""
    try:
        run = repo.get_workflow_run(run_id)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Could not load run {run_id}: {exc}")
        return ""

    # PyGithub exposes the authenticated requester; reuse it so the token and
    # any GitHub Enterprise base URL are handled for us.
    try:
        _, _, raw = repo._requester.requestBlob("GET", run.logs_url)  # noqa: SLF001
        data = raw.read() if hasattr(raw, "read") else raw
    except Exception:  # noqa: BLE001 - fall back to a plain authenticated GET
        try:
            import requests

            token = os.environ.get("GITHUB_TOKEN", "")
            resp = requests.get(
                run.logs_url,
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/vnd.github+json"},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.content
        except Exception as exc:  # noqa: BLE001
            print(f"::warning::Could not download logs: {exc}")
            return ""

    if isinstance(data, str):
        return data
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            parts = []
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                with archive.open(name) as fh:
                    parts.append(f"===== {name} =====\n"
                                 + fh.read().decode("utf-8", errors="replace"))
            return "\n".join(parts)
    except zipfile.BadZipFile:
        return data.decode("utf-8", errors="replace")


def failed_step_names(repo, run_id: int):
    names = []
    try:
        run = repo.get_workflow_run(run_id)
        for job in run.jobs():
            if job.conclusion != "failure":
                continue
            for step in job.steps:
                if step.conclusion == "failure":
                    names.append(f"{job.name} / {step.name}")
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Could not enumerate jobs: {exc}")
    return names


def extract_excerpt(logs: str, pattern: str, context: int = 3) -> str:
    lines = logs.splitlines()
    for i, line in enumerate(lines):
        if re.search(pattern, line, re.IGNORECASE):
            lo, hi = max(0, i - context), min(len(lines), i + context + 1)
            return "\n".join(lines[lo:hi])[:1200]
    return ""


def diagnose(logs: str, steps):
    """Return (issue_type, explanation, recommendations, excerpt)."""
    if not logs:
        return (
            "logs_unavailable",
            "The run's logs could not be downloaded, so no automated diagnosis "
            "was possible. Logs expire, and the token may lack `actions: read`.",
            ["Open the run in the Actions tab and read the failing step directly.",
             "Confirm the workflow grants `actions: read`.",
             "Re-run the job to regenerate logs if they have expired."],
            "Failed steps: " + (", ".join(steps) if steps else "unknown"),
        )

    for pattern, label, explanation, recommendations in FAILURE_SIGNATURES:
        if re.search(pattern, logs, re.IGNORECASE):
            return label, explanation, recommendations, extract_excerpt(logs, pattern)

    # No signature matched. Surface the most useful raw evidence instead of
    # inventing a diagnosis.
    excerpt = extract_excerpt(logs, r"^\s*(Error|error|FAILED|fatal|Traceback)") or \
        "\n".join(logs.splitlines()[-40:])[:1200]
    return (
        "unknown",
        "The failure did not match any known signature. The log excerpt below is "
        "the most likely relevant section.",
        ["Read the excerpt and the full run log in the Actions tab.",
         "If this failure recurs, add a signature for it in workflow_doctor.py."],
        excerpt,
    )


def build_report(run_id, workflow_name, issue_type, explanation, recommendations,
                 excerpt, steps, run_url):
    steps_text = "\n".join(f"- `{s}`" for s in steps) or "- (none reported)"
    recs = "\n".join(f"{i}. {r}" for i, r in enumerate(recommendations, 1))
    return (
        f"## Workflow failure: {workflow_name}\n\n"
        f"**Diagnosis:** {issue_type}\n\n"
        f"{explanation}\n\n"
        f"### Failed steps\n{steps_text}\n\n"
        f"### Suggested fixes\n{recs}\n\n"
        f"### Log excerpt\n```\n{excerpt or '(no excerpt available)'}\n```\n\n"
        f"[View the full run]({run_url})\n\n"
        f"---\n"
        f"_Filed by Workflow Doctor. This tool diagnoses only; it does not edit "
        f"workflow files._\n"
    )


def write_outputs(**fields) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in fields.items():
                delimiter = f"EOF_{key}_{os.urandom(8).hex()}"
                fh.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
    for key, value in fields.items():
        preview = str(value).splitlines()[0][:120] if value else ""
        print(f"{key}: {preview}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose a failed GitHub Actions run.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--workflow-name", default="unknown")
    args = parser.parse_args()

    try:
        from github import Github

        repo = Github(os.environ["GITHUB_TOKEN"]).get_repo(args.repo)
    except Exception as exc:  # noqa: BLE001
        print(f"::error::Could not connect to GitHub: {exc}")
        write_outputs(issue_type="error", report=f"Workflow Doctor failed to start: {exc}")
        return 0

    print(f"Diagnosing run {args.run_id} of '{args.workflow_name}'")
    logs = fetch_logs(repo, args.run_id)
    print(f"Retrieved {len(logs)} characters of log text.")
    steps = failed_step_names(repo, args.run_id)
    issue_type, explanation, recommendations, excerpt = diagnose(logs, steps)
    print(f"Diagnosis: {issue_type}")

    run_url = f"https://github.com/{args.repo}/actions/runs/{args.run_id}"
    report = build_report(args.run_id, args.workflow_name, issue_type, explanation,
                          recommendations, excerpt, steps, run_url)
    write_outputs(issue_type=issue_type, report=report,
                  title=f"Workflow failure: {args.workflow_name} ({issue_type})")
    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
