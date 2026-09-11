import unittest

from mobile_budget import budget_for, evaluate_mobile_budget, recommended_decimate_ratio


class MobileBudgetTests(unittest.TestCase):
    def test_class_specific_budget(self):
        chair = budget_for("CHAIR")
        stair = budget_for("STAIR")
        self.assertLess(chair["lod0TargetTriangles"], stair["lod0TargetTriangles"])
        self.assertLess(chair["lod2TargetTriangles"], stair["lod2TargetTriangles"])

    def test_decimate_ratio(self):
        self.assertEqual(recommended_decimate_ratio(50_000, 80_000), 1.0)
        self.assertEqual(recommended_decimate_ratio(100_000, 50_000), 0.5)
        self.assertEqual(recommended_decimate_ratio(10_000_000, 10_000), 0.05)

    def test_budget_status(self):
        within = evaluate_mobile_budget({"triangles": 50_000, "materialSlots": 4}, "WINDOW")
        self.assertEqual(within["status"], "WITHIN_TARGET")
        self.assertEqual(within["warnings"], [])

        over = evaluate_mobile_budget({"triangles": 200_000, "materialSlots": 9}, "WINDOW")
        self.assertEqual(over["status"], "OVER_TARGET")
        self.assertTrue(over["warnings"])
        self.assertLess(over["suggestedLod1Ratio"], 1.0)

        hard = evaluate_mobile_budget({"triangles": 500_000, "materialSlots": 2}, "WINDOW")
        self.assertEqual(hard["status"], "OVER_HARD_LIMIT")


if __name__ == "__main__":
    unittest.main()
