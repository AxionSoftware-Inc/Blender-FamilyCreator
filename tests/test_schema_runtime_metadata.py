import copy
import unittest

from schema import validate_manifest
from test_schema import BASE_MANIFEST


class RuntimeMetadataSchemaTests(unittest.TestCase):
    def _with_runtime_metadata(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["runtimeCost"] = {
            "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
            "memberCount": 1,
            "meshObjects": 1,
            "nonMeshObjects": 0,
            "vertices": 1000,
            "triangles": 1800,
            "materialSlots": 2,
            "members": [
                {
                    "name": "Top",
                    "role": "TOP",
                    "vertices": 1000,
                    "triangles": 1800,
                    "materialSlots": 2,
                }
            ],
        }
        data["mobileBudget"] = {
            "policyVersion": 1,
            "familyKind": "TABLE",
            "status": "WITHIN_TARGET",
            "sourceTriangles": 1800,
            "sourceMaterialSlots": 2,
            "budget": {
                "lod0TargetTriangles": 160000,
                "lod0HardTriangles": 450000,
                "lod1TargetTriangles": 55000,
                "lod2TargetTriangles": 10000,
                "targetMaterialSlots": 8,
            },
            "suggestedLod1Ratio": 1.0,
            "suggestedLod2Ratio": 0.5,
            "warnings": [],
        }
        return data

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

    def test_geometry_lods_are_valid(self):
        data = self._with_runtime_metadata()
        data["geometryLods"] = {
            "LOD0": {
                "uri": "family.glb",
                "generated": False,
                "triangles": 180000,
                "ratio": 1.0,
            },
            "LOD1": {
                "uri": "lod/lod1.glb",
                "generated": True,
                "triangles": 55000,
                "requestedRatio": 0.3056,
                "protectedOrSkippedMembers": [],
            },
            "LOD2": {
                "uri": "lod/lod2.glb",
                "generated": True,
                "triangles": 10000,
                "requestedRatio": 0.0556,
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

    def test_lod_alias_is_valid(self):
        data = self._with_runtime_metadata()
        data["geometryLods"] = {
            "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1000, "ratio": 1.0},
            "LOD1": {"uri": "family.glb", "generated": False, "aliasOf": "LOD0", "triangles": 1000, "ratio": 1.0},
            "LOD2": {"uri": "lod/lod2.glb", "generated": True, "triangles": 500, "protectedOrSkippedMembers": []},
        }
        data["lodStrategy"] = {
            "mode": "NON_DESTRUCTIVE_DECIMATE",
            "source": "LOD0",
            "levelCount": 3,
            "protectedRoles": [],
        }
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_lod_path_traversal(self):
        data = self._with_runtime_metadata()
        data["geometryLods"] = {
            "LOD0": {"uri": "family.glb", "generated": False, "triangles": 1000},
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


if __name__ == "__main__":
    unittest.main()
