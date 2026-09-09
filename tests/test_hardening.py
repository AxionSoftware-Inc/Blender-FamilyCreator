import unittest

from hardening import build_hardening_report, review_reasons


class HardeningMetricsTests(unittest.TestCase):
    def test_review_reason_normalization(self):
        item = {
            "source": "assets/sofas/a.fbx",
            "quality": {
                "automaticReady": False,
                "roleCoverage": 0.5,
                "missingRoleGroups": [["SEAT"]],
                "missingRecommendedRoleGroups": [["ARM_LEFT", "ARM_RIGHT", "ARM"]],
                "preflight": {
                    "stats": {
                        "nonUniformScaleMembers": 1,
                        "nonUnitScaleMembers": 1,
                        "negativeDeterminantMembers": 1,
                        "shapeKeyMembers": 0,
                        "armatureMembers": 0,
                    },
                    "warnings": ["Heavy source geometry: 600,000 polygons"],
                    "severe": [],
                },
            },
            "export_warnings": ["Thumbnail render failed"],
        }
        reasons = review_reasons(item)
        self.assertIn("LOW_ROLE_COVERAGE", reasons)
        self.assertIn("MISSING_REQUIRED_ROLE:SEAT", reasons)
        self.assertIn("MISSING_RECOMMENDED_ROLE:ARM_LEFT|ARM_RIGHT|ARM", reasons)
        self.assertIn("NON_UNIFORM_SCALE", reasons)
        self.assertIn("MIRRORED_TRANSFORM", reasons)
        self.assertIn("HEAVY_GEOMETRY", reasons)
        self.assertIn("EXPORT_WARNING", reasons)
        self.assertNotIn("UNAPPLIED_SCALE", reasons)

    def test_builds_class_format_and_reason_metrics(self):
        report = {
            "family_kind": "AUTO_FOLDER",
            "input_directory": "assets",
            "output_directory": "library",
            "discovered": 3,
            "results": [
                {
                    "source": "assets/sofas/a.fbx",
                    "family_kind": "SOFA",
                    "quality": {
                        "automaticReady": True,
                        "score": 96,
                        "roleCoverage": 1.0,
                        "missingRoleGroups": [],
                        "missingRecommendedRoleGroups": [],
                        "preflight": {"stats": {}, "warnings": [], "severe": []},
                    },
                },
                {
                    "source": "assets/sofas/b.glb",
                    "family_kind": "SOFA",
                    "quality": {
                        "automaticReady": False,
                        "score": 62,
                        "roleCoverage": 0.6,
                        "missingRoleGroups": [],
                        "missingRecommendedRoleGroups": [],
                        "preflight": {"stats": {}, "warnings": [], "severe": []},
                    },
                },
            ],
            "errors": [{"source": "assets/doors/bad.obj", "error": "import failed"}],
        }
        result = build_hardening_report(report)
        self.assertEqual(result["summary"]["discovered"], 3)
        self.assertEqual(result["summary"]["converted"], 2)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(result["summary"]["automaticReady"], 1)
        self.assertEqual(result["summary"]["autoAcceptanceRate"], 0.5)
        self.assertEqual(result["byClass"]["SOFA"]["converted"], 2)
        self.assertEqual(result["byFormat"]["FBX"]["converted"], 1)
        self.assertEqual(result["byFormat"]["OBJ"]["failed"], 1)
        reasons = {item["reason"]: item["count"] for item in result["reviewReasons"]}
        self.assertEqual(reasons["LOW_ROLE_COVERAGE"], 1)
        self.assertEqual(reasons["CONVERSION_FAILED"], 1)


if __name__ == "__main__":
    unittest.main()
