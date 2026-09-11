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
        "runtimeCost": {
            "memberCount": 3,
            "vertices": 1000,
            "triangles": 2000,
            "materialSlots": 2,
        },
        "mobileBudget": {
            "status": "WITHIN_TARGET",
            "suggestedLod1Ratio": 1.0,
            "suggestedLod2Ratio": 0.5,
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
            self.assertEqual(payload["mobileBudgetStatusCounts"], {"WITHIN_TARGET": 2})

            first = payload["families"][0]
            self.assertEqual(first["familyId"], "axion:sofa:a")
            self.assertEqual(first["manifest"], "sofa/A/a.family.json")
            self.assertEqual(first["geometryVariants"]["Default"], "sofa/A/a.glb")
            self.assertEqual(first["geometryVariants"]["Wide"], "sofa/A/variants/wide.glb")
            self.assertEqual(first["thumbnail"], "sofa/A/a.thumbnail.png")
            self.assertEqual(first["runtimeCost"]["triangles"], 2000)
            self.assertEqual(first["mobileBudget"]["status"], "WITHIN_TARGET")

    def test_reports_missing_assets_without_rejecting_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "window" / "A" / "a.family.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(_manifest("axion:window:a", "A", "WINDOW")),
                encoding="utf-8",
            )

            _path, payload = build_library_index(root)
            self.assertEqual(payload["familyCount"], 1)
            self.assertEqual(payload["missingAssetCount"], 3)
            self.assertEqual(payload["familiesWithAssetWarnings"], 1)
            self.assertFalse(payload["families"][0]["assetsComplete"])
            self.assertEqual(len(payload["families"][0]["assetWarnings"]), 3)

    def test_existing_assets_clear_integrity_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "window" / "A"
            (package / "variants").mkdir(parents=True)
            manifest = _manifest("axion:window:a", "A", "WINDOW")
            (package / "a.family.json").write_text(json.dumps(manifest), encoding="utf-8")
            (package / "a.glb").write_bytes(b"glb")
            (package / "variants" / "wide.glb").write_bytes(b"glb")
            (package / "a.thumbnail.png").write_bytes(b"png")

            _path, payload = build_library_index(root)
            self.assertEqual(payload["missingAssetCount"], 0)
            self.assertEqual(payload["assetWarningCount"], 0)
            self.assertTrue(payload["families"][0]["assetsComplete"])

    def test_indexes_lod_uris_and_missing_lod_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "window" / "A"
            (package / "variants").mkdir(parents=True)
            (package / "lod").mkdir(parents=True)
            manifest = _manifest("axion:window:a", "A", "WINDOW")
            manifest["geometryLods"] = {
                "LOD0": {"uri": "a.glb", "generated": False, "triangles": 2000},
                "LOD1": {"uri": "lod/lod1.glb", "generated": True, "triangles": 1000},
                "LOD2": {"uri": "lod/lod2.glb", "generated": True, "triangles": 300},
            }
            (package / "a.family.json").write_text(json.dumps(manifest), encoding="utf-8")
            (package / "a.glb").write_bytes(b"glb")
            (package / "variants" / "wide.glb").write_bytes(b"glb")
            (package / "a.thumbnail.png").write_bytes(b"png")
            (package / "lod" / "lod1.glb").write_bytes(b"lod1")

            _path, payload = build_library_index(root)
            self.assertEqual(payload["familiesWithLods"], 1)
            family = payload["families"][0]
            self.assertEqual(family["geometryLods"]["LOD0"]["uri"], "window/A/a.glb")
            self.assertEqual(family["geometryLods"]["LOD1"]["uri"], "window/A/lod/lod1.glb")
            self.assertEqual(family["geometryLods"]["LOD2"]["uri"], "window/A/lod/lod2.glb")
            self.assertEqual(payload["missingAssetCount"], 1)
            self.assertFalse(family["assetsComplete"])

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
