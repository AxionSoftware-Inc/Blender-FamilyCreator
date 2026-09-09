import unittest
from pathlib import Path

from family_path import resolve_family_class_from_path


class FamilyPathTests(unittest.TestCase):
    def test_resolves_top_level_class_folder(self):
        root = Path("/library/assets")
        self.assertEqual(resolve_family_class_from_path(root / "sofas" / "a.glb", root), "SOFA")
        self.assertEqual(resolve_family_class_from_path(root / "doors" / "d.fbx", root), "DOOR")

    def test_resolves_nested_exact_class_folder(self):
        root = Path("/library/assets")
        path = root / "furniture" / "tables" / "office" / "table.blend"
        self.assertEqual(resolve_family_class_from_path(path, root), "TABLE")

    def test_unknown_folder_does_not_guess(self):
        root = Path("/library/assets")
        self.assertIsNone(resolve_family_class_from_path(root / "random" / "object.glb", root))


if __name__ == "__main__":
    unittest.main()
