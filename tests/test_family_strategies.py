import unittest

from family_types.strategies import infer_member_rule


class FamilyStrategyTests(unittest.TestCase):
    def test_sofa_width_behavior(self):
        self.assertEqual(infer_member_rule("SOFA", "X", 0.80, 0.00, "seat"), "STRETCH")
        self.assertEqual(infer_member_rule("SOFA", "X", 0.15, 0.80, "arm_left"), "MOVE")
        self.assertEqual(infer_member_rule("SOFA", "Y", 0.90, 0.00, "seat"), "FIXED")

    def test_table_leg_and_top_behavior(self):
        self.assertEqual(infer_member_rule("TABLE", "X", 0.12, 0.80, "leg_fl"), "MOVE")
        self.assertEqual(infer_member_rule("TABLE", "Z", 0.12, 0.85, "top"), "MOVE")
        self.assertEqual(infer_member_rule("TABLE", "Z", 0.75, 0.10, "leg"), "STRETCH")

    def test_openings_do_not_scale_depth(self):
        self.assertEqual(infer_member_rule("DOOR", "Y", 0.90, 0.00, "panel"), "FIXED")
        self.assertEqual(infer_member_rule("WINDOW", "Y", 0.90, 0.00, "glass"), "FIXED")
        self.assertEqual(infer_member_rule("DOOR", "X", 0.90, 0.00, "panel"), "STRETCH")

    def test_stair_is_width_only_in_v02(self):
        self.assertEqual(infer_member_rule("STAIR", "X", 0.90, 0.00, "tread"), "STRETCH")
        self.assertEqual(infer_member_rule("STAIR", "Y", 0.90, 0.00, "tread"), "FIXED")
        self.assertEqual(infer_member_rule("STAIR", "Z", 0.90, 0.00, "riser"), "FIXED")

    def test_fixed_fixture(self):
        for axis in ("X", "Y", "Z"):
            self.assertEqual(infer_member_rule("TOILET", axis, 0.90, 0.00, "body"), "FIXED")

    def test_sink_preserves_drain(self):
        self.assertEqual(infer_member_rule("SINK", "X", 0.80, 0.00, "bowl"), "STRETCH")
        self.assertEqual(infer_member_rule("SINK", "X", 0.10, 0.00, "drain"), "FIXED")


if __name__ == "__main__":
    unittest.main()
