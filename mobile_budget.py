"""Pure-Python mobile geometry budget policy for Axion families.

Budgets are runtime targets, not source-family validity requirements. A family
can be semantically automaticReady while still needing LOD work for mobile.
"""

from __future__ import annotations


DEFAULT_BUDGET = {
    "lod0TargetTriangles": 180_000,
    "lod0HardTriangles": 500_000,
    "lod1TargetTriangles": 60_000,
    "lod2TargetTriangles": 12_000,
    "targetMaterialSlots": 8,
}


CLASS_BUDGETS = {
    "SOFA": {"lod0TargetTriangles": 220_000, "lod0HardTriangles": 600_000, "lod1TargetTriangles": 80_000, "lod2TargetTriangles": 16_000, "targetMaterialSlots": 10},
    "TABLE": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8},
    "CHAIR": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6},
    "BED": {"lod0TargetTriangles": 250_000, "lod0HardTriangles": 700_000, "lod1TargetTriangles": 90_000, "lod2TargetTriangles": 18_000, "targetMaterialSlots": 12},
    "CABINET": {"lod0TargetTriangles": 150_000, "lod0HardTriangles": 400_000, "lod1TargetTriangles": 50_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8},
    "WARDROBE": {"lod0TargetTriangles": 180_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 60_000, "lod2TargetTriangles": 12_000, "targetMaterialSlots": 10},
    "SHELF": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6},
    "KITCHEN_BASE": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8},
    "KITCHEN_WALL": {"lod0TargetTriangles": 160_000, "lod0HardTriangles": 450_000, "lod1TargetTriangles": 55_000, "lod2TargetTriangles": 10_000, "targetMaterialSlots": 8},
    "DOOR": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6},
    "WINDOW": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 8},
    "STAIR": {"lod0TargetTriangles": 280_000, "lod0HardTriangles": 800_000, "lod1TargetTriangles": 100_000, "lod2TargetTriangles": 20_000, "targetMaterialSlots": 8},
    "TOILET": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6},
    "SINK": {"lod0TargetTriangles": 100_000, "lod0HardTriangles": 300_000, "lod1TargetTriangles": 35_000, "lod2TargetTriangles": 7_000, "targetMaterialSlots": 6},
    "BATHTUB": {"lod0TargetTriangles": 120_000, "lod0HardTriangles": 350_000, "lod1TargetTriangles": 40_000, "lod2TargetTriangles": 8_000, "targetMaterialSlots": 6},
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

    if triangles > budget["lod0HardTriangles"]:
        status = "OVER_HARD_LIMIT"
    elif triangles > budget["lod0TargetTriangles"]:
        status = "OVER_TARGET"
    else:
        status = "WITHIN_TARGET"

    warnings = []
    if status == "OVER_HARD_LIMIT":
        warnings.append(
            f"LOD0 has {triangles:,} triangles; hard mobile budget is {budget['lod0HardTriangles']:,}"
        )
    elif status == "OVER_TARGET":
        warnings.append(
            f"LOD0 has {triangles:,} triangles; target mobile budget is {budget['lod0TargetTriangles']:,}"
        )
    if material_slots > budget["targetMaterialSlots"]:
        warnings.append(
            f"Family uses {material_slots} material slots; target is {budget['targetMaterialSlots']}"
        )

    return {
        "policyVersion": 1,
        "familyKind": str(family_kind or "GENERIC").upper(),
        "status": status,
        "sourceTriangles": triangles,
        "sourceMaterialSlots": material_slots,
        "budget": budget,
        "suggestedLod1Ratio": recommended_decimate_ratio(triangles, budget["lod1TargetTriangles"]),
        "suggestedLod2Ratio": recommended_decimate_ratio(triangles, budget["lod2TargetTriangles"]),
        "warnings": warnings,
    }
