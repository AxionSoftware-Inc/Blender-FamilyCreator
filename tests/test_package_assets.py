import unittest

from package_assets import manifest_asset_uris, safe_relative_asset_uri


class PackageAssetTests(unittest.TestCase):
    def test_extracts_unique_managed_runtime_assets(self):
        data = {
            "geometryVariants": {
                "Default": {"uri": "family.glb"},
                "Wide": {"uri": "variants/wide.glb"},
            },
            "geometryLods": {
                "LOD0": {"uri": "family.glb"},
                "LOD1": {"uri": "lod/lod1.glb"},
                "LOD2": {"uri": "family.glb", "aliasOf": "LOD0"},
            },
            "thumbnail": {"uri": "family.thumbnail.png"},
        }
        self.assertEqual(
            manifest_asset_uris(data),
            {
                "family.glb",
                "variants/wide.glb",
                "lod/lod1.glb",
                "family.thumbnail.png",
            },
        )

    def test_rejects_unsafe_asset_uris(self):
        for value in (
            "/absolute/file.glb",
            "C:/windows/file.glb",
            "../outside.glb",
            "lod/../../outside.glb",
            "./family.glb",
            "",
            None,
        ):
            self.assertIsNone(safe_relative_asset_uri(value), value)

    def test_normalizes_windows_separators(self):
        self.assertEqual(
            safe_relative_asset_uri(r"variants\wide.glb"),
            "variants/wide.glb",
        )

    def test_ignores_non_asset_manifest_fields(self):
        data = {
            "source": {"asset": "C:/vendor/original.blend"},
            "members": [{"name": "Part"}],
            "geometryVariants": {},
        }
        self.assertEqual(manifest_asset_uris(data), set())


if __name__ == "__main__":
    unittest.main()
