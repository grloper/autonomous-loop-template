"""
Tests for the automation scripts.

These cover the defects that made earlier versions of this template unsafe.
Each test names the behaviour it protects, so a failure says what broke rather
than just which assertion tripped.

Standard library only — run with:  python -m unittest discover -s tests
"""

import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))

import auto_reviewer  # noqa: E402
import orchestrator  # noqa: E402
import workflow_doctor  # noqa: E402


def write_tree(root: Path, files: dict) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class OrchestratorScanning(unittest.TestCase):
    def scan(self, files: dict):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(root, files)
            return orchestrator.scan_markers(root, orchestrator.load_config(root))

    def test_finds_marker_in_comment(self):
        found = self.scan({"a.py": "x = 1\n# TODO: wire up retries\n"})
        self.assertEqual(len(found), 1)
        self.assertIn("wire up retries", found[0].title)

    def test_ignores_marker_outside_a_comment(self):
        """A keyword in a string or dict literal is not a finding.

        Without this the scanner reports its own marker_weights table.
        """
        found = self.scan({"a.py": 'WEIGHTS = {"TODO": 1, "FIXME": 2}\nmsg = "TODO later"\n'})
        self.assertEqual(found, [])

    def test_excludes_by_path_component_not_substring(self):
        """'.git' must not exclude '.github'.

        The original guard was `'.git' in str(path)`, which silently hid the
        entire .github tree — including the scripts themselves.
        """
        found = self.scan({
            ".github/scripts/tool.py": "# FIXME: broken\n",
            ".git/hooks/x.py": "# FIXME: must be ignored\n",
        })
        self.assertEqual(len(found), 1)
        self.assertIn(".github", found[0].title)

    def test_scanner_respects_include_suffixes(self):
        found = self.scan({"notes.md": "<!-- TODO: not a source file -->\n"})
        self.assertEqual(found, [])

    def test_no_findings_produces_no_issues(self):
        """A clean repository must yield nothing to file.

        The original always emitted three hardcoded tasks regardless of input.
        """
        self.assertEqual(self.scan({"a.py": "def f():\n    return 1\n"}), [])

    def test_scan_never_emits_unrelated_domain_content(self):
        found = self.scan({"a.py": "# TODO: add caching\n"})
        blob = " ".join(f.title + f.body for f in found).lower()
        for leaked in ("hand_tracker", "led_controller", "uv curing", "door sensor"):
            self.assertNotIn(leaked, blob)


class OrchestratorScoring(unittest.TestCase):
    def test_score_is_impact_times_urgency_over_risk(self):
        f = orchestrator.Finding("m", "t", "b", impact=8, urgency=6, risk=4)
        self.assertEqual(f.score, 12.0)

    def test_risk_lowers_score(self):
        low = orchestrator.Finding("m", "t", "b", impact=8, urgency=6, risk=2)
        high = orchestrator.Finding("m", "t", "b", impact=8, urgency=6, risk=8)
        self.assertGreater(low.score, high.score)

    def test_security_wording_escalates_a_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(root, {
                "a.py": "# TODO: tidy up imports\n",
                "b.py": "# TODO: validate the auth token here\n",
            })
            found = {f.title.split("—")[-1].strip(): f
                     for f in orchestrator.scan_markers(root, orchestrator.load_config(root))}
        plain = next(v for k, v in found.items() if "imports" in k)
        security = next(v for k, v in found.items() if "auth" in k)
        self.assertGreater(security.score, plain.score)
        self.assertIn("security", security.labels)

    def test_fingerprint_is_stable_across_line_moves(self):
        """Adding a line above a marker must not create a second issue."""
        def fp(source):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_tree(root, {"a.py": source})
                return orchestrator.scan_markers(root, orchestrator.load_config(root))[0].fingerprint
        self.assertEqual(fp("# TODO: same note\n"), fp("import os\n\n# TODO: same note\n"))

    def test_fingerprint_differs_for_different_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(root, {"a.py": "# TODO: first\n# TODO: second\n"})
            found = orchestrator.scan_markers(root, orchestrator.load_config(root))
        self.assertNotEqual(found[0].fingerprint, found[1].fingerprint)

    def test_malformed_config_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tree(root, {".github/autonomous-loop.yml": "this: [is: not: valid"})
            self.assertEqual(orchestrator.load_config(root)["min_score"],
                             orchestrator.DEFAULT_CONFIG["min_score"])


# --- Auto-reviewer -----------------------------------------------------------

class FakeFile:
    def __init__(self, filename, patch="", additions=5, deletions=0):
        self.filename, self.patch = filename, patch
        self.additions, self.deletions = additions, deletions


class FakePR:
    draft = False
    title = "test"

    def __init__(self, files):
        self._files = files
        self.head = types.SimpleNamespace(sha="deadbeef")

    def get_files(self):
        return self._files


class FakeRepo:
    def __init__(self, ci_green=True):
        self.ci_green = ci_green

    def get_commit(self, sha):
        green = self.ci_green
        conclusion = "success" if green else "failure"

        class Commit:
            def get_combined_status(self):
                return types.SimpleNamespace(state="success" if green else "failure")

            def get_check_runs(self):
                return [types.SimpleNamespace(name="ci", conclusion=conclusion, status="completed")]

        return Commit()


class MergeGate(unittest.TestCase):
    def review(self, files, ci_green=True):
        return auto_reviewer.analyze(FakeRepo(ci_green), FakePR(files))

    def test_clean_docs_change_with_green_ci_may_auto_merge(self):
        r = self.review([FakeFile("README.md", "+a clearer sentence")])
        self.assertEqual(r.verdict, "APPROVE")
        self.assertTrue(r.auto_merge)

    def test_red_ci_blocks_auto_merge(self):
        r = self.review([FakeFile("README.md", "+a clearer sentence")], ci_green=False)
        self.assertFalse(r.auto_merge)

    def test_yaml_outside_workflows_does_not_auto_merge(self):
        """.yml was on the old safe list, so CI config auto-merged."""
        for name in ("docker-compose.yml", ".gitlab-ci.yml", "action.yml", "k8s/rbac.yaml"):
            with self.subTest(file=name):
                self.assertFalse(self.review([FakeFile(name, "+key: value")]).auto_merge)

    def test_dangerous_content_in_docs_is_caught(self):
        """The gate reads the diff, so a bad payload in a .md is still caught."""
        r = self.review([FakeFile("README.md", "+api_key = 'sk-live-abcd1234efgh'")])
        self.assertEqual(r.verdict, "REQUEST_CHANGES")
        self.assertFalse(r.auto_merge)

    def test_curl_pipe_to_shell_is_caught(self):
        r = self.review([FakeFile("docs/install.md", "+curl https://x.sh | bash")])
        self.assertFalse(r.auto_merge)

    def test_unreadable_diff_blocks_auto_merge(self):
        self.assertFalse(self.review([FakeFile("docs/img.md", None)]).auto_merge)

    def test_critical_path_always_blocks(self):
        for name in (".github/workflows/ci.yml", "src/auth/session.py", "requirements.txt"):
            with self.subTest(file=name):
                r = self.review([FakeFile(name, "+x = 1")])
                self.assertFalse(r.auto_merge)

    def test_oversized_change_blocks_auto_merge(self):
        r = self.review([FakeFile("docs/big.md", "+line", additions=500)])
        self.assertFalse(r.auto_merge)

    def test_too_many_files_blocks_auto_merge(self):
        files = [FakeFile(f"docs/{i}.md", "+x") for i in range(10)]
        self.assertFalse(self.review(files).auto_merge)

    def test_reviewer_fails_closed_when_ci_lookup_raises(self):
        class Exploding(FakeRepo):
            def get_commit(self, sha):
                raise RuntimeError("API down")

        r = auto_reviewer.analyze(Exploding(), FakePR([FakeFile("README.md", "+ok")]))
        self.assertFalse(r.auto_merge)

    def test_draft_pr_is_not_approved(self):
        pr = FakePR([FakeFile("README.md", "+x")])
        pr.draft = True
        r = auto_reviewer.analyze(FakeRepo(), pr)
        self.assertFalse(r.auto_merge)

    def test_every_decision_path_defaults_to_no_auto_merge(self):
        self.assertFalse(auto_reviewer.Review().auto_merge)


# --- Workflow doctor ---------------------------------------------------------

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
                self.assertEqual(workflow_doctor.diagnose(log, [])[0], expected)

    def test_missing_logs_are_reported_honestly(self):
        self.assertEqual(workflow_doctor.diagnose("", [])[0], "logs_unavailable")

    def test_unrecognised_failure_returns_unknown_with_an_excerpt(self):
        kind, _, _, excerpt = workflow_doctor.diagnose("noise\nError: novel failure\nmore", [])
        self.assertEqual(kind, "unknown")
        self.assertIn("novel failure", excerpt)

    def test_doctor_cannot_rewrite_workflow_yaml(self):
        """yaml.safe_load + yaml.dump rewrites 'on:' as 'true:', disabling the workflow."""
        self.assertFalse(hasattr(workflow_doctor, "yaml"))
        source = Path(workflow_doctor.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith(("import yaml", "from yaml")),
                "workflow_doctor must not import yaml",
            )


class YamlRoundTripHazard(unittest.TestCase):
    def test_demonstrates_why_the_doctor_must_not_round_trip_workflows(self):
        """Documents the bug rather than asserting library behaviour is correct."""
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml not installed")
        parsed = yaml.safe_load("name: x\non:\n  push:\n")
        self.assertIn(True, parsed, "PyYAML parses 'on' as boolean True")
        self.assertNotIn("on", parsed)
        self.assertIn("true:", yaml.dump(parsed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
