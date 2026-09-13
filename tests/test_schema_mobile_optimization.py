import copy
import unittest

from schema import validate_manifest


BASE_MANIFEST = {
    "schema": "axion.family",
    "schemaVersion": 2,
    "familyId": "axion:table:mobile_budget_test",
    "familyKind": "TABLE",
    "name": "Mobile Budget Test",
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
            "semanticParameters": {},
        },
    },
    "semanticParameters": {},
    "members": [
        {
            "name": "Top",
            "type": "MESH",
            "role": "TOP",
            "rules": {"x": "STRETCH", "y": "STRETCH", "z": "MOVE"},
        },
    ],
    "materials": [],
    "runtimeProxy": {
        "coordinateSystem": "RIGHT_HANDED_Z_UP",
        "selection": {
            "shape": "AABB",
            "min": [-0.6, -0.4, -0.375],
            "max": [0.6, 0.4, 0.375],
            "center": [0.0, 0.0, 0.0],
            "size": [1.2, 0.8, 0.75],
        },
        "collision": {
            "shape": "AABB",
            "coarse": True,
            "center": [0.0, 0.0, 0.0],
            "size": [1.2, 0.8, 0.75],
        },
        "planFootprint": {
            "shape": "RECTANGLE",
            "min": [-0.6, -0.4],
            "max": [0.6, 0.4],
            "baseZ": -0.375,
        },
        "typeBounds": {
            "Default": {
                "min": [-0.6, -0.4, -0.375],
                "max": [0.6, 0.4, 0.375],
                "center": [0.0, 0.0, 0.0],
                "size": [1.2, 0.8, 0.75],
            },
        },
    },
    "quality": {"ready": True, "automaticReady": True},
    "generator": {"supported": True, "revision": 1},
}


class MobileOptimizationSchemaTests(unittest.TestCase):
    def _manifest_with_mobile_budget(self):
        data = copy.deepcopy(BASE_MANIFEST)
        data["mobileBudget"] = {
            "policyVersion": 2,
            "familyKind": "TABLE",
            "status": "OVER_TARGET",
            "sourceTriangles": 220000,
            "sourceMaterialSlots": 9,
            "sourceDrawCallEstimate": 14,
            "sourceMaxTextureDimension": 4096,
            "sourceTextureMemoryMiB": 72.0,
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
            "optimizationReasons": [
                "TRIANGLES",
                "MATERIAL_SLOTS",
                "DRAW_CALLS",
                "TEXTURE_DIMENSION",
                "TEXTURE_MEMORY",
            ],
            "geometryLodRecommended": True,
            "materialOptimizationRecommended": True,
            "textureOptimizationRecommended": True,
            "suggestedLod1Ratio": 0.25,
            "suggestedLod2Ratio": 0.05,
            "warnings": ["Optimization recommended"],
        }
        return data

    def test_accepts_optional_optimization_metadata(self):
        self.assertEqual(validate_manifest(self._manifest_with_mobile_budget()), [])

    def test_rejects_unknown_optimization_reason(self):
        data = self._manifest_with_mobile_budget()
        data["mobileBudget"]["optimizationReasons"] = ["TRIANGLES", "MAGIC"]
        errors = validate_manifest(data)
        self.assertTrue(any("optimizationReasons" in error for error in errors))

    def test_rejects_duplicate_optimization_reasons(self):
        data = self._manifest_with_mobile_budget()
        data["mobileBudget"]["optimizationReasons"] = ["TRIANGLES", "TRIANGLES"]
        errors = validate_manifest(data)
        self.assertTrue(any("must not contain duplicates" in error for error in errors))

    def test_rejects_non_boolean_recommendation_flag(self):
        data = self._manifest_with_mobile_budget()
        data["mobileBudget"]["geometryLodRecommended"] = 1
        errors = validate_manifest(data)
        self.assertTrue(any("geometryLodRecommended must be boolean" in error for error in errors))

    def test_old_schema_v2_mobile_budget_without_flags_remains_valid(self):
        data = self._manifest_with_mobile_budget()
        for field in (
            "optimizationReasons",
            "geometryLodRecommended",
            "materialOptimizationRecommended",
            "textureOptimizationRecommended",
        ):
            data["mobileBudget"].pop(field, None)
        self.assertEqual(validate_manifest(data), [])


if __name__ == "__main__":
    unittest.main()
