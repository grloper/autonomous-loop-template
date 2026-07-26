"""
Tests for the repository scanner and the failure doctor.

Each test protects a defect that shipped in an earlier version of this repo.
"""

import tempfile
import unittest
from pathlib import Path

import _helpers  # noqa: F401
import doctor
import scan
from _helpers import write_tree


def scan_files(files: dict):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_tree(root, files)
        return scan.scan_markers(root, scan.load_config(root))


class Scanning(unittest.TestCase):
    def test_finds_a_marker_in_a_comment(self):
        found = scan_files({"a.py": "x = 1\n# TODO: wire up retries\n"})
        self.assertEqual(len(found), 1)
        self.assertIn("wire up retries", found[0].title)

    def test_ignores_a_marker_outside_a_comment(self):
        """Without this the scanner reports its own configuration table."""
        found = scan_files({"a.py": 'W = {"TODO": 1, "FIXME": 2}\nmsg = "TODO later"\n'})
        self.assertEqual(found, [])

    def test_excludes_by_path_component_not_substring(self):
        """'.git' must not exclude '.github'.

        The original guard was `'.git' in str(path)`, which hid the entire
        .github tree — including the scripts themselves.
        """
        found = scan_files({
            ".github/scripts/tool.py": "# FIXME: broken\n",
            ".git/hooks/x.py": "# FIXME: must be ignored\n",
        })
        self.assertEqual(len(found), 1)
        self.assertIn(".github", found[0].title)

    def test_respects_include_suffixes(self):
        self.assertEqual(scan_files({"notes.md": "<!-- TODO: not a source file -->\n"}), [])

    def test_clean_repo_produces_nothing(self):
        """The original emitted three hardcoded tasks regardless of input."""
        self.assertEqual(scan_files({"a.py": "def f():\n    return 1\n"}), [])

    def test_never_emits_unrelated_domain_content(self):
        found = scan_files({"a.py": "# TODO: add caching\n"})
        blob = " ".join(f.title + f.body for f in found).lower()
        for leaked in ("hand_tracker", "led_controller", "uv curing", "door sensor"):
            self.assertNotIn(leaked, blob)


class Scoring(unittest.TestCase):
    def test_score_is_impact_times_urgency_over_risk(self):
        self.assertEqual(scan.Finding("m", "t", "b", impact=8, urgency=6, risk=4).score, 12.0)

    def test_risk_lowers_score(self):
        low = scan.Finding("m", "t", "b", impact=8, urgency=6, risk=2)
        high = scan.Finding("m", "t", "b", impact=8, urgency=6, risk=8)
        self.assertGreater(low.score, high.score)

    def test_security_wording_escalates(self):
        found = scan_files({"a.py": "# TODO: tidy imports\n",
                            "b.py": "# TODO: validate the auth token here\n"})
        by_note = {f.title.split("—")[-1].strip(): f for f in found}
        plain = next(v for k, v in by_note.items() if "imports" in k)
        secure = next(v for k, v in by_note.items() if "auth" in k)
        self.assertGreater(secure.score, plain.score)
        self.assertIn("security", secure.labels)

    def test_fingerprint_is_stable_across_line_moves(self):
        a = scan_files({"a.py": "# TODO: same note\n"})[0].fingerprint
        b = scan_files({"a.py": "import os\n\n# TODO: same note\n"})[0].fingerprint
        self.assertEqual(a, b, "a shifted line must not create a duplicate issue")

    def test_distinct_markers_get_distinct_fingerprints(self):
        found = scan_files({"a.py": "# TODO: first\n# TODO: second\n"})
        self.assertNotEqual(found[0].fingerprint, found[1].fingerprint)

    def test_malformed_config_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(root, {".github/autonomous-loop.yml": "this: [is: not: valid"})
            self.assertEqual(scan.load_config(root)["min_score"],
                             scan.DEFAULT_CONFIG["min_score"])


class Doctor(unittest.TestCase):
    def test_signatures_match_real_log_text(self):
        cases = {
            "permissions": "##[error]Resource not accessible by integration",
            "dependency": "ModuleNotFoundError: No module named 'github'",
            "syntax": "Invalid workflow file: .github/workflows/x.yml#L5",
            "missing_secret": "Error: Bad credentials (401 Unauthorized)",
            "timeout": "The job running on runner X has exceeded the maximum execution time",
            "disk_space": "write error: no space left on device",
            "rate_limit": "429 Too Many Requests: API rate limit exceeded",
        }
        for expected, log in cases.items():
            with self.subTest(signature=expected):
                self.assertEqual(doctor.diagnose(log, [])[0], expected)

    def test_missing_logs_reported_honestly(self):
        self.assertEqual(doctor.diagnose("", [])[0], "logs_unavailable")

    def test_unrecognised_failure_returns_an_excerpt(self):
        kind, _, _, excerpt = doctor.diagnose("noise\nError: novel failure\nmore", [])
        self.assertEqual(kind, "unknown")
        self.assertIn("novel failure", excerpt)

    def test_doctor_cannot_rewrite_workflow_yaml(self):
        """yaml.safe_load + yaml.dump rewrites 'on:' as 'true:', disabling the workflow."""
        self.assertFalse(hasattr(doctor, "yaml"))
        for line in Path(doctor.__file__).read_text(encoding="utf-8").splitlines():
            self.assertFalse(line.strip().startswith(("import yaml", "from yaml")),
                             "doctor must not import yaml")


class YamlRoundTripHazard(unittest.TestCase):
    def test_documents_why_the_doctor_must_not_round_trip(self):
        import yaml
        parsed = yaml.safe_load("name: x\non:\n  push:\n")
        self.assertIn(True, parsed, "PyYAML parses 'on' as boolean True")
        self.assertNotIn("on", parsed)
        self.assertIn("true:", yaml.dump(parsed))


class ShippedWorkflowsAreValid(unittest.TestCase):
    def test_every_workflow_parses_and_keeps_its_trigger(self):
        import yaml
        root = Path(__file__).resolve().parents[1]
        files = sorted((root / ".github" / "workflows").glob("*.yml"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(workflow=path.name):
                parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIn(True, parsed, "workflow lost its 'on:' trigger")
                self.assertTrue(path.read_text(encoding="utf-8").startswith("name:"))

    def test_no_workflow_interpolates_untrusted_text_into_a_script(self):
        root = Path(__file__).resolve().parents[1]
        import re
        bad = re.compile(r"\$\{\{\s*github\.event\.(pull_request|issue)\.(title|body)")
        for path in (root / ".github" / "workflows").glob("*.yml"):
            with self.subTest(workflow=path.name):
                self.assertIsNone(bad.search(path.read_text(encoding="utf-8")))

    def test_gate_never_checks_out_the_pr_head(self):
        text = (Path(__file__).resolve().parents[1]
                / ".github" / "workflows" / "gate.yml").read_text(encoding="utf-8")
        self.assertNotIn("pull_request.head.ref", text)
        self.assertNotIn("pull_request.head.sha", text)
        self.assertIn("base.sha", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
