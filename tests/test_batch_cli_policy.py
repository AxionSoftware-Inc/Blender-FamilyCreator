import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_batch_cli_module():
    fake_bpy = types.ModuleType("bpy")
    spec = importlib.util.spec_from_file_location(
        "bfc_batch_cli_policy_test",
        REPO_ROOT / "batch_cli.py",
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"bpy": fake_bpy}):
        spec.loader.exec_module(module)
    return module


class BatchCliPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_batch_cli_module()

    def _clean_report(self):
        return {
            "failed": 0,
            "ready": 1,
            "needs_review": 0,
            "cleanup_warnings": 0,
            "cleanup_leftover_datablocks": 0,
            "stale_output_count": 0,
            "failed_refresh_package_count": 0,
            "source_index_error": None,
            "library_rejected_manifest_count": 0,
            "library_missing_asset_count": 0,
            "library_index_error": None,
            "library_audit_complete": True,
            "library_audit_warning_count": 0,
            "library_audit_error": None,
        }

    def test_clean_summary_has_no_strict_failures(self):
        summary = self.cli._summary(self._clean_report())
        self.assertEqual(self.cli._strict_failures(summary), [])

    def test_rejected_manifest_blocks_strict_publish(self):
        report = self._clean_report()
        report["library_rejected_manifest_count"] = 2
        summary = self.cli._summary(report)
        failures = self.cli._strict_failures(summary)
        self.assertTrue(any("2 rejected library manifest" in item for item in failures))

    def test_corrupt_source_index_blocks_strict_publish(self):
        report = self._clean_report()
        report["source_index_error"] = "Existing batch-source-index.json is unreadable"
        summary = self.cli._summary(report)
        failures = self.cli._strict_failures(summary)
        self.assertTrue(any("batch source index error" in item for item in failures))

    def test_incomplete_audit_blocks_strict_publish(self):
        report = self._clean_report()
        report["library_audit_complete"] = False
        report["library_audit_warning_count"] = 1
        summary = self.cli._summary(report)
        failures = self.cli._strict_failures(summary)
        self.assertTrue(any("library audit incomplete" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
