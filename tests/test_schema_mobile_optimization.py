import copy
import unittest

from schema import validate_manifest
from tests.test_schema import BASE_MANIFEST


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
