"""
Tests for prompt improvement.

The two safety properties matter more than the clustering: proposals must never
be applied without a human, and applying an accepted one must never touch text a
human wrote.
"""

import unittest

import _helpers  # noqa: F401
import prompts
from prompts import FailureRecord as F


def many(category, count, author="copilot-swe-agent[bot]", detail=""):
    return [F(pr_number=i, author=author, category=category, detail=detail)
            for i in range(1, count + 1)]


class Clustering(unittest.TestCase):
    def test_recurring_failure_becomes_a_proposal(self):
        proposals = prompts.cluster(many("hardcoded-secret", 4))
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].category, "hardcoded-secret")
        self.assertEqual(proposals[0].occurrences, 4)

    def test_a_single_incident_proposes_nothing(self):
        """One mistake is an accident. A rule for it is noise."""
        self.assertEqual(prompts.cluster(many("hardcoded-secret", 1)), [])

    def test_threshold_is_configurable(self):
        self.assertEqual(prompts.cluster(many("ci-red", 2), min_occurrences=5), [])
        self.assertEqual(len(prompts.cluster(many("ci-red", 2), min_occurrences=2)), 1)

    def test_unknown_category_is_ignored(self):
        self.assertEqual(prompts.cluster(many("not-a-real-category", 10)), [])

    def test_proposals_are_ordered_by_frequency(self):
        failures = many("ci-red", 3) + many("todo-added", 8)
        self.assertEqual(prompts.cluster(failures)[0].category, "todo-added")

    def test_rule_names_the_most_common_detail(self):
        failures = (many("protected-path", 5, detail="src/auth/**")
                    + many("protected-path", 2, detail="terraform/**"))
        self.assertIn("src/auth/**", prompts.cluster(failures)[0].rule)

    def test_proposal_cites_evidence_and_authors(self):
        p = prompts.cluster(many("reverted", 3, author="devin-ai-integration[bot]"))[0]
        self.assertEqual(p.evidence, [1, 2, 3])
        self.assertEqual(p.authors, ["devin-ai-integration[bot]"])

    def test_evidence_is_deduplicated_per_pull_request(self):
        failures = [F(7, "bot", "ci-red"), F(7, "bot", "ci-red"), F(8, "bot", "ci-red")]
        self.assertEqual(prompts.cluster(failures, min_occurrences=2)[0].evidence, [7, 8])

    def test_every_catalogued_category_produces_a_usable_rule(self):
        for category in prompts.RULE_CATALOGUE:
            with self.subTest(category=category):
                p = prompts.cluster(many(category, 3))[0]
                self.assertTrue(p.rule.strip())
                self.assertNotIn("{", p.rule, "template placeholder left unfilled")
                self.assertNotIn("{", p.rationale)


class ManagedBlock(unittest.TestCase):
    def test_block_is_appended_when_absent(self):
        result = prompts.apply_block("# My instructions\n\nHand-written.\n",
                                     prompts.render_block(prompts.cluster(many("ci-red", 3))))
        self.assertIn("# My instructions", result)
        self.assertIn("Hand-written.", result)
        self.assertIn(prompts.BLOCK_START, result)

    def test_human_text_is_never_modified(self):
        """The tool owns the block and nothing else."""
        human = ("# My instructions\n\nDo not touch this sentence.\n\n"
                 "## Conventions\n\n- Use tabs.\n")
        block = prompts.render_block(prompts.cluster(many("todo-added", 3)))
        once = prompts.apply_block(human, block)
        twice = prompts.apply_block(once, prompts.render_block(
            prompts.cluster(many("ci-red", 3))))
        for line in human.splitlines():
            if line.strip():
                self.assertIn(line, twice)

    def test_reapplying_replaces_rather_than_duplicates(self):
        text = prompts.apply_block("", prompts.render_block(prompts.cluster(many("ci-red", 3))))
        text = prompts.apply_block(text, prompts.render_block(
            prompts.cluster(many("todo-added", 3))))
        self.assertEqual(text.count(prompts.BLOCK_START), 1)
        self.assertEqual(text.count(prompts.BLOCK_END), 1)
        self.assertNotIn("rule:ci-red", text)
        self.assertIn("rule:todo-added", text)

    def test_existing_rules_are_recoverable_from_the_file(self):
        text = prompts.apply_block("", prompts.render_block(
            prompts.cluster(many("ci-red", 3) + many("todo-added", 3))))
        self.assertEqual(set(prompts.parse_managed_block(text)), {"ci-red", "todo-added"})

    def test_no_block_means_no_existing_rules(self):
        self.assertEqual(prompts.parse_managed_block("# Just prose\n"), [])


class Retirement(unittest.TestCase):
    def test_a_rule_whose_failure_stopped_is_retired(self):
        stale = prompts.find_stale(["ci-red"], failures=[],
                                   retire_after_clean=100, recent_prs=150)
        self.assertEqual([p.category for p in stale], ["ci-red"])
        self.assertEqual(stale[0].action, "retire")

    def test_a_rule_whose_failure_persists_is_kept(self):
        stale = prompts.find_stale(["ci-red"], failures=many("ci-red", 3),
                                   retire_after_clean=100, recent_prs=150)
        self.assertEqual(stale, [])

    def test_nothing_retires_before_enough_evidence(self):
        """A quiet week is not proof a rule is no longer needed."""
        self.assertEqual(prompts.find_stale(["ci-red"], [], 100, recent_prs=10), [])


class Report(unittest.TestCase):
    def test_report_cites_pull_requests(self):
        report = prompts.render_report(prompts.cluster(many("reverted", 4)), [], "X.md")
        for number in ("#1", "#2", "#3", "#4"):
            self.assertIn(number, report)

    def test_report_states_nothing_was_applied(self):
        report = prompts.render_report(prompts.cluster(many("ci-red", 3)), [], "X.md")
        self.assertIn("Nothing has been applied", report)

    def test_empty_input_says_so_plainly(self):
        self.assertIn("No instruction changes proposed",
                      prompts.render_report([], [], "X.md"))

    def test_report_names_the_target_file(self):
        self.assertIn("custom/AGENTS.md",
                      prompts.render_report(prompts.cluster(many("ci-red", 3)), [],
                                            "custom/AGENTS.md"))


class ReviewParsing(unittest.TestCase):
    def test_protected_path_is_generalised_to_a_directory(self):
        found = prompts.failures_from_review(
            7, "bot", "- `src/auth/session.py` is a protected path")
        self.assertEqual(found[0].category, "protected-path")
        self.assertEqual(found[0].detail, "src/auth/**")

    def test_top_level_protected_file_keeps_its_name(self):
        found = prompts.failures_from_review(7, "bot", "- `Makefile` is a protected path")
        self.assertEqual(found[0].detail, "Makefile")

    def test_size_limit_is_captured(self):
        found = prompts.failures_from_review(7, "bot", "- 400 lines changed (limit 150)")
        self.assertEqual(found[0].category, "oversized")
        self.assertIn("150", found[0].detail)

    def test_multiple_failures_in_one_review_are_all_captured(self):
        body = ("- `src/auth/x.py` is a protected path\n"
                "- CI is not green (failing: tests)\n"
                "- `README.md`: looks like a hardcoded credential")
        categories = {f.category for f in prompts.failures_from_review(7, "bot", body)}
        self.assertEqual(categories,
                         {"protected-path", "ci-red", "hardcoded-secret"})

    def test_a_clean_review_yields_nothing(self):
        self.assertEqual(prompts.failures_from_review(
            7, "bot", "**Merge gate: APPROVE**\n\nClean diff, CI green."), [])


class SafetyProperties(unittest.TestCase):
    def test_nothing_is_written_without_the_apply_flag(self):
        """cluster/render must be pure — the CLI gates writing behind --apply."""
        source = (_helpers.SCRIPTS / "prompts.py").read_text(encoding="utf-8")
        write_line = next(l for l in source.splitlines()
                          if "instructions_path.write_text" in l)
        self.assertIn("        ", write_line, "write must be nested under a guard")
        self.assertIn("if args.apply", source)

    def test_rules_never_grant_permission(self):
        """A learned rule must constrain an agent, never widen what it may do."""
        forbidden = ("you may", "it is fine to", "allowed to", "auto-merge",
                     "skip review", "without review", "no need to")
        for category, entry in prompts.RULE_CATALOGUE.items():
            with self.subTest(category=category):
                text = entry["rule"].lower()
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_managed_markers_are_html_comments(self):
        """They must be invisible in rendered markdown to a human reader."""
        self.assertTrue(prompts.BLOCK_START.startswith("<!--"))
        self.assertTrue(prompts.BLOCK_END.endswith("-->"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
