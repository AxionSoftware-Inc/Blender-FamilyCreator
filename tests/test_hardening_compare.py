import unittest

from hardening_compare import compare_hardening_reports


class HardeningCompareTests(unittest.TestCase):
    def test_separates_overlap_from_new_assets(self):
        baseline = {
            "summary": {
                "discovered": 2,
                "converted": 2,
                "failed": 0,
                "automaticReady": 1,
                "needsReview": 1,
                "conversionSuccessRate": 1.0,
                "autoAcceptanceRate": 0.5,
            },
            "byClass": {
                "BED": {
                    "converted": 1,
                    "automaticReady": 1,
                    "autoAcceptanceRate": 1.0,
                    "averageScore": 95,
                    "averageRoleCoverage": 0.96,
                },
                "WINDOW": {
                    "converted": 1,
                    "automaticReady": 0,
                    "autoAcceptanceRate": 0.0,
                    "averageScore": 80,
                    "averageRoleCoverage": 1.0,
                },
            },
            "byFormat": {
                "BLEND": {
                    "discovered": 2,
                    "converted": 2,
                    "failed": 0,
                    "conversionSuccessRate": 1.0,
                    "autoAcceptanceRate": 0.5,
                }
            },
            "reasonFrequency": {"NON_UNIFORM_SCALE": 1},
            "assets": [
                {
                    "source": r"C:\old\beds\bed.blend",
                    "familyKind": "BED",
                    "converted": True,
                    "automaticReady": True,
                    "score": 95,
                    "roleCoverage": 0.96,
                    "reasons": [],
                },
                {
                    "source": r"C:\old\windows\window.blend",
                    "familyKind": "WINDOW",
                    "converted": True,
                    "automaticReady": False,
                    "score": 80,
                    "roleCoverage": 1.0,
                    "reasons": ["NON_UNIFORM_SCALE"],
                },
            ],
        }
        candidate = {
            "summary": {
                "discovered": 4,
                "converted": 4,
                "failed": 0,
                "automaticReady": 3,
                "needsReview": 1,
                "conversionSuccessRate": 1.0,
                "autoAcceptanceRate": 0.75,
            },
            "byClass": {
                "BED": {
                    "converted": 2,
                    "automaticReady": 2,
                    "autoAcceptanceRate": 1.0,
                    "averageScore": 96,
                    "averageRoleCoverage": 0.97,
                },
                "WINDOW": {
                    "converted": 2,
                    "automaticReady": 1,
                    "autoAcceptanceRate": 0.5,
                    "averageScore": 90,
                    "averageRoleCoverage": 1.0,
                },
            },
            "byFormat": {
                "BLEND": {
                    "discovered": 2,
                    "converted": 2,
                    "failed": 0,
                    "conversionSuccessRate": 1.0,
                    "autoAcceptanceRate": 0.5,
                },
                "FBX": {
                    "discovered": 2,
                    "converted": 2,
                    "failed": 0,
                    "conversionSuccessRate": 1.0,
                    "autoAcceptanceRate": 1.0,
                },
            },
            "reasonFrequency": {"NON_UNIFORM_SCALE": 1},
            "assets": [
                {
                    "source": r"D:\expanded\beds\bed.blend",
                    "familyKind": "BED",
                    "converted": True,
                    "automaticReady": True,
                    "score": 96,
                    "roleCoverage": 0.98,
                    "reasons": [],
                },
                {
                    "source": r"D:\expanded\windows\window.blend",
                    "familyKind": "WINDOW",
                    "converted": True,
                    "automaticReady": False,
                    "score": 80,
                    "roleCoverage": 1.0,
                    "reasons": ["NON_UNIFORM_SCALE"],
                },
                {
                    "source": r"D:\expanded\beds\new_bed.fbx",
                    "familyKind": "BED",
                    "converted": True,
                    "automaticReady": True,
                    "score": 96,
                    "roleCoverage": 0.96,
                    "reasons": [],
                },
                {
                    "source": r"D:\expanded\windows\new_window.fbx",
                    "familyKind": "WINDOW",
                    "converted": True,
                    "automaticReady": True,
                    "score": 100,
                    "roleCoverage": 1.0,
                    "reasons": [],
                },
            ],
        }

        result = compare_hardening_reports(baseline, candidate)
        self.assertEqual(result["corpus"]["overlapCount"], 2)
        self.assertEqual(result["corpus"]["newCount"], 2)
        self.assertEqual(result["corpus"]["removedCount"], 0)
        self.assertEqual(result["newAssets"]["automaticReady"], 2)
        self.assertEqual(result["newAssets"]["autoAcceptanceRate"], 1.0)
        self.assertTrue(result["gate"]["passesNoRegressionGate"])
        self.assertEqual(result["formatDelta"]["FBX"]["candidateConverted"], 2)

    def test_detects_overlap_readiness_regression(self):
        baseline = {
            "summary": {},
            "assets": [{
                "source": r"C:\old\beds\bed.blend",
                "familyKind": "BED",
                "converted": True,
                "automaticReady": True,
                "score": 99,
                "roleCoverage": 0.98,
                "reasons": [],
            }],
        }
        candidate = {
            "summary": {},
            "assets": [{
                "source": r"D:\new\beds\bed.blend",
                "familyKind": "BED",
                "converted": True,
                "automaticReady": False,
                "score": 80,
                "roleCoverage": 0.70,
                "reasons": ["LOW_ROLE_COVERAGE"],
            }],
        }
        result = compare_hardening_reports(baseline, candidate)
        self.assertFalse(result["gate"]["passesNoRegressionGate"])
        self.assertEqual(result["gate"]["overlapRegressionCount"], 1)
        self.assertEqual(result["overlap"]["regressions"][0]["regression"], "AUTOMATIC_READY_LOST")


if __name__ == "__main__":
    unittest.main()
