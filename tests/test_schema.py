import copy
import unittest

from schema import assert_valid_manifest, validate_manifest


BASE_MANIFEST = {
    "schema": "axion.family",
    "schemaVersion": 2,
    "familyId": "axion:table:test_table",
    "familyKind": "TABLE",
    "name": "Test Table",
    "activeType": "Default",
    "units": {"length": "meter"},
    "coordinateSystems": {
        "family": "RIGHT_HANDED_Z_UP",
        "geometry": "GLTF_RIGHT_HANDED_Y_UP",
    },
    "baseDimensions": {"width": 1.2, "depth": 0.8, "height": 0.75},
    "dimensions": {"width": 1.2, "depth": 0.8, "height": 0.75},
    "types": {
        "Default": {
            "width": 1.2,
            "depth": 0.8,
            "height": 0.75,
            "semanticParameters": {"top_thickness": 0.04},
        }
    },
    "semanticParameters": {"top_thickness": 0.04},
    "members": [
        {
            "name": "Top",
            "type": "MESH",
            "role": "TOP",
            "rules": {"x": "STRETCH", "y": "STRETCH", "z": "MOVE"},
        }
    ],
    "materials": [],
    "quality": {"ready": True, "automaticReady": True},
    "generator": {"supported": True, "revision": 1},
}


class FamilySchemaTests(unittest.TestCase):
    def test_valid_minimal_schema_v2(self):
        self.assertEqual(validate_manifest(copy.deepcopy(BASE_MANIFEST)), [])
        self.assertIsNotNone(assert_valid_manifest(copy.deepcopy(BASE_MANIFEST)))

    def test_rejects_invalid_dimensions(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["dimensions"]["width"] = 0.0
        errors = validate_manifest(data)
        self.assertTrue(any("dimensions.width" in error for error in errors))

    def test_rejects_invalid_member_rule(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["members"][0]["rules"]["x"] = "SCALE_ANYTHING"
        errors = validate_manifest(data)
        self.assertTrue(any("members[0].rules.x" in error for error in errors))

    def test_rejects_duplicate_material_ids(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["materials"] = [
            {"id": "oak", "name": "Oak A", "usages": []},
            {"id": "oak", "name": "Oak B", "usages": []},
        ]
        errors = validate_manifest(data)
        self.assertTrue(any("duplicate material id" in error for error in errors))

    def test_validates_hosted_opening(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["familyKind"] = "DOOR"
        data["hosting"] = {
            "hostType": "WALL",
            "opening": {
                "shape": "RECTANGLE",
                "width": 0.9,
                "height": 2.1,
                "depth": 0.15,
            },
        }
        self.assertEqual(validate_manifest(data), [])

        data["hosting"]["opening"]["height"] = -2.1
        errors = validate_manifest(data)
        self.assertTrue(any("hosting.opening.height" in error for error in errors))

    def test_validates_baked_geometry_variants(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["types"]["Wide"] = {
            "width": 1.8,
            "depth": 0.8,
            "height": 0.75,
            "semanticParameters": {"top_thickness": 0.04},
        }
        data["geometryVariants"] = {
            "Default": {"uri": "test_table.glb", "baked": True, "primary": True},
            "Wide": {"uri": "variants/wide.glb", "baked": True, "primary": False},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_TYPE_VARIANTS",
            "activeType": "Default",
            "variantCount": 2,
        }
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_variant_primary_mismatch(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["types"]["Wide"] = {
            "width": 1.8,
            "depth": 0.8,
            "height": 0.75,
            "semanticParameters": {"top_thickness": 0.04},
        }
        data["geometryVariants"] = {
            "Default": {"uri": "test_table.glb", "baked": True, "primary": False},
            "Wide": {"uri": "variants/wide.glb", "baked": True, "primary": True},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_TYPE_VARIANTS",
            "activeType": "Default",
            "variantCount": 2,
        }
        errors = validate_manifest(data)
        self.assertTrue(any("primary geometry variant" in error for error in errors))

    def test_rejects_absolute_variant_uri(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["geometryVariants"] = {
            "Default": {"uri": "/tmp/test_table.glb", "baked": True, "primary": True},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_ACTIVE_TYPE",
            "activeType": "Default",
            "variantCount": 1,
        }
        errors = validate_manifest(data)
        self.assertTrue(any("relative non-empty path" in error for error in errors))

    def test_validates_thumbnail_metadata(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["thumbnail"] = {
            "uri": "test_table.thumbnail.png",
            "width": 512,
            "height": 512,
            "format": "PNG",
            "transparent": True,
        }
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_absolute_thumbnail_uri(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["thumbnail"] = {
            "uri": "/tmp/table.png",
            "width": 512,
            "height": 512,
            "format": "PNG",
        }
        errors = validate_manifest(data)
        self.assertTrue(any("thumbnail.uri" in error for error in errors))

    def test_validates_export_warnings(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["exportWarnings"] = ["Thumbnail render failed: no render engine"]
        self.assertEqual(validate_manifest(data), [])

        data["exportWarnings"] = [123]
        errors = validate_manifest(data)
        self.assertTrue(any("exportWarnings" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
