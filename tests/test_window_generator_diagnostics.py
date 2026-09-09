import unittest

from hardening import review_reasons


class WindowGeneratorDiagnosticTests(unittest.TestCase):
    def _quality(self):
        return {
            "automaticReady": True,
            "roleCoverage": 1.0,
            "missingRoleGroups": [],
            "missingRecommendedRoleGroups": [],
            "preflight": {"stats": {}, "warnings": [], "severe": []},
        }

    def test_no_separate_frame_is_not_a_review_reason(self):
        reasons = review_reasons({
            "quality": self._quality(),
            "generator": {
                "supported": True,
                "changed": False,
                "reasonCode": "NO_SEPARATE_FRAME",
                "message": "No separate frame members; baked source geometry kept",
            },
        })
        self.assertNotIn("GENERATOR_NO_CHANGE", reasons)
        self.assertNotIn("GENERATOR_MISSING_SEMANTICS", reasons)
        self.assertNotIn("GENERATOR_AUTO_OR_MISSING_SEMANTICS", reasons)

    def test_auto_frame_width_remains_diagnostic(self):
        reasons = review_reasons({
            "quality": self._quality(),
            "generator": {
                "supported": True,
                "changed": False,
                "reasonCode": "PARAMETER_AUTO",
                "message": "Window Frame Width is Auto/zero; source frame geometry kept",
            },
        })
        self.assertIn("GENERATOR_PARAMETER_AUTO", reasons)


if __name__ == "__main__":
    unittest.main()
