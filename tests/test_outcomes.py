"""
Tests for outcome measurement and trust scoring.

The confidence maths matters most here. If a single clean merge could buy an
agent autonomy, the whole mechanism becomes a way to launder luck into
permission, so the small-sample behaviour is asserted explicitly.
"""

import json
import tempfile
import unittest
from pathlib import Path

import _helpers  # noqa: F401
import outcomes
import policy as policy_mod
from gate import ChangedFile, PullRequestFacts, evaluate

POL = policy_mod.load_policy(Path(__file__).resolve().parents[1])
THRESHOLDS = {"min_sample": 20, "trusted": 0.95, "watch": 0.80}


def change(number, title, author="copilot-swe-agent[bot]", sha="", branch=None):
    # Default the branch to match the author, so a human-authored fixture is not
    # classified as an agent by an agent branch prefix.
    if branch is None:
        branch = "copilot/x" if author.endswith("[bot]") else "feature/x"
    return outcomes.MergedChange(number=number, title=title, author=author,
                                 branch=branch, merge_sha=sha)


class RevertDetection(unittest.TestCase):
    def test_matches_an_explicit_number_reference(self):
        found = outcomes.detect_reverts(
            [change(7, "Add caching")],
            [outcomes.RevertEvent(subject="Revert the caching change", references=7)])
        self.assertIn(7, found)

    def test_matches_a_quoted_subject(self):
        found = outcomes.detect_reverts(
            [change(7, "Add caching")],
            [outcomes.RevertEvent(subject='Revert "Add caching"')])
        self.assertIn(7, found)

    def test_matches_through_a_squash_merge_suffix(self):
        """GitHub appends '(#7)' to squash subjects; the revert quotes that."""
        found = outcomes.detect_reverts(
            [change(7, "Add caching")],
            [outcomes.RevertEvent(subject='Revert "Add caching (#7)"')])
        self.assertIn(7, found)

    def test_unrelated_revert_is_not_attributed(self):
        found = outcomes.detect_reverts(
            [change(7, "Add caching")],
            [outcomes.RevertEvent(subject='Revert "Something else entirely"')])
        self.assertEqual(found, {})

    def test_a_normal_commit_is_not_a_revert(self):
        found = outcomes.detect_reverts(
            [change(7, "Add caching")],
            [outcomes.RevertEvent(subject="Add more caching")])
        self.assertEqual(found, {})


class BranchBreakDetection(unittest.TestCase):
    def test_failing_merge_commit_is_attributed(self):
        found = outcomes.detect_branch_breaks(
            [change(7, "Add caching", sha="abc123")],
            [outcomes.BranchBreak(sha="abc123")])
        self.assertIn(7, found)

    def test_unrelated_failing_commit_is_not_attributed(self):
        """Only the merge commit's own result counts.

        Blaming a merge for a later failure would attribute flaky
        infrastructure to whoever merged most recently.
        """
        found = outcomes.detect_branch_breaks(
            [change(7, "Add caching", sha="abc123")],
            [outcomes.BranchBreak(sha="def456")])
        self.assertEqual(found, {})


class Confidence(unittest.TestCase):
    def test_zero_merges_scores_zero(self):
        self.assertEqual(outcomes.TrustScore("x", True).confidence, 0.0)

    def test_one_clean_merge_is_not_confident(self):
        """The whole point: a single success must not look like certainty."""
        s = outcomes.TrustScore("x", True, merges=1)
        self.assertEqual(s.raw_rate, 1.0)
        self.assertLess(s.confidence, 0.25)

    def test_confidence_rises_with_volume_at_the_same_rate(self):
        small = outcomes.TrustScore("x", True, merges=5)
        large = outcomes.TrustScore("x", True, merges=200)
        self.assertEqual(small.raw_rate, large.raw_rate)
        self.assertGreater(large.confidence, small.confidence)

    def test_confidence_never_exceeds_the_raw_rate(self):
        for merges, reverts in ((10, 0), (50, 3), (200, 10), (1, 0)):
            with self.subTest(merges=merges, reverts=reverts):
                s = outcomes.TrustScore("x", True, merges=merges, reverts=reverts)
                self.assertLessEqual(s.confidence, s.raw_rate + 1e-9)

    def test_failures_lower_the_score(self):
        clean = outcomes.TrustScore("x", True, merges=50)
        messy = outcomes.TrustScore("x", True, merges=50, reverts=10)
        self.assertGreater(clean.confidence, messy.confidence)

    def test_breaks_and_reverts_both_count_as_failures(self):
        s = outcomes.TrustScore("x", True, merges=10, reverts=2, breaks=3)
        self.assertEqual(s.failures, 5)
        self.assertEqual(s.survivals, 5)

    def test_survivals_never_go_negative(self):
        """A PR both reverted and breaking would otherwise double-count."""
        s = outcomes.TrustScore("x", True, merges=2, reverts=2, breaks=2)
        self.assertEqual(s.survivals, 0)
        self.assertGreaterEqual(s.confidence, 0.0)


class Verdicts(unittest.TestCase):
    def test_small_sample_is_insufficient_data_however_clean(self):
        s = outcomes.TrustScore("x", True, merges=19)
        self.assertEqual(s.verdict(THRESHOLDS), "insufficient-data")

    def test_long_clean_record_is_trusted(self):
        s = outcomes.TrustScore("x", True, merges=500)
        self.assertEqual(s.verdict(THRESHOLDS), "trusted")

    def test_poor_record_is_untrusted(self):
        s = outcomes.TrustScore("x", True, merges=50, reverts=20)
        self.assertEqual(s.verdict(THRESHOLDS), "untrusted")

    def test_middling_record_is_watched(self):
        s = outcomes.TrustScore("x", True, merges=100, reverts=8)
        self.assertEqual(s.verdict(THRESHOLDS), "watch")


class Aggregation(unittest.TestCase):
    def test_scores_are_grouped_by_author(self):
        changes = [change(1, "a"), change(2, "b"), change(3, "c", author="alice")]
        result = outcomes.score(outcomes.build_outcomes(POL, changes, [], []))
        self.assertEqual(result["copilot-swe-agent[bot]"].merges, 2)
        self.assertEqual(result["alice"].merges, 1)
        self.assertTrue(result["copilot-swe-agent[bot]"].is_agent)
        self.assertFalse(result["alice"].is_agent)

    def test_a_reverted_change_is_not_counted_as_survived(self):
        changes = [change(7, "Add caching")]
        reverts = [outcomes.RevertEvent(subject='Revert "Add caching"')]
        result = outcomes.build_outcomes(POL, changes, reverts, [])
        self.assertFalse(result[0].survived)
        self.assertIn("reverted", result[0].reason)

    def test_scoreboard_renders_a_row_per_author(self):
        changes = [change(1, "a"), change(2, "b", author="alice")]
        board = outcomes.render_scoreboard(
            outcomes.score(outcomes.build_outcomes(POL, changes, [], [])), THRESHOLDS)
        self.assertIn("copilot-swe-agent[bot]", board)
        self.assertIn("alice", board)

    def test_empty_scoreboard_says_so(self):
        self.assertIn("No merged pull requests", outcomes.render_scoreboard({}, THRESHOLDS))


class Ledger(unittest.TestCase):
    def test_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.json"
            scores = {"bot": outcomes.TrustScore("bot", True, merges=100)}
            outcomes.save_ledger(path, scores, THRESHOLDS)
            data = json.loads(path.read_text())
        self.assertEqual(data["identities"]["bot"]["verdict"], "trusted")
        self.assertEqual(data["identities"]["bot"]["merges"], 100)

    def test_missing_ledger_is_empty_not_an_error(self):
        self.assertEqual(outcomes.load_ledger(Path("/nonexistent/trust.json")), {})

    def test_corrupt_ledger_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trust.json"
            path.write_text("{not json")
            self.assertEqual(outcomes.load_ledger(path), {})

    def test_trusted_identities_extracts_only_trusted(self):
        ledger = {"identities": {
            "good": {"verdict": "trusted"},
            "meh": {"verdict": "watch"},
            "new": {"verdict": "insufficient-data"},
        }}
        self.assertEqual(outcomes.trusted_identities(ledger), {"good"})


class EarnedAutonomy(unittest.TestCase):
    """Trust may widen the allowlist and nothing else."""

    def setUp(self):
        self.pol = policy_mod.load_policy(Path(__file__).resolve().parents[1])
        self.pol.trust = {**self.pol.trust, "enabled": True,
                          "trusted_auto_merge_paths": ["tests/**"]}
        self.actor = "copilot-swe-agent[bot]"

    def facts(self, filename, patch="+x"):
        return PullRequestFacts(actor=self.actor, branch="copilot/x",
                                ci_state="passing",
                                files=[ChangedFile(filename, patch)])

    def test_untrusted_author_cannot_merge_the_earned_path(self):
        d = evaluate(self.pol, self.facts("tests/test_x.py"), frozenset())
        self.assertFalse(d.auto_merge)

    def test_trusted_author_can_merge_the_earned_path(self):
        d = evaluate(self.pol, self.facts("tests/test_x.py"), frozenset({self.actor}))
        self.assertTrue(d.auto_merge)
        self.assertTrue(d.trusted)

    def test_trust_never_unlocks_a_protected_path(self):
        d = evaluate(self.pol, self.facts(".github/workflows/ci.yml"),
                     frozenset({self.actor}))
        self.assertFalse(d.auto_merge)

    def test_trust_never_relaxes_ci(self):
        facts = self.facts("tests/test_x.py")
        facts.ci_state = "failing"
        self.assertFalse(evaluate(self.pol, facts, frozenset({self.actor})).auto_merge)

    def test_trust_never_relaxes_diff_rules(self):
        d = evaluate(self.pol, self.facts("tests/test_x.py", "+api_key = 'sk-live-abcd1234'"),
                     frozenset({self.actor}))
        self.assertEqual(d.verdict, "REQUEST_CHANGES")

    def test_trust_never_relaxes_size_limits(self):
        facts = PullRequestFacts(
            actor=self.actor, branch="copilot/x", ci_state="passing",
            files=[ChangedFile("tests/test_x.py", "+x", 900, 0)])
        self.assertFalse(evaluate(self.pol, facts, frozenset({self.actor})).auto_merge)

    def test_disabled_trust_ignores_the_trusted_set(self):
        self.pol.trust = {**self.pol.trust, "enabled": False}
        d = evaluate(self.pol, self.facts("tests/test_x.py"), frozenset({self.actor}))
        self.assertFalse(d.auto_merge)

    def test_demo_trust_scenarios_behave_as_labelled(self):
        """The README shows this; a drift here makes the README wrong."""
        import copy

        import demo
        pol = copy.deepcopy(policy_mod.load_policy(Path(__file__).resolve().parents[1]))
        pol.trust = {**pol.trust, "enabled": True,
                     "trusted_auto_merge_paths": ["tests/**"]}
        for label, expected, facts, trusted in demo.trust_scenarios():
            with self.subTest(scenario=label):
                self.assertEqual(evaluate(pol, facts, trusted).auto_merge, expected)

    def test_shipped_policy_has_trust_disabled(self):
        """Shipping this on by default would widen merging without consent."""
        self.assertFalse(policy_mod.load_policy(
            Path(__file__).resolve().parents[1]).trust_enabled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
