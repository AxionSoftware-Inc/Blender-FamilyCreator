import copy
import unittest

from schema import validate_manifest
from test_schema import BASE_MANIFEST


class RuntimeMetadataSchemaTests(unittest.TestCase):
    def _with_runtime_metadata(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["runtimeCost"] = {
            "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
            "textureMemoryEstimate": "UNCOMPRESSED_RGBA8",
            "memberCount": 1,
            "meshObjects": 1,
            "nonMeshObjects": 0,
            "vertices": 1000,
            "triangles": 1800,
            "materialSlots": 2,
            "uniqueMaterials": 2,
            "drawCallEstimate": 2,
            "textureCount": 0,
            "texturePixels": 0,
            "maxTextureDimension": 0,
            "estimatedTextureBytesRGBA": 0,
            "estimatedTextureMemoryMiB": 0.0,
            "textures": [],
            "members": [
                {
                    "name": "Top",
                    "role": "TOP",
                    "vertices": 1000,
                    "triangles": 1800,
                    "materialSlots": 2,
                    "drawCallEstimate": 2,
                }
            ],
        }
        data["mobileBudget"] = {
            "policyVersion": 2,
            "familyKind": "TABLE",
            "status": "WITHIN_TARGET",
            "sourceTriangles": 1800,
            "sourceMaterialSlots": 2,
            "sourceDrawCallEstimate": 2,
            "sourceMaxTextureDimension": 0,
            "sourceTextureMemoryMiB": 0.0,
            "budget": {
                "lod0TargetTriangles": 160000,
                "lod0HardTriangles": 450000,
                "lod1TargetTriangles": 55000,
                "lod2TargetTriangles": 10000,
                "targetMaterialSlots": 8,
                "targetDrawCalls": 12,
                "targetTextureDimension": 2048,
                "hardTextureDimension": 4096,
                "targetTextureMemoryMiB": 64,
            },
            "optimizationReasons": [],
            "geometryLodRecommended": False,
            "materialOptimizationRecommended": False,
            "textureOptimizationRecommended": False,
            "suggestedLod1Ratio": 1.0,
            "suggestedLod2Ratio": 1.0,
            "warnings": [],
        }
        return data

    def _add_primary_geometry(self, data, uri="family.glb"):
        data["geometryVariants"] = {
            "Default": {"uri": uri, "baked": True, "primary": True},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_ACTIVE_TYPE",
            "activeType": "Default",
            "variantCount": 1,
        }

    def test_runtime_cost_and_mobile_budget_are_valid(self):
        data = self._with_runtime_metadata()
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_invalid_runtime_cost(self):
        data = self._with_runtime_metadata()
        data["runtimeCost"]["triangles"] = -1
        errors = validate_manifest(data)
        self.assertTrue(any("runtimeCost.triangles" in error for error in errors))

    def test_rejects_invalid_mobile_ratio(self):
        data = self._with_runtime_metadata()
        data["mobileBudget"]["suggestedLod2Ratio"] = 1.5
        errors = validate_manifest(data)
        self.assertTrue(any("suggestedLod2Ratio" in error for error in errors))

    def test_rejects_mobile_runtime_metric_mismatch(self):
        data = self._with_runtime_metadata()
        data["mobileBudget"]["sourceTriangles"] = 1801
        data["mobileBudget"]["sourceTextureMemoryMiB"] = 1.0
        errors = validate_manifest(data)
        self.assertTrue(any("sourceTriangles must match runtimeCost.triangles" in error for error in errors))
        self.assertTrue(any("sourceTextureMemoryMiB must match" in error for error in errors))

    def test_rejects_mobile_family_kind_mismatch(self):
        data = self._with_runtime_metadata()
        data["mobileBudget"]["familyKind"] = "CHAIR"
        errors = validate_manifest(data)
        self.assertTrue(any("mobileBudget.familyKind must match" in error for error in errors))

    def test_geometry_lods_are_valid(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data)
        data["geometryLods"] = {
            "LOD0": {
                "uri": "family.glb",
                "generated": False,
                "triangles": 1800,
                "targetTriangles": 160000,
                "meetsTarget": True,
                "ratio": 1.0,
            },
            "LOD1": {
                "uri": "lod/lod1.glb",
                "generated": True,
                "triangles": 1000,
                "targetTriangles": 55000,
                "meetsTarget": True,
                "requestedRatio": 0.55,
                "protectedOrSkippedMembers": [],
            },
            "LOD2": {
                "uri": "lod/lod2.glb",
                "generated": True,
                "triangles": 500,
                "targetTriangles": 10000,
                "meetsTarget": True,
                "requestedRatio": 0.28,
                "protectedOrSkippedMembers": [],
            },
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 3,
            "protectedRoles": ["HARDWARE"],
        }
        self.assertEqual(validate_manifest(data), [])

    def test_lod_alias_is_valid_even_when_alias_precedes_lod0(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data)
        data["geometryLods"] = {
            "LOD1": {
                "uri": "family.glb",
                "generated": False,
                "aliasOf": "LOD0",
                "triangles": 1800,
                "targetTriangles": 55000,
                "meetsTarget": True,
                "ratio": 1.0,
            },
            "LOD0": {
                "uri": "family.glb",
                "generated": False,
                "triangles": 1800,
                "targetTriangles": 160000,
                "meetsTarget": True,
                "ratio": 1.0,
            },
            "LOD2": {
                "uri": "lod/lod2.glb",
                "generated": True,
                "triangles": 500,
                "targetTriangles": 10000,
                "meetsTarget": True,
                "protectedOrSkippedMembers": [],
            },
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 3,
            "protectedRoles": [],
        }
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_alias_uri_mismatch_regardless_of_record_order(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data)
        data["geometryLods"] = {
            "LOD1": {
                "uri": "other.glb",
                "generated": False,
                "aliasOf": "LOD0",
                "triangles": 1800,
            },
            "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1800},
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 2,
            "protectedRoles": [],
        }
        errors = validate_manifest(data)
        self.assertTrue(any("alias URI must match LOD0" in error for error in errors))

    def test_rejects_non_generated_lod_without_alias(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data)
        data["geometryLods"] = {
            "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1800},
            "LOD1": {"uri": "other.glb", "generated": False, "triangles": 1800},
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 2,
            "protectedRoles": [],
        }
        errors = validate_manifest(data)
        self.assertTrue(any("non-generated level must alias LOD0" in error for error in errors))

    def test_rejects_lod0_runtime_and_primary_uri_mismatch(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data, uri="primary.glb")
        data["geometryLods"] = {
            "LOD0": {"uri": "other.glb", "generated": False, "triangles": 999},
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 1,
            "protectedRoles": [],
        }
        errors = validate_manifest(data)
        self.assertTrue(any("LOD0.triangles must match runtimeCost.triangles" in error for error in errors))
        self.assertTrue(any("LOD0.uri must match" in error for error in errors))

    def test_rejects_meets_target_contradiction(self):
        data = self._with_runtime_metadata()
        self._add_primary_geometry(data)
        data["geometryLods"] = {
            "LOD0": {
                "uri": "family.glb",
                "generated": False,
                "triangles": 1800,
                "targetTriangles": 1000,
                "meetsTarget": True,
            },
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 1,
            "protectedRoles": [],
        }
        errors = validate_manifest(data)
        self.assertTrue(any("meetsTarget must match" in error for error in errors))

    def test_rejects_lod_path_traversal(self):
        data = self._with_runtime_metadata()
        data["geometryLods"] = {
            "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1800},
            "LOD1": {"uri": "../../outside.glb", "generated": True, "triangles": 500},
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 2,
            "protectedRoles": [],
        }
        errors = validate_manifest(data)
        self.assertTrue(any("geometryLods.LOD1.uri" in error for error in errors))

    def test_rejects_variant_path_traversal(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["geometryVariants"] = {
            "Default": {"uri": "../outside.glb", "baked": True, "primary": True},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_ACTIVE_TYPE",
            "activeType": "Default",
            "variantCount": 1,
        }
        errors = validate_manifest(data)
        self.assertTrue(any("geometryVariants.Default.uri" in error for error in errors))

    def test_rejects_wrong_geometry_strategy_mode_for_variant_count(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["geometryVariants"] = {
            "Default": {"uri": "family.glb", "baked": True, "primary": True},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_TYPE_VARIANTS",
            "activeType": "Default",
            "variantCount": 1,
        }
        errors = validate_manifest(data)
        self.assertTrue(any("geometryStrategy.mode must be BAKED_ACTIVE_TYPE" in error for error in errors))

    def test_rejects_geometry_variant_for_unsaved_type(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["geometryVariants"] = {
            "Default": {"uri": "family.glb", "baked": True, "primary": True},
            "Ghost": {"uri": "variants/ghost.glb", "baked": True, "primary": False},
        }
        data["geometryStrategy"] = {
            "mode": "BAKED_TYPE_VARIANTS",
            "activeType": "Default",
            "variantCount": 2,
        }
        errors = validate_manifest(data)
        self.assertTrue(any("Ghost does not match a saved Family Type" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
