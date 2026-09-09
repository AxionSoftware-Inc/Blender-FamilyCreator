import unittest

from family_types.strategies import classify_member_role, infer_member_rule


class RealAssetHeuristicTests(unittest.TestCase):
    def test_generic_bed_mattress_survives_headboard_shift(self):
        self.assertEqual(
            classify_member_role(
                "BED",
                (0.82, 0.78, 0.24),
                (0.0, 0.0, -0.22),
                "Cube.014",
            ),
            "MATTRESS",
        )
        self.assertEqual(
            classify_member_role(
                "BED",
                (0.84, 0.12, 0.62),
                (0.0, 0.72, 0.18),
                "Cube.015",
            ),
            "HEADBOARD",
        )
        self.assertEqual(
            classify_member_role(
                "BED",
                (0.80, 0.75, 0.22),
                (0.0, 0.0, -0.62),
                "Cube.016",
            ),
            "BASE",
        )

    def test_generic_window_frame_edges(self):
        self.assertEqual(
            classify_member_role("WINDOW", (0.28, 0.35, 0.82), (-0.72, 0.0, 0.0), "Cube"),
            "FRAME_LEFT",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.28, 0.35, 0.82), (0.72, 0.0, 0.0), "Cube.001"),
            "FRAME_RIGHT",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.82, 0.35, 0.28), (0.0, 0.0, 0.72), "Cube.002"),
            "FRAME_HEAD",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.82, 0.35, 0.28), (0.0, 0.0, -0.72), "Cube.003"),
            "FRAME_SILL",
        )

    def test_generic_window_glass_and_mullions(self):
        self.assertEqual(
            classify_member_role("WINDOW", (0.72, 0.08, 0.72), (0.0, 0.0, 0.0), "Cube.010"),
            "GLASS",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.12, 0.20, 0.72), (0.0, 0.0, 0.0), "Cube.011"),
            "MULLION",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.72, 0.20, 0.12), (0.0, 0.0, 0.0), "Cube.012"),
            "MULLION",
        )
        self.assertEqual(infer_member_rule("WINDOW", "X", 0.12, 0.0, "Cube.011", role="MULLION"), "MOVE")
        self.assertEqual(infer_member_rule("WINDOW", "Z", 0.72, 0.0, "Cube.011", role="MULLION"), "STRETCH")
        self.assertEqual(infer_member_rule("WINDOW", "X", 0.72, 0.0, "Cube.012", role="MULLION"), "STRETCH")
        self.assertEqual(infer_member_rule("WINDOW", "Z", 0.12, 0.0, "Cube.012", role="MULLION"), "MOVE")


if __name__ == "__main__":
    unittest.main()
