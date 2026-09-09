import unittest

from family_types.strategies import classify_member_role


class VendorSemanticAliasTests(unittest.TestCase):
    def test_bed_mattress_typo_and_soft_trim_aliases(self):
        self.assertEqual(
            classify_member_role("BED", (0.75, 0.38, 0.24), (0.0, 0.45, -0.31), "mattres"),
            "MATTRESS",
        )
        self.assertEqual(
            classify_member_role("BED", (0.02, 0.78, 0.01), (0.90, 0.0, -0.30), "piping_Part_09"),
            "DECOR",
        )
        self.assertEqual(
            classify_member_role("BED", (0.90, 0.27, 0.56), (0.0, 0.36, -0.17), "BedCover_Part_01"),
            "DECOR",
        )

    def test_opening_named_fasteners_are_hardware(self):
        self.assertEqual(
            classify_member_role("WINDOW", (0.012, 0.12, 0.011), (0.90, -0.65, 0.04), "Bolt.002"),
            "HARDWARE",
        )

    def test_opening_tiny_generic_parts_are_hardware(self):
        self.assertEqual(
            classify_member_role("WINDOW", (0.058, 0.23, 0.09), (0.91, -0.77, -0.03), "Cube.006"),
            "HARDWARE",
        )
        self.assertEqual(
            classify_member_role("WINDOW", (0.008, 0.10, 0.013), (-0.97, 0.65, 0.88), "Cube.009_Part_01"),
            "HARDWARE",
        )

    def test_curved_window_truncated_frame_name_uses_stronger_name_evidence(self):
        self.assertEqual(
            classify_member_role(
                "WINDOW",
                (0.3267, 0.1663, 0.5301),
                (0.3243, 0.0122, -0.3265),
                "L fram _Part_02",
            ),
            "FRAME_RIGHT",
        )
        self.assertEqual(
            classify_member_role(
                "WINDOW",
                (0.3267, 0.1663, 0.5301),
                (-0.3405, 0.0122, -0.3274),
                "L fram _Part_03",
            ),
            "FRAME_LEFT",
        )

    def test_explicit_sash_semantics_remain_sash(self):
        self.assertEqual(
            classify_member_role("WINDOW", (0.75, 0.08, 0.75), (0.0, 0.0, 0.0), "sash"),
            "WINDOW_SASH",
        )


if __name__ == "__main__":
    unittest.main()
