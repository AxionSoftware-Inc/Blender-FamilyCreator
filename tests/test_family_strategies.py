import unittest

from family_types.strategies import classify_member_role, infer_member_rule


class FamilyStrategyTests(unittest.TestCase):
    def test_sofa_width_behavior(self):
        self.assertEqual(infer_member_rule("SOFA", "X", 0.80, 0.00, "seat", role="SEAT"), "STRETCH")
        self.assertEqual(infer_member_rule("SOFA", "X", 0.15, 0.80, "arm_left", role="ARM_LEFT"), "MOVE")
        self.assertEqual(infer_member_rule("SOFA", "Y", 0.90, 0.00, "seat", role="SEAT"), "FIXED")

    def test_sofa_multi_cushion_keeps_cushion_shape(self):
        self.assertEqual(infer_member_rule("SOFA", "X", 0.28, 0.62, "seat_left", role="SEAT"), "MOVE")
        self.assertEqual(infer_member_rule("SOFA", "X", 0.28, 0.00, "seat_center", role="SEAT"), "MOVE")
        self.assertEqual(infer_member_rule("SOFA", "X", 0.28, 0.62, "seat_right", role="SEAT"), "MOVE")

    def test_sofa_role_classification_from_name(self):
        self.assertEqual(classify_member_role("SOFA", (0.15, 0.8, 0.7), (-0.85, 0.0, 0.0), "left_arm"), "ARM_LEFT")
        self.assertEqual(classify_member_role("SOFA", (0.15, 0.8, 0.7), (0.85, 0.0, 0.0), "right_arm"), "ARM_RIGHT")
        self.assertEqual(classify_member_role("SOFA", (0.25, 0.6, 0.2), (0.0, 0.0, -0.2), "seat_cushion"), "SEAT")
        self.assertEqual(classify_member_role("SOFA", (0.25, 0.2, 0.2), (-0.8, -0.5, -0.7), "leg_fl"), "LEG")

    def test_sofa_role_classification_without_names(self):
        self.assertEqual(classify_member_role("SOFA", (0.14, 0.70, 0.70), (-0.82, 0.0, 0.0), "Object.001"), "ARM_LEFT")
        self.assertEqual(classify_member_role("SOFA", (0.14, 0.70, 0.70), (0.82, 0.0, 0.0), "Object.002"), "ARM_RIGHT")
        self.assertEqual(classify_member_role("SOFA", (0.70, 0.65, 0.18), (0.0, 0.0, -0.35), "Object.003"), "SEAT")

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
