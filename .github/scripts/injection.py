"""
Prompt-injection scanning for repository content.

An agent with a write token reads issue titles, pull request bodies, code
comments, and README text. Anything it reads, an attacker can write — filing a
public issue has been sufficient to redirect coding agents into leaking
credentials, and the pattern has assigned CVEs across several vendors.

This module scans that content for the shapes those attacks take. It is a
detector, not a sanitiser: it tells you which text is trying to give your agent
orders, so a human decides before the agent acts on it.

Precision matters more than recall here. A scanner that fires on every README
gets muted in a week, so each rule needs both an imperative aimed at a reader
and a payload worth caring about.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Text that tries to override an agent's existing instructions.
OVERRIDE_PATTERNS = [
    (r"(?i)\bignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
     "instructs a reader to ignore previous instructions"),
    (r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|rules?|guidelines?)",
     "instructs a reader to disregard its instructions"),
    (r"(?i)\b(you\s+are\s+now|from\s+now\s+on,?\s+you)\b.{0,40}\b(a|an|the)\b",
     "attempts to reassign the reader's role"),
    (r"(?i)<\s*/?\s*(system|system_prompt|instructions?)\s*>",
     "contains fake system-prompt delimiters"),
    (r"(?i)\bnew\s+(system\s+)?(instructions?|directive|task)\s*[::]",
     "declares new instructions"),
    (r"(?i)\b(developer|system|admin)\s+(mode|override|instruction)\b",
     "claims elevated instruction authority"),
]

# Text that names a secret or credential source an agent could read.
SECRET_ACCESS_PATTERNS = [
    (r"/proc/self/environ", "references /proc/self/environ, the documented credential-read path"),
    (r"(?i)ACTIONS_ID_TOKEN_REQUEST_(TOKEN|URL)", "references the Actions OIDC token variables"),
    (r"(?i)\bprint(env)?\b.{0,20}\b(env|environment|secrets?)\b", "asks a reader to print the environment"),
    (r"(?i)\b(cat|read|dump|show|reveal|output)\b.{0,30}\b(\.env|secrets?|credentials?|api[_-]?keys?|tokens?)\b",
     "asks a reader to read secrets"),
    (r"(?i)\$\{\{\s*secrets\.", "interpolates a workflow secret"),
    (r"(?i)\bprocess\.env\.[A-Z_]{4,}", "references a named environment variable"),
    (r"(?i)~/\.(ssh|aws|npmrc|git-credentials)", "references a credential file"),
]

# Text that describes sending data somewhere.
EXFILTRATION_PATTERNS = [
    (r"(?i)\b(post|send|upload|exfiltrate|transmit|report)\b.{0,40}\bto\b.{0,20}https?://",
     "asks a reader to send data to a URL"),
    (r"(?i)\b(curl|wget|fetch)\b[^\n]{0,80}(-d|--data|-X\s*POST)",
     "constructs an outbound POST"),
    (r"(?i)\b(webhook|pastebin|requestbin|ngrok|burpcollaborator|oastify)\b",
     "names a common exfiltration endpoint"),
    (r"(?i)\bbase64\b.{0,30}\b(encode|encoding)\b.{0,40}\b(send|post|url)\b",
     "encodes data for transport"),
]

# Text that would relax an agent's own guardrails.
SELF_ESCALATION_PATTERNS = [
    (r"(?i)chat\.tools\.autoApprove", "sets the editor flag that disables tool confirmation (CVE-2025-53773)"),
    (r"(?i)allowed_non_write_users\s*:\s*['\"]?\*", "grants agent triggering to every user"),
    (r"(?i)\b(auto[_-]?approve|yolo\s*mode|--dangerously-skip-permissions|--yes-always)\b",
     "requests unattended approval"),
    (r"(?i)\badd\b.{0,30}\bto\b.{0,20}\b(allowlist|allowed_tools|permissions)\b",
     "asks to widen an allowlist"),
]

CATEGORIES = [
    ("instruction-override", OVERRIDE_PATTERNS, "high"),
    ("secret-access", SECRET_ACCESS_PATTERNS, "critical"),
    ("exfiltration", EXFILTRATION_PATTERNS, "critical"),
    ("self-escalation", SELF_ESCALATION_PATTERNS, "critical"),
]

# Characters used to hide text from a human reviewer while an agent still
# reads it. Bidi overrides are the "Trojan Source" technique.
INVISIBLE_CHARS = {
    "​": "zero-width space",
    "‌": "zero-width non-joiner",
    "‍": "zero-width joiner",
    "⁠": "word joiner",
    "﻿": "zero-width no-break space",
    "‪": "bidi embedding", "‫": "bidi embedding",
    "‬": "bidi pop", "‭": "bidi override", "‮": "bidi override",
    "⁦": "bidi isolate", "⁧": "bidi isolate",
    "⁨": "bidi isolate", "⁩": "bidi isolate",
    "­": "soft hyphen",
}

# An imperative aimed at a reader. Required alongside a payload match for the
# override category, so prose that merely mentions secrets does not fire.
IMPERATIVE = re.compile(
    r"(?i)\b(you\s+(must|should|will|need\s+to)|please\s+\w+|do\s+not|don't|"
    r"ignore|disregard|instead\s+of|before\s+(you\s+)?(continue|proceed|responding)|"
    r"first,?\s+\w+|immediately)\b"
)

HIDDEN_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)

# An imperative alone is not enough to flag an HTML comment: "generated file,
# do not edit" is an imperative and is entirely benign. A concealed comment
# only counts when it also addresses a reader directly or names a payload.
DIRECT_ADDRESS = re.compile(r"(?i)\b(you|your|assistant|agent|model|copilot|claude)\b")


@dataclass
class Signal:
    category: str
    severity: str
    message: str
    excerpt: str
    location: str = ""

    def __str__(self) -> str:
        where = f"{self.location}: " if self.location else ""
        return f"[{self.severity}] {where}{self.message} — {self.excerpt!r}"


def _excerpt(text: str, index: int, width: int = 90) -> str:
    lo = max(0, index - width // 3)
    return text[lo:lo + width].replace("\n", " ").strip()


def find_invisible(text: str, location: str = "") -> list:
    signals = []
    seen = set()
    for char, name in INVISIBLE_CHARS.items():
        if char in text and name not in seen:
            seen.add(name)
            index = text.index(char)
            signals.append(Signal(
                "hidden-text", "high",
                f"contains {name} (U+{ord(char):04X}), which hides content from a human reviewer",
                _excerpt(text, index), location,
            ))
    return signals


def scan_text(text: str, location: str = "", require_imperative: bool = True) -> list:
    """Return injection signals found in a block of text."""
    if not text:
        return []

    signals: list = []
    normalized = unicodedata.normalize("NFKC", text)
    has_imperative = bool(IMPERATIVE.search(normalized))

    for category, patterns, severity in CATEGORIES:
        for pattern, message in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            # The override category is definitionally an instruction, so it
            # does not need a second imperative to corroborate it. The others
            # do, otherwise documentation that discusses secrets trips them.
            if (require_imperative and category != "instruction-override"
                    and not has_imperative):
                continue
            signals.append(Signal(category, severity, message,
                                  _excerpt(normalized, match.start()), location))

    signals.extend(find_invisible(text, location))

    # Instructions concealed inside an HTML comment are invisible in rendered
    # markdown but present in the raw text an agent reads.
    for comment in HIDDEN_HTML_COMMENT.findall(normalized):
        text_in = comment.strip()
        if len(text_in) <= 20 or not IMPERATIVE.search(text_in):
            continue
        payload = any(re.search(p, text_in)
                      for _, patterns, _ in CATEGORIES for p, _ in patterns)
        if not (DIRECT_ADDRESS.search(text_in) or payload):
            continue
        signals.append(Signal(
            "hidden-text", "high",
            "HTML comment contains instructions addressed to a reader, "
            "which render invisibly to a human",
            text_in[:90], location,
        ))

    return signals


def scan_pull_request(title: str, body: str, branch: str = "") -> list:
    """Scan the attacker-controlled fields of a pull request.

    The title is included deliberately: in the disclosed claude-code-action
    compromise, an issue title alone carried the payload, so a scanner that
    covers bodies but not titles is incomplete.
    """
    signals = []
    signals += scan_text(title, "PR title")
    signals += scan_text(body, "PR body")
    signals += scan_text(branch, "branch name")
    return signals


def scan_diff(patch: str, filename: str) -> list:
    """Scan lines a patch ADDS. Removing an injection payload is a fix."""
    if not patch:
        return []
    added = "\n".join(
        line[1:] for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    return scan_text(added, filename)


def worst_severity(signals) -> str:
    if any(s.severity == "critical" for s in signals):
        return "critical"
    if any(s.severity == "high" for s in signals):
        return "high"
    return "none" if not signals else "low"
