import copy
import json
import tempfile
import unittest
from pathlib import Path

from library_audit import audit_library
from test_schema import BASE_MANIFEST


def _manifest(family_id="axion:window:test"):
    data = copy.deepcopy(BASE_MANIFEST)
    data["familyId"] = family_id
    data["familyKind"] = "WINDOW"
    data["name"] = "Test Window"
    data["quality"] = {"ready": True, "automaticReady": True, "score": 100}
    data["types"]["Wide"] = {
        "width": 1.8,
        "depth": 0.8,
        "height": 0.75,
        "semanticParameters": {"top_thickness": 0.04},
    }
    data["runtimeProxy"]["typeBounds"]["Wide"] = {
        "min": [-0.9, -0.4, -0.375],
        "max": [0.9, 0.4, 0.375],
        "center": [0.0, 0.0, 0.0],
        "size": [1.8, 0.8, 0.75],
    }
    data["geometryVariants"] = {
        "Default": {"uri": "family.glb", "baked": True, "primary": True},
        "Wide": {"uri": "variants/wide.glb", "baked": True, "primary": False},
    }
    data["geometryStrategy"] = {
        "mode": "BAKED_TYPE_VARIANTS",
        "activeType": "Default",
        "variantCount": 2,
    }
    data["thumbnail"] = {
        "uri": "preview.png",
        "width": 512,
        "height": 512,
        "format": "PNG",
    }
    return data


class LibraryAuditTests(unittest.TestCase):
    def test_complete_family_has_no_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "window" / "test"
            (package / "variants").mkdir(parents=True)
            (package / "family.glb").write_bytes(b"glb")
            (package / "variants" / "wide.glb").write_bytes(b"glb-wide")
            (package / "preview.png").write_bytes(b"png")
            (package / "test.family.json").write_text(json.dumps(_manifest()), encoding="utf-8")

            result = audit_library(root)
            self.assertTrue(result["complete"])
            self.assertEqual(result["manifestCount"], 1)
            self.assertEqual(result["validFamilyCount"], 1)
            self.assertEqual(result["missingAssetCount"], 0)
            self.assertEqual(result["warningCount"], 0)
            self.assertTrue(result["families"][0]["assetsComplete"])

    def test_missing_assets_are_non_destructive_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "window" / "test"
            package.mkdir(parents=True)
            (package / "test.family.json").write_text(json.dumps(_manifest()), encoding="utf-8")

            result = audit_library(root)
            self.assertFalse(result["complete"])
            self.assertEqual(result["validFamilyCount"], 1)
            self.assertEqual(result["missingAssetCount"], 3)
            self.assertEqual(result["warningCounts"]["MISSING_GEOMETRY_FILE"], 2)
            self.assertEqual(result["warningCounts"]["MISSING_THUMBNAIL_FILE"], 1)
            self.assertFalse(result["families"][0]["assetsComplete"])

    def test_lod_files_are_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "window" / "test"
            (package / "variants").mkdir(parents=True)
            (package / "lod").mkdir(parents=True)
            manifest = _manifest()
            manifest["geometryLods"] = {
                "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1000},
                "LOD1": {"uri": "lod/lod1.glb", "generated": True, "triangles": 500},
                "LOD2": {"uri": "lod/missing.glb", "generated": True, "triangles": 100},
            }
            manifest["lodStrategy"] = {
                "mode": "NON_DESTRUCTIVE_DECIMATE",
                "source": "LOD0",
                "levelCount": 3,
                "protectedRoles": [],
            }
            (package / "family.glb").write_bytes(b"glb")
            (package / "variants" / "wide.glb").write_bytes(b"glb-wide")
            (package / "preview.png").write_bytes(b"png")
            (package / "lod" / "lod1.glb").write_bytes(b"lod1")
            (package / "test.family.json").write_text(json.dumps(manifest), encoding="utf-8")

            result = audit_library(root)
            self.assertEqual(result["validFamilyCount"], 1)
            self.assertEqual(result["warningCounts"]["MISSING_LOD_FILE"], 1)
            self.assertEqual(result["missingAssetCount"], 1)
            self.assertFalse(result["complete"])

    def test_path_traversal_is_reported_even_when_schema_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "a"
            package.mkdir()

            manifest = _manifest("axion:window:unsafe")
            manifest["geometryVariants"] = {
                "Default": {"uri": "../../outside.glb", "baked": True, "primary": True},
            }
            manifest["geometryStrategy"] = {
                "mode": "BAKED_ACTIVE_TYPE",
                "activeType": "Default",
                "variantCount": 1,
            }
            manifest["geometryLods"] = {
                "LOD0": {"uri": "../../outside-lod.glb", "generated": False, "triangles": 1},
            }
            manifest["lodStrategy"] = {
                "mode": "NON_DESTRUCTIVE_DECIMATE",
                "source": "LOD0",
                "levelCount": 1,
                "protectedRoles": [],
            }
            (package / "a.family.json").write_text(json.dumps(manifest), encoding="utf-8")

            result = audit_library(root)
            self.assertEqual(result["validFamilyCount"], 0)
            self.assertEqual(result["warningCounts"]["INVALID_MANIFEST_SCHEMA"], 1)
            self.assertEqual(result["warningCounts"]["UNSAFE_GEOMETRY_URI"], 1)
            self.assertEqual(result["warningCounts"]["UNSAFE_LOD_URI"], 1)
            self.assertGreaterEqual(result["unsafeUriCount"], 2)

    def test_duplicate_valid_family_ids_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a"
            second = root / "b"
            first.mkdir()
            second.mkdir()
            family_id = "axion:window:duplicate"
            (first / "a.family.json").write_text(json.dumps(_manifest(family_id)), encoding="utf-8")
            (second / "b.family.json").write_text(json.dumps(_manifest(family_id)), encoding="utf-8")

            result = audit_library(root)
            self.assertEqual(result["validFamilyCount"], 2)
            self.assertEqual(result["familyIdsUnique"], 1)
            self.assertEqual(result["warningCounts"]["DUPLICATE_FAMILY_ID"], 1)
            self.assertFalse(result["complete"])

    def test_schema_invalid_manifest_is_not_counted_as_valid_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "bad"
            package.mkdir()
            manifest = _manifest("axion:window:bad")
            manifest["dimensions"]["width"] = 0.0
            (package / "bad.family.json").write_text(json.dumps(manifest), encoding="utf-8")

            result = audit_library(root)
            self.assertEqual(result["manifestCount"], 1)
            self.assertEqual(result["validFamilyCount"], 0)
            self.assertEqual(result["warningCounts"]["INVALID_MANIFEST_SCHEMA"], 1)
            self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
