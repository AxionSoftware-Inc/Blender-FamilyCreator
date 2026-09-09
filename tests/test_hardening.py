import unittest

from hardening import build_hardening_report, review_reasons


class HardeningMetricsTests(unittest.TestCase):
    def test_review_reason_normalization(self):
        item = {
            "source": "assets/tables/table-chair-set.fbx",
            "quality": {
                "automaticReady": False,
                "roleCoverage": 0.5,
                "missingRoleGroups": [["TOP"]],
                "missingRecommendedRoleGroups": [["LEG", "SUPPORT"]],
                "preflight": {
                    "stats": {
                        "nonUniformScaleMembers": 1,
                        "nonUnitScaleMembers": 1,
                        "negativeDeterminantMembers": 1,
                        "shapeKeyMembers": 0,
                        "armatureMembers": 0,
                        "genericNameShare": 0.75,
                        "mixedSceneNameHint": True,
                    },
                    "warnings": [
                        "Heavy source geometry: 600,000 polygons",
                        "Source name suggests a mixed/multi-item set; review family isolation before automatic acceptance",
                    ],
                    "severe": [],
                },
            },
            "export_warnings": ["Thumbnail render failed"],
        }
        reasons = review_reasons(item)
        self.assertIn("LOW_ROLE_COVERAGE", reasons)
        self.assertIn("MISSING_REQUIRED_ROLE:TOP", reasons)
        self.assertIn("MISSING_RECOMMENDED_ROLE:LEG|SUPPORT", reasons)
        self.assertIn("NON_UNIFORM_SCALE", reasons)
        self.assertIn("MIRRORED_TRANSFORM", reasons)
        self.assertIn("GENERIC_OBJECT_NAMES", reasons)
        self.assertIn("MIXED_SCENE_SUSPECTED", reasons)
        self.assertIn("HEAVY_GEOMETRY", reasons)
        self.assertIn("EXPORT_WARNING", reasons)
        self.assertNotIn("UNAPPLIED_SCALE", reasons)

    def test_generic_names_do_not_create_reason_when_semantics_are_good(self):
        item = {
            "quality": {
                "automaticReady": True,
                "roleCoverage": 1.0,
                "missingRoleGroups": [],
                "missingRecommendedRoleGroups": [],
                "preflight": {
                    "stats": {"genericNameShare": 1.0},
                    "warnings": [],
                    "severe": [],
                },
            }
        }
        self.assertNotIn("GENERIC_OBJECT_NAMES", review_reasons(item))

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
                        "preflight": {
                            "stats": {"genericNameShare": 0.2},
                            "warnings": [],
                            "severe": [],
                        },
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
                        "preflight": {
                            "stats": {"genericNameShare": 0.8},
                            "warnings": [],
                            "severe": [],
                        },
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
        self.assertEqual(result["counts"]["needsReview"], 1)
        self.assertEqual(result["conversionSuccessPercent"], 66.67)
        self.assertEqual(result["automaticReadyPercent"], 50.0)
        self.assertEqual(result["byClass"]["SOFA"]["converted"], 2)
        self.assertEqual(result["byClass"]["SOFA"]["averageGenericNameShare"], 0.5)
        self.assertEqual(result["byFormat"]["FBX"]["converted"], 1)
        self.assertEqual(result["byFormat"]["OBJ"]["failed"], 1)
        reasons = {item["reason"]: item["count"] for item in result["reviewReasons"]}
        self.assertEqual(reasons["LOW_ROLE_COVERAGE"], 1)
        self.assertEqual(reasons["GENERIC_OBJECT_NAMES"], 1)
        self.assertEqual(reasons["CONVERSION_FAILED"], 1)
        self.assertEqual(result["reasonFrequency"]["LOW_ROLE_COVERAGE"], 1)
        self.assertEqual(result["reasonFrequency"]["GENERIC_OBJECT_NAMES"], 1)
        self.assertEqual(result["reasonFrequency"]["CONVERSION_FAILED"], 1)
        self.assertEqual(len(result["assets"]), 3)
        self.assertTrue(result["assets"][0]["converted"])
        self.assertFalse(result["assets"][-1]["converted"])


if __name__ == "__main__":
    unittest.main()
