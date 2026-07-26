"""
Policy loading and evaluation.

Policy lives in `.github/agent-policy.yml`, not in Python constants. Editing a
YAML file is reviewable in a pull request; editing a constant inside the tool
that enforces it is not, and it means every consumer carries a fork.

The shipped defaults are deliberately strict. Loosening them should be a commit
someone signs off on.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

POLICY_FILENAME = ".github/agent-policy.yml"

DEFAULT_POLICY = {
    "version": 1,
    # How to tell an agent-authored pull request from a human one. Agent PRs
    # get the stricter profile because nobody watched them being written.
    "provenance": {
        "actors": [
            "copilot-swe-agent[bot]", "copilot[bot]", "github-actions[bot]",
            "claude[bot]", "devin-ai-integration[bot]", "cursoragent",
            "sweep-ai[bot]", "codegen-sh[bot]",
        ],
        "branch_prefixes": [
            "copilot/", "claude/", "agent/", "devin/", "sweep/", "codegen/",
        ],
        "title_markers": ["[agent]", "🤖"],
    },
    # Paths that always require a human, whoever wrote the change.
    "protected_paths": [
        ".github/**", "**/.github/**",
        "**/Dockerfile*", "**/docker-compose*.y*ml", "**/action.y*ml",
        "**/*.tf", "**/*.tfvars", "**/k8s/**", "**/helm/**", "**/charts/**",
        "**/requirements*.txt", "**/package.json", "**/package-lock.json",
        "**/pnpm-lock.yaml", "**/yarn.lock", "**/Gemfile*", "**/go.mod",
        "**/go.sum", "**/Cargo.toml", "**/Cargo.lock", "**/pyproject.toml",
        "**/*auth*", "**/*secret*", "**/*credential*", "**/security/**",
        "**/.env*", "**/Makefile", "**/*.sh", "**/migrations/**",
    ],
    "profiles": {
        "agent": {
            "auto_merge_paths": ["**/*.md", "**/*.markdown", "**/*.txt",
                                 "**/*.rst", "docs/**"],
            "max_files": 5,
            "max_lines": 150,
            "require_ci": True,
            "require_linked_issue": False,
        },
        "human": {
            "auto_merge_paths": [],   # humans merge their own work
            "max_files": 0,
            "max_lines": 0,
            "require_ci": True,
            "require_linked_issue": False,
        },
    },
    # Earned autonomy. An identity rated `trusted` by outcomes.py may merge the
    # additional paths listed here. Disabled by default: turning it on is a
    # decision to let measured history widen what a machine can merge.
    "trust": {
        "enabled": False,
        "ledger": ".github/agent-trust.json",
        "min_sample": 20,      # merges required before any rating is given
        "trusted": 0.95,       # Wilson lower bound needed to be 'trusted'
        "watch": 0.80,         # below this an identity is 'untrusted'
        "trusted_auto_merge_paths": [],
    },
    # Matched against added and removed diff lines. `severity: block` produces
    # REQUEST_CHANGES; `warn` is reported but does not change the verdict.
    "diff_rules": [
        {"id": "eval", "pattern": r"\beval\s*\(", "severity": "block",
         "message": "uses eval()"},
        {"id": "exec", "pattern": r"\bexec\s*\(", "severity": "block",
         "message": "uses exec()"},
        {"id": "shell-true",
         "pattern": r"subprocess\.\w+\([^)]*shell\s*=\s*True",
         "severity": "block", "message": "shell=True subprocess call"},
        {"id": "os-system", "pattern": r"\bos\.system\s*\(", "severity": "block",
         "message": "uses os.system()"},
        {"id": "curl-pipe-sh", "pattern": r"curl[^\n|]*\|\s*(ba)?sh",
         "severity": "block", "message": "pipes a download into a shell"},
        {"id": "hardcoded-secret",
         "pattern": r"(?i)\b(api[_-]?key|secret|password|token|private[_-]?key)\b\s*[=:]\s*['\"][^'\"]{8,}",
         "severity": "block", "message": "looks like a hardcoded credential"},
        {"id": "tls-off-py", "pattern": r"(?i)verify\s*=\s*False",
         "severity": "block", "message": "disables TLS verification"},
        {"id": "tls-off-node", "pattern": r"(?i)rejectUnauthorized\s*:\s*false",
         "severity": "block", "message": "disables TLS verification"},
        {"id": "disable-control",
         "pattern": r"(?i)\b(disable|bypass|skip|remove)\w*[_\s-]*(auth|security|validation|verification|check)",
         "severity": "block", "message": "disables a security control"},
        {"id": "no-verify", "pattern": r"(?i)--no-verify\b", "severity": "block",
         "message": "bypasses git hooks"},
        {"id": "write-all", "pattern": r"(?i)permissions:\s*write-all",
         "severity": "block", "message": "grants write-all permissions"},
        {"id": "id-token",
         "pattern": r"(?i)id-token:\s*write", "severity": "block",
         "message": "requests an OIDC token — combined with contents: write this is the documented exfiltration path"},
        {"id": "chmod-777", "pattern": r"\bchmod\s+(-R\s+)?777\b",
         "severity": "block", "message": "world-writable permissions"},
        {"id": "drop-table", "pattern": r"(?i)\bDROP\s+(TABLE|DATABASE)\b",
         "severity": "block", "message": "destructive SQL"},
        {"id": "rm-rf-root", "pattern": r"(?i)\brm\s+-rf\s+/",
         "severity": "block", "message": "recursive delete from root"},
        {"id": "debug-flag", "pattern": r"(?i)\bDEBUG\s*=\s*True",
         "severity": "warn", "message": "enables debug mode"},
        {"id": "todo-added", "pattern": r"^\+.*\b(TODO|FIXME)\b",
         "severity": "warn", "message": "adds a TODO/FIXME"},
    ],
}


@dataclass
class Profile:
    auto_merge_paths: list = field(default_factory=list)
    max_files: int = 0
    max_lines: int = 0
    require_ci: bool = True
    require_linked_issue: bool = False


@dataclass
class DiffRule:
    id: str
    pattern: str
    severity: str
    message: str
    _compiled: object = None

    def matches(self, line: str) -> bool:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern)
        return bool(self._compiled.search(line))


@dataclass
class Policy:
    protected_paths: list = field(default_factory=list)
    profiles: dict = field(default_factory=dict)
    diff_rules: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    trust: dict = field(default_factory=dict)
    source: str = "built-in defaults"
    warnings: list = field(default_factory=list)

    def profile_for(self, is_agent: bool) -> Profile:
        return self.profiles["agent" if is_agent else "human"]

    @property
    def trust_enabled(self) -> bool:
        return bool(self.trust.get("enabled"))

    def is_protected(self, path: str) -> bool:
        return match_any(path, self.protected_paths)


def match_any(path: str, globs) -> bool:
    """Glob match that also tries a leading slash, so '**/x' matches 'x'."""
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch("/" + path, g)
               for g in globs)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_policy(repo_root: Path | str = ".") -> Policy:
    """Load policy, falling back to strict defaults on any problem.

    A broken policy file must never silently relax enforcement, so every
    failure path keeps the defaults and records a warning that the gate
    surfaces in its review comment.
    """
    root = Path(repo_root)
    raw = dict(DEFAULT_POLICY)
    source = "built-in defaults"
    warnings: list = []

    path = root / POLICY_FILENAME
    if path.is_file():
        try:
            import yaml
            user = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(user, dict):
                warnings.append(f"{POLICY_FILENAME} is not a mapping; using defaults.")
            elif user.get("version") not in (None, 1):
                warnings.append(
                    f"{POLICY_FILENAME} declares version {user.get('version')}, "
                    f"but this tool understands version 1; using defaults.")
            else:
                raw = _deep_merge(raw, user)
                source = POLICY_FILENAME
        except ImportError:
            warnings.append("pyyaml is not installed; using built-in defaults.")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"could not read {POLICY_FILENAME} ({exc}); using defaults.")

    profiles = {}
    for name in ("agent", "human"):
        spec = raw.get("profiles", {}).get(name, {})
        profiles[name] = Profile(
            auto_merge_paths=list(spec.get("auto_merge_paths", [])),
            max_files=int(spec.get("max_files", 0)),
            max_lines=int(spec.get("max_lines", 0)),
            require_ci=bool(spec.get("require_ci", True)),
            require_linked_issue=bool(spec.get("require_linked_issue", False)),
        )

    rules = []
    for spec in raw.get("diff_rules", []):
        try:
            re.compile(spec["pattern"])
        except (re.error, KeyError, TypeError) as exc:
            warnings.append(f"ignoring invalid diff rule {spec!r}: {exc}")
            continue
        rules.append(DiffRule(
            id=str(spec.get("id", "custom")),
            pattern=spec["pattern"],
            severity=str(spec.get("severity", "block")),
            message=str(spec.get("message", "matched a custom rule")),
        ))

    return Policy(
        protected_paths=list(raw.get("protected_paths", [])),
        profiles=profiles,
        diff_rules=rules,
        provenance=raw.get("provenance", {}),
        trust=dict(raw.get("trust", {})),
        source=source,
        warnings=warnings,
    )


def looks_like_agent(policy: Policy, actor: str, branch: str, title: str) -> tuple:
    """(is_agent, reason). Unknown authorship is treated as agent-authored.

    Getting this wrong in the strict direction costs a human review. Getting it
    wrong in the permissive direction merges unreviewed machine output.
    """
    prov = policy.provenance
    actor_l, branch_l, title_l = (actor or "").lower(), (branch or "").lower(), (title or "").lower()

    for known in prov.get("actors", []):
        if actor_l == known.lower():
            return True, f"author `{actor}` is a known agent account"
    if actor_l.endswith("[bot]"):
        return True, f"author `{actor}` is a bot account"
    for prefix in prov.get("branch_prefixes", []):
        if branch_l.startswith(prefix.lower()):
            return True, f"branch `{branch}` uses the agent prefix `{prefix}`"
    for marker in prov.get("title_markers", []):
        if marker.lower() in title_l:
            return True, f"title contains the agent marker `{marker}`"
    return False, f"author `{actor}` looks human"
