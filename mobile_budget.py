"""Pure-Python mobile runtime budget policy for Axion families.

Budgets are runtime targets, not source-family validity requirements. A family
can be semantically automaticReady while still needing LOD/material/texture
optimization for mobile.
"""

from __future__ import annotations


DEFAULT_BUDGET = {
    "lod0TargetTriangles": 180_000,
    "lod0HardTriangles": 500_000,
    "lod1TargetTriangles": 60_000,
    "lod2TargetTriangles": 12_000,
    "targetMaterialSlots": 8,
    "targetDrawCalls": 12,
    "targetTextureDimension": 2048,
    "hardTextureDimension": 4096,
    "targetTextureMemoryMiB": 64,
}


CLASS_BUDGETS = {
    "SOFA": {"lod0TargetTriangles": 220_000, "lod0HardTriangles": 600_000, "lod1TargetTriangles": 80_000, "lod2TargetTriangles": 16_000, "targetMaterialSlots": 10, "targetDrawCalls": 16},
    "TABLE": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8, "targetDrawCalls": 12},
    "CHAIR": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6, "targetDrawCalls": 10},
    "BED": {"lod0TargetTriangles": 250_000, "lod0HardTriangles": 700_000, "lod1TargetTriangles": 90_000, "lod2TargetTriangles": 18_000, "targetMaterialSlots": 12, "targetDrawCalls": 18, "targetTextureMemoryMiB": 96},
    "CABINET": {"lod0TargetTriangles": 150_000, "lod0HardTriangles": 400_000, "lod1TargetTriangles": 50_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8, "targetDrawCalls": 12},
    "WARDROBE": {"lod0TargetTriangles": 180_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 60_000, "lod2TargetTriangles": 12_000, "targetMaterialSlots": 10, "targetDrawCalls": 14},
    "SHELF": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6, "targetDrawCalls": 10},
    "KITCHEN_BASE": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8, "targetDrawCalls": 12},
    "KITCHEN_WALL": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8, "targetDrawCalls": 12},
    "DOOR": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6, "targetDrawCalls": 8},
    "WINDOW": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 8, "targetDrawCalls": 10},
    "STAIR": {"lod0TargetTriangles": 280_000, "lod0HardTriangles": 800_000, "lod1TargetTriangles": 100_000, "lod2TargetTriangles": 20_000, "targetMaterialSlots": 8, "targetDrawCalls": 16, "targetTextureMemoryMiB": 96},
    "TOILET": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6, "targetDrawCalls": 8},
    "SINK": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6, "targetDrawCalls": 8},
    "BATHTUB": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6, "targetDrawCalls": 8},
}


OPTIMIZATION_REASONS = {
    "TRIANGLES",
    "MATERIAL_SLOTS",
    "DRAW_CALLS",
    "TEXTURE_DIMENSION",
    "TEXTURE_MEMORY",
}


def budget_for(family_kind):
    budget = dict(DEFAULT_BUDGET)
    budget.update(CLASS_BUDGETS.get(str(family_kind or "GENERIC").upper(), {}))
    return budget


def recommended_decimate_ratio(source_triangles, target_triangles, minimum=0.05):
    source = max(int(source_triangles or 0), 0)
    target = max(int(target_triangles or 0), 0)
    if source <= 0 or target <= 0 or source <= target:
        return 1.0
    return round(max(float(minimum), min(1.0, float(target) / float(source))), 4)


def evaluate_mobile_budget(cost, family_kind):
    cost = cost if isinstance(cost, dict) else {}
    budget = budget_for(family_kind)
    triangles = max(int(cost.get("triangles", 0) or 0), 0)
    material_slots = max(int(cost.get("materialSlots", 0) or 0), 0)
    draw_calls = max(int(cost.get("drawCallEstimate", 0) or 0), 0)
    max_texture_dimension = max(int(cost.get("maxTextureDimension", 0) or 0), 0)
    texture_memory_mib = max(float(cost.get("estimatedTextureMemoryMiB", 0.0) or 0.0), 0.0)

    optimization_reasons = []
    if triangles > budget["lod0TargetTriangles"]:
        optimization_reasons.append("TRIANGLES")
    if material_slots > budget["targetMaterialSlots"]:
        optimization_reasons.append("MATERIAL_SLOTS")
    if draw_calls > budget["targetDrawCalls"]:
        optimization_reasons.append("DRAW_CALLS")
    if max_texture_dimension > budget["targetTextureDimension"]:
        optimization_reasons.append("TEXTURE_DIMENSION")
    if texture_memory_mib > budget["targetTextureMemoryMiB"]:
        optimization_reasons.append("TEXTURE_MEMORY")

    hard_limit = (
        triangles > budget["lod0HardTriangles"]
        or max_texture_dimension > budget["hardTextureDimension"]
    )
    if hard_limit:
        status = "OVER_HARD_LIMIT"
    elif optimization_reasons:
        status = "OVER_TARGET"
    else:
        status = "WITHIN_TARGET"

    warnings = []
    if triangles > budget["lod0HardTriangles"]:
        warnings.append(
            f"LOD0 has {triangles:,} triangles; hard mobile budget is {budget['lod0HardTriangles']:,}"
        )
    elif triangles > budget["lod0TargetTriangles"]:
        warnings.append(
            f"LOD0 has {triangles:,} triangles; target mobile budget is {budget['lod0TargetTriangles']:,}"
        )
    if material_slots > budget["targetMaterialSlots"]:
        warnings.append(
            f"Family uses {material_slots} material slots; target is {budget['targetMaterialSlots']}"
        )
    if draw_calls > budget["targetDrawCalls"]:
        warnings.append(
            f"Estimated draw calls are {draw_calls}; target is {budget['targetDrawCalls']}"
        )
    if max_texture_dimension > budget["hardTextureDimension"]:
        warnings.append(
            f"Texture dimension reaches {max_texture_dimension}px; hard mobile limit is {budget['hardTextureDimension']}px"
        )
    elif max_texture_dimension > budget["targetTextureDimension"]:
        warnings.append(
            f"Texture dimension reaches {max_texture_dimension}px; target is {budget['targetTextureDimension']}px"
        )
    if texture_memory_mib > budget["targetTextureMemoryMiB"]:
        warnings.append(
            f"Estimated uncompressed RGBA texture memory is {texture_memory_mib:.1f} MiB; "
            f"target is {budget['targetTextureMemoryMiB']} MiB"
        )

    geometry_optimization = "TRIANGLES" in optimization_reasons
    material_optimization = any(
        reason in optimization_reasons for reason in ("MATERIAL_SLOTS", "DRAW_CALLS")
    )
    texture_optimization = any(
        reason in optimization_reasons for reason in ("TEXTURE_DIMENSION", "TEXTURE_MEMORY")
    )

    return {
        "policyVersion": 2,
        "familyKind": str(family_kind or "GENERIC").upper(),
        "status": status,
        "sourceTriangles": triangles,
        "sourceMaterialSlots": material_slots,
        "sourceDrawCallEstimate": draw_calls,
        "sourceMaxTextureDimension": max_texture_dimension,
        "sourceTextureMemoryMiB": round(texture_memory_mib, 3),
        "budget": budget,
        "optimizationReasons": optimization_reasons,
        "geometryLodRecommended": geometry_optimization,
        "materialOptimizationRecommended": material_optimization,
        "textureOptimizationRecommended": texture_optimization,
        "suggestedLod1Ratio": recommended_decimate_ratio(triangles, budget["lod1TargetTriangles"]),
        "suggestedLod2Ratio": recommended_decimate_ratio(triangles, budget["lod2TargetTriangles"]),
        "warnings": warnings,
    }
