from __future__ import annotations

import copy
import math
import unittest

from training_run_audit import (
    SAMPLE_RUN,
    TrainingRunContractError,
    evidence_summary,
    validate_training_run,
)


class TrainingRunAuditTests(unittest.TestCase):
    def make_run(self):
        return copy.deepcopy(SAMPLE_RUN)

    def test_valid_record_has_non_sensitive_summary(self):
        summary = evidence_summary(self.make_run())

        self.assertEqual(summary["selection_split"], "validation")
        self.assertEqual(summary["split_sizes"], {"train": 3, "validation": 1, "test": 2})

    def test_rejects_test_set_model_selection(self):
        run = self.make_run()
        run["selection"]["used_split"] = "test"

        with self.assertRaisesRegex(TrainingRunContractError, "never 'test'"):
            validate_training_run(run)

    def test_rejects_overlap_between_training_and_test(self):
        run = self.make_run()
        run["splits"]["test"].append("ticket-001")

        with self.assertRaisesRegex(TrainingRunContractError, "overlap"):
            validate_training_run(run)

    def test_rejects_mutable_candidate_alias(self):
        run = self.make_run()
        run["candidate_id"] = "latest"

        with self.assertRaisesRegex(TrainingRunContractError, "mutable alias"):
            validate_training_run(run)

    def test_rejects_missing_lineage(self):
        run = self.make_run()
        del run["transform_id"]

        with self.assertRaisesRegex(TrainingRunContractError, "transform_id"):
            validate_training_run(run)

    def test_rejects_non_finite_test_metric(self):
        run = self.make_run()
        run["test_report"]["metrics"]["macro_f1"] = math.nan

        with self.assertRaisesRegex(TrainingRunContractError, "finite numeric metric"):
            validate_training_run(run)

    def test_allows_finite_metrics_outside_the_unit_interval(self):
        run = self.make_run()
        run["test_report"]["metrics"]["cross_entropy_loss"] = 1.37
        run["test_report"]["slice_metrics"]["billing"]["perplexity"] = 12.4

        validate_training_run(run)

    def test_rejects_test_report_before_selection(self):
        run = self.make_run()
        run["test_report"]["evaluated_after_selection"] = False

        with self.assertRaisesRegex(TrainingRunContractError, "after checkpoint selection"):
            validate_training_run(run)


if __name__ == "__main__":
    unittest.main()
