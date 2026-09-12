import copy
import unittest

from schema import validate_manifest


def _base_manifest():
    return {
        "schema": "axion.family",
        "schemaVersion": 2,
        "familyId": "axion:chair:runtime-budget-test",
        "familyKind": "CHAIR",
        "name": "Runtime Budget Test",
        "activeType": "Default",
        "units": {"length": "meter"},
        "coordinateSystems": {
            "family": "RIGHT_HANDED_Z_UP",
            "geometry": "GLTF_RIGHT_HANDED_Y_UP",
        },
        "baseDimensions": {"width": 0.5, "depth": 0.5, "height": 0.9},
        "dimensions": {"width": 0.5, "depth": 0.5, "height": 0.9},
        "types": {
            "Default": {
                "width": 0.5,
                "depth": 0.5,
                "height": 0.9,
                "semanticParameters": {},
            }
        },
        "semanticParameters": {},
        "members": [
            {
                "name": "Seat",
                "type": "MESH",
                "role": "SEAT",
                "rules": {"x": "STRETCH", "y": "STRETCH", "z": "MOVE"},
            }
        ],
        "materials": [],
        "runtimeProxy": {
            "coordinateSystem": "RIGHT_HANDED_Z_UP",
            "selection": {
                "shape": "AABB",
                "min": [-0.25, -0.25, -0.45],
                "max": [0.25, 0.25, 0.45],
                "center": [0.0, 0.0, 0.0],
                "size": [0.5, 0.5, 0.9],
            },
            "collision": {
                "shape": "AABB",
                "coarse": True,
                "center": [0.0, 0.0, 0.0],
                "size": [0.5, 0.5, 0.9],
            },
            "planFootprint": {
                "shape": "RECTANGLE",
                "min": [-0.25, -0.25],
                "max": [0.25, 0.25],
                "baseZ": -0.45,
            },
            "typeBounds": {
                "Default": {
                    "min": [-0.25, -0.25, -0.45],
                    "max": [0.25, 0.25, 0.45],
                    "center": [0.0, 0.0, 0.0],
                    "size": [0.5, 0.5, 0.9],
                }
            },
        },
        "quality": {"ready": True, "automaticReady": True},
        "generator": {"supported": True, "revision": 1},
    }


def _runtime_cost():
    return {
        "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
        "textureMemoryEstimate": "UNCOMPRESSED_RGBA8",
        "memberCount": 1,
        "meshObjects": 1,
        "nonMeshObjects": 0,
        "vertices": 10_000,
        "triangles": 20_000,
        "materialSlots": 2,
        "uniqueMaterials": 2,
        "drawCallEstimate": 2,
        "textureCount": 1,
        "texturePixels": 4_194_304,
        "maxTextureDimension": 2048,
        "estimatedTextureBytesRGBA": 16_777_216,
        "estimatedTextureMemoryMiB": 16.0,
        "textures": [
            {
                "name": "Albedo",
                "width": 2048,
                "height": 2048,
                "pixels": 4_194_304,
                "estimatedBytesRGBA": 16_777_216,
            }
        ],
        "members": [
            {
                "name": "Seat",
                "role": "SEAT",
                "vertices": 10_000,
                "triangles": 20_000,
                "materialSlots": 2,
                "drawCallEstimate": 2,
            }
        ],
    }


def _mobile_budget():
    return {
        "policyVersion": 2,
        "familyKind": "CHAIR",
        "status": "WITHIN_TARGET",
        "sourceTriangles": 20_000,
        "sourceMaterialSlots": 2,
        "sourceDrawCallEstimate": 2,
        "sourceMaxTextureDimension": 2048,
        "sourceTextureMemoryMiB": 16.0,
        "budget": {
            "lod0TargetTriangles": 120_000,
            "lod0HardTriangles": 350_000,
            "lod1TargetTriangles": 40_000,
            "lod2TargetTriangles": 8_000,
            "targetMaterialSlots": 6,
            "targetDrawCalls": 10,
            "targetTextureDimension": 2048,
            "hardTextureDimension": 4096,
            "targetTextureMemoryMiB": 64,
        },
        "suggestedLod1Ratio": 1.0,
        "suggestedLod2Ratio": 0.4,
        "warnings": [],
    }


class RuntimeBudgetSchemaTests(unittest.TestCase):
    def test_valid_runtime_cost_and_mobile_budget_v2(self):
        data = _base_manifest()
        data["runtimeCost"] = _runtime_cost()
        data["mobileBudget"] = _mobile_budget()
        self.assertEqual(validate_manifest(data), [])

    def test_rejects_invalid_texture_record(self):
        data = _base_manifest()
        data["runtimeCost"] = _runtime_cost()
        data["runtimeCost"]["textures"][0]["width"] = -1
        errors = validate_manifest(data)
        self.assertTrue(any("runtimeCost.textures[0].width" in error for error in errors))

    def test_rejects_invalid_texture_memory_marker(self):
        data = _base_manifest()
        data["runtimeCost"] = _runtime_cost()
        data["runtimeCost"]["textureMemoryEstimate"] = "MAGIC_COMPRESSION"
        errors = validate_manifest(data)
        self.assertTrue(any("textureMemoryEstimate" in error for error in errors))

    def test_rejects_negative_runtime_resource_costs(self):
        data = _base_manifest()
        data["runtimeCost"] = _runtime_cost()
        data["runtimeCost"]["drawCallEstimate"] = -1
        data["runtimeCost"]["estimatedTextureMemoryMiB"] = -0.1
        errors = validate_manifest(data)
        self.assertTrue(any("drawCallEstimate" in error for error in errors))
        self.assertTrue(any("estimatedTextureMemoryMiB" in error for error in errors))

    def test_rejects_invalid_mobile_source_resource_costs(self):
        data = _base_manifest()
        data["mobileBudget"] = _mobile_budget()
        data["mobileBudget"]["sourceMaxTextureDimension"] = -1
        data["mobileBudget"]["sourceTextureMemoryMiB"] = -0.5
        errors = validate_manifest(data)
        self.assertTrue(any("sourceMaxTextureDimension" in error for error in errors))
        self.assertTrue(any("sourceTextureMemoryMiB" in error for error in errors))

    def test_rejects_hard_texture_limit_below_target(self):
        data = _base_manifest()
        data["mobileBudget"] = _mobile_budget()
        data["mobileBudget"]["budget"]["hardTextureDimension"] = 1024
        errors = validate_manifest(data)
        self.assertTrue(any("hardTextureDimension must be >=" in error for error in errors))

    def test_rejects_invalid_member_draw_call_cost(self):
        data = _base_manifest()
        data["runtimeCost"] = _runtime_cost()
        data["runtimeCost"]["members"][0]["drawCallEstimate"] = "two"
        errors = validate_manifest(data)
        self.assertTrue(any("runtimeCost.members[0].drawCallEstimate" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
