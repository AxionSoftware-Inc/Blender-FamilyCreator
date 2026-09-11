import json
import tempfile
import unittest
from pathlib import Path

from library_audit import audit_library


def _manifest(family_id="axion:window:test"):
    return {
        "schema": "axion.family",
        "schemaVersion": 2,
        "familyId": family_id,
        "familyKind": "WINDOW",
        "name": "Test Window",
        "quality": {"automaticReady": True},
        "geometryVariants": {
            "Default": {"uri": "family.glb", "baked": True, "primary": True},
            "Wide": {"uri": "variants/wide.glb", "baked": True, "primary": False},
        },
        "thumbnail": {"uri": "preview.png", "width": 512, "height": 512, "format": "PNG"},
    }


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
            self.assertEqual(result["missingAssetCount"], 3)
            self.assertEqual(result["warningCounts"]["MISSING_GEOMETRY_FILE"], 2)
            self.assertEqual(result["warningCounts"]["MISSING_THUMBNAIL_FILE"], 1)
            self.assertFalse(result["families"][0]["assetsComplete"])

    def test_path_traversal_and_duplicate_ids_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a"
            second = root / "b"
            first.mkdir()
            second.mkdir()

            manifest = _manifest("axion:window:duplicate")
            manifest["geometryVariants"] = {
                "Default": {"uri": "../../outside.glb", "baked": True, "primary": True},
            }
            (first / "a.family.json").write_text(json.dumps(manifest), encoding="utf-8")
            (second / "b.family.json").write_text(json.dumps(_manifest("axion:window:duplicate")), encoding="utf-8")

            result = audit_library(root)
            self.assertEqual(result["warningCounts"]["DUPLICATE_FAMILY_ID"], 1)
            self.assertEqual(result["warningCounts"]["UNSAFE_GEOMETRY_URI"], 1)
            self.assertGreaterEqual(result["unsafeUriCount"], 1)


if __name__ == "__main__":
    unittest.main()
