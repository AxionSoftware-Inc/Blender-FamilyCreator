import unittest

from mobile_budget import budget_for, evaluate_mobile_budget, recommended_decimate_ratio


class MobileBudgetTests(unittest.TestCase):
    def test_class_specific_budget(self):
        chair = budget_for("CHAIR")
        stair = budget_for("STAIR")
        self.assertLess(chair["lod0TargetTriangles"], stair["lod0TargetTriangles"])
        self.assertLess(chair["lod2TargetTriangles"], stair["lod2TargetTriangles"])
        self.assertEqual(budget_for("GENERIC")["targetDrawCalls"], 12)
        self.assertEqual(budget_for("SOFA")["targetDrawCalls"], 16)

    def test_decimate_ratio(self):
        self.assertEqual(recommended_decimate_ratio(50_000, 80_000), 1.0)
        self.assertEqual(recommended_decimate_ratio(100_000, 50_000), 0.5)
        self.assertEqual(recommended_decimate_ratio(10_000_000, 10_000), 0.05)
        self.assertEqual(recommended_decimate_ratio(0, 60_000), 1.0)

    def test_within_all_targets(self):
        result = evaluate_mobile_budget(
            {
                "triangles": 50_000,
                "materialSlots": 4,
                "drawCallEstimate": 6,
                "maxTextureDimension": 2048,
                "estimatedTextureMemoryMiB": 32.0,
            },
            "GENERIC",
        )
        self.assertEqual(result["status"], "WITHIN_TARGET")
        self.assertEqual(result["policyVersion"], 2)
        self.assertEqual(result["warnings"], [])

    def test_triangle_target_and_hard_limit(self):
        target = evaluate_mobile_budget({"triangles": 180_001}, "GENERIC")
        hard = evaluate_mobile_budget({"triangles": 500_001}, "GENERIC")
        self.assertEqual(target["status"], "OVER_TARGET")
        self.assertEqual(hard["status"], "OVER_HARD_LIMIT")
        self.assertLess(target["suggestedLod1Ratio"], 1.0)

    def test_draw_calls_alone_can_require_optimization(self):
        result = evaluate_mobile_budget(
            {
                "triangles": 10_000,
                "materialSlots": 2,
                "drawCallEstimate": 13,
                "maxTextureDimension": 1024,
                "estimatedTextureMemoryMiB": 8.0,
            },
            "GENERIC",
        )
        self.assertEqual(result["status"], "OVER_TARGET")
        self.assertTrue(any("draw calls" in warning.lower() for warning in result["warnings"]))

    def test_texture_dimension_target_vs_hard_limit(self):
        at_target = evaluate_mobile_budget({"triangles": 1_000, "maxTextureDimension": 2048}, "GENERIC")
        at_hard = evaluate_mobile_budget({"triangles": 1_000, "maxTextureDimension": 4096}, "GENERIC")
        over_hard = evaluate_mobile_budget({"triangles": 1_000, "maxTextureDimension": 8192}, "GENERIC")
        self.assertEqual(at_target["status"], "WITHIN_TARGET")
        self.assertEqual(at_hard["status"], "OVER_TARGET")
        self.assertEqual(over_hard["status"], "OVER_HARD_LIMIT")

    def test_texture_memory_can_require_optimization(self):
        result = evaluate_mobile_budget(
            {
                "triangles": 1_000,
                "maxTextureDimension": 2048,
                "estimatedTextureMemoryMiB": 64.001,
            },
            "GENERIC",
        )
        self.assertEqual(result["status"], "OVER_TARGET")
        self.assertTrue(any("texture memory" in warning.lower() for warning in result["warnings"]))

    def test_class_override_can_keep_same_asset_within_target(self):
        cost = {
            "triangles": 10_000,
            "materialSlots": 4,
            "drawCallEstimate": 14,
            "maxTextureDimension": 1024,
            "estimatedTextureMemoryMiB": 8.0,
        }
        self.assertEqual(evaluate_mobile_budget(cost, "GENERIC")["status"], "OVER_TARGET")
        self.assertEqual(evaluate_mobile_budget(cost, "SOFA")["status"], "WITHIN_TARGET")


if __name__ == "__main__":
    unittest.main()
