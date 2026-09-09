import json
import tempfile
import unittest
from pathlib import Path

from catalog import build_library_index


def _manifest(family_id, name, family_kind, automatic_ready=True):
    return {
        "schema": "axion.family",
        "schemaVersion": 2,
        "familyId": family_id,
        "familyKind": family_kind,
        "name": name,
        "category": "Furniture",
        "activeType": "Default",
        "types": {
            "Default": {"width": 1.0, "depth": 1.0, "height": 1.0, "semanticParameters": {}},
        },
        "dimensions": {"width": 1.0, "depth": 1.0, "height": 1.0},
        "quality": {"automaticReady": automatic_ready, "score": 90 if automatic_ready else 60},
        "familyProfile": {"group": "Furniture", "category": "Furniture"},
        "materials": [],
        "geometryVariants": {
            "Default": {"uri": f"{name.lower()}.glb", "baked": True, "primary": True},
            "Wide": {"uri": "variants/wide.glb", "baked": True, "primary": False},
        },
        "thumbnail": {
            "uri": f"{name.lower()}.thumbnail.png",
            "width": 512,
            "height": 512,
            "format": "PNG",
        },
    }


class CatalogTests(unittest.TestCase):
    def test_builds_cross_class_library_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sofa = root / "sofa" / "A" / "a.family.json"
            table = root / "table" / "B" / "b.family.json"
            sofa.parent.mkdir(parents=True)
            table.parent.mkdir(parents=True)
            sofa.write_text(json.dumps(_manifest("axion:sofa:a", "A", "SOFA")), encoding="utf-8")
            table.write_text(json.dumps(_manifest("axion:table:b", "B", "TABLE", False)), encoding="utf-8")

            path, payload = build_library_index(root)
            self.assertTrue(path.exists())
            self.assertEqual(payload["familyCount"], 2)
            self.assertEqual(payload["automaticReady"], 1)
            self.assertEqual(payload["needsReview"], 1)
            self.assertEqual(payload["classCounts"], {"SOFA": 1, "TABLE": 1})

            first = payload["families"][0]
            self.assertEqual(first["familyId"], "axion:sofa:a")
            self.assertEqual(first["manifest"], "sofa/A/a.family.json")
            self.assertEqual(first["geometryVariants"]["Default"], "sofa/A/a.glb")
            self.assertEqual(first["geometryVariants"]["Wide"], "sofa/A/variants/wide.glb")
            self.assertEqual(first["thumbnail"], "sofa/A/a.thumbnail.png")

    def test_rejects_duplicate_family_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in (1, 2):
                path = root / str(index) / f"same_{index}.family.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(_manifest("axion:chair:same", f"Chair {index}", "CHAIR")),
                    encoding="utf-8",
                )

            _path, payload = build_library_index(root)
            self.assertEqual(payload["familyCount"], 1)
            self.assertEqual(len(payload["rejectedManifests"]), 1)
            self.assertIn("duplicate familyId", payload["rejectedManifests"][0]["error"])


if __name__ == "__main__":
    unittest.main()
