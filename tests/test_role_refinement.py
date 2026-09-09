import unittest

from family_types import bed, window
from family_types.opening_base import (
    ROLE_FRAME_HEAD,
    ROLE_FRAME_LEFT,
    ROLE_FRAME_RIGHT,
    ROLE_FRAME_SILL,
    ROLE_GLASS,
)
from family_types.strategies import refine_member_roles


def member(name, role, span, center):
    return {
        "name": name,
        "role": role,
        "span": span,
        "center": center,
        "normalized_span": span,
        "normalized_center": center,
    }


class BedRoleRefinementTests(unittest.TestCase):
    def test_promotes_upper_broad_base_when_mattress_missing(self):
        members = [
            member("Cube.001", "BASE", (0.82, 0.82, 0.22), (0.0, 0.0, -0.55)),
            member("Cube.002", "BASE", (0.76, 0.78, 0.28), (0.0, 0.0, -0.12)),
            member("Cube.003", "HEADBOARD", (0.80, 0.16, 0.75), (0.0, 0.80, 0.18)),
        ]
        refined = bed.refine_roles(members, (2.0, 2.0, 1.2))
        self.assertEqual(refined[0]["role"], "BASE")
        self.assertEqual(refined[1]["role"], "MATTRESS")
        self.assertEqual(refined[1]["roleRefinement"], "BED_MATTRESS_CANDIDATE")

    def test_does_not_turn_single_base_into_mattress(self):
        members = [
            member("bed_base", "BASE", (0.82, 0.82, 0.24), (0.0, 0.0, -0.20)),
        ]
        refined = bed.refine_roles(members, (2.0, 2.0, 0.8))
        self.assertEqual(refined[0]["role"], "BASE")

    def test_existing_mattress_is_preserved(self):
        members = [
            member("Mattress", "MATTRESS", (0.80, 0.80, 0.20), (0.0, 0.0, -0.10)),
            member("Cube.001", "BASE", (0.85, 0.85, 0.20), (0.0, 0.0, -0.45)),
        ]
        refined = refine_member_roles("BED", members, (2.0, 2.0, 1.0))
        self.assertEqual([item["role"] for item in refined], ["MATTRESS", "BASE"])


class WindowRoleRefinementTests(unittest.TestCase):
    def test_fills_missing_frame_edges_from_generic_parts(self):
        members = [
            member("Cube.001", "UNKNOWN", (0.25, 0.10, 0.82), (-0.78, 0.0, 0.0)),
            member("Cube.002", "UNKNOWN", (0.25, 0.10, 0.82), (0.78, 0.0, 0.0)),
            member("Cube.003", "UNKNOWN", (0.82, 0.10, 0.22), (0.0, 0.0, 0.78)),
            member("Cube.004", "UNKNOWN", (0.82, 0.10, 0.22), (0.0, 0.0, -0.78)),
            member("Cube.005", ROLE_GLASS, (0.70, 0.05, 0.68), (0.0, 0.0, 0.0)),
        ]
        refined = window.refine_roles(members, (1.5, 0.2, 1.5))
        roles = [item["role"] for item in refined]
        self.assertIn(ROLE_FRAME_LEFT, roles)
        self.assertIn(ROLE_FRAME_RIGHT, roles)
        self.assertIn(ROLE_FRAME_HEAD, roles)
        self.assertIn(ROLE_FRAME_SILL, roles)
        self.assertEqual(refined[4]["role"], ROLE_GLASS)

    def test_explicit_sash_is_never_repurposed_as_frame(self):
        members = [
            member("sash", "WINDOW_SASH", (0.26, 0.10, 0.82), (-0.80, 0.0, 0.0)),
        ]
        refined = window.refine_roles(members, (1.2, 0.2, 1.2))
        self.assertEqual(refined[0]["role"], "WINDOW_SASH")

    def test_ambiguous_near_tied_edge_candidates_stay_unresolved(self):
        members = [
            member("Cube.001", "UNKNOWN", (0.24, 0.10, 0.80), (-0.78, 0.0, 0.0)),
            member("Cube.002", "UNKNOWN", (0.24, 0.10, 0.80), (-0.77, 0.0, 0.0)),
        ]
        refined = window.refine_roles(members, (1.2, 0.2, 1.2))
        self.assertNotIn(ROLE_FRAME_LEFT, [item["role"] for item in refined])


if __name__ == "__main__":
    unittest.main()
