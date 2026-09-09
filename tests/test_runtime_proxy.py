import unittest

from runtime_proxy import anchored_axis_bounds, envelope_from_dimensions


class RuntimeProxyTests(unittest.TestCase):
    def test_center_anchor_expands_symmetrically(self):
        minimum, maximum = anchored_axis_bounds(1.0, 2.0, "CENTER")
        self.assertAlmostEqual(minimum, -1.0)
        self.assertAlmostEqual(maximum, 1.0)

    def test_min_anchor_keeps_base_minimum(self):
        minimum, maximum = anchored_axis_bounds(2.0, 3.0, "MIN")
        self.assertAlmostEqual(minimum, -1.0)
        self.assertAlmostEqual(maximum, 2.0)

    def test_max_anchor_keeps_base_maximum(self):
        minimum, maximum = anchored_axis_bounds(2.0, 3.0, "MAX")
        self.assertAlmostEqual(minimum, -2.0)
        self.assertAlmostEqual(maximum, 1.0)

    def test_envelope_uses_family_axis_anchors(self):
        bounds = envelope_from_dimensions(
            (1.0, 2.0, 1.0),
            (2.0, 4.0, 2.0),
            {"X": "CENTER", "Y": "MIN", "Z": "MIN"},
        )
        self.assertEqual(bounds["min"], [-1.0, -1.0, -0.5])
        self.assertEqual(bounds["max"], [1.0, 3.0, 1.5])
        self.assertEqual(bounds["center"], [0.0, 1.0, 0.5])
        self.assertEqual(bounds["size"], [2.0, 4.0, 2.0])


if __name__ == "__main__":
    unittest.main()
