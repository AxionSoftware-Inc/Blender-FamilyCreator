"""Non-destructive mobile LOD generation for Axion family geometry.

LOD meshes are temporary duplicates. Source family objects and datablocks are
never modified. The high-quality family remains the authoring truth.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from . import core
from .geometry_export import export_glb_objects
from .runtime_cost import family_runtime_cost


PROTECTED_ROLES = {
    "HANDLE",
    "HINGE",
    "HARDWARE",
    "DRAIN",
    "CONNECTOR",
    "FAUCET",
    "FLUSH",
    "OVERFLOW",
}


def _evaluated_triangles(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = None
    try:
        try:
            mesh = evaluated.to_mesh()
        except Exception:
            mesh = None
        if mesh is None:
            return 0
        try:
            mesh.calc_loop_triangles()
            return len(mesh.loop_triangles)
        except Exception:
            return sum(max(len(poly.vertices) - 2, 1) for poly in getattr(mesh, "polygons", ()))
    finally:
        if mesh is not None:
            try:
                evaluated.to_mesh_clear()
            except Exception:
                pass


def _duplicate_for_lod(obj, ratio, level):
    duplicate = obj.copy()
    duplicate.name = f"__BFC_{level}_{obj.name}"
    duplicate.parent = None
    duplicate.matrix_world = obj.matrix_world.copy()
    try:
        duplicate.animation_data_clear()
    except Exception:
        pass

    copied_data = None
    if getattr(obj, "type", None) == "MESH" and getattr(obj, "data", None) is not None:
        copied_data = obj.data.copy()
        duplicate.data = copied_data

    bpy.context.scene.collection.objects.link(duplicate)
    duplicate["bfc_lod_source_name"] = obj.name
    duplicate["bfc_lod_level"] = level

    role = str(getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN")
    applied_ratio = float(ratio)
    if role in PROTECTED_ROLES:
        applied_ratio = max(applied_ratio, 0.65)

    skipped_reason = None
    if getattr(duplicate, "type", None) == "MESH" and applied_ratio < 0.999:
        data = getattr(duplicate, "data", None)
        if data is not None and getattr(data, "shape_keys", None) is not None:
            skipped_reason = "SHAPE_KEYS"
        elif len(getattr(data, "polygons", ())) < 24:
            skipped_reason = "LOW_POLY"
        else:
            modifier = duplicate.modifiers.new(name=f"__BFC_{level}_Decimate", type="DECIMATE")
            modifier.decimate_type = "COLLAPSE"
            modifier.ratio = max(0.01, min(applied_ratio, 1.0))
            try:
                modifier.use_collapse_triangulate = True
            except Exception:
                pass

    return duplicate, copied_data, applied_ratio, skipped_reason


def _remove_temporary(objects, datablocks):
    for obj in reversed(objects):
        try:
            if obj and obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        except Exception:
            pass
    for datablock in datablocks:
        try:
            if datablock is not None and datablock.users == 0:
                bpy.data.meshes.remove(datablock)
        except Exception:
            pass


def _export_level(root, directory, level, ratio):
    source_members = list(core.exportable_family_members(root))
    if not source_members:
        raise ValueError("Family has no exportable geometry for LOD generation")

    temporary_objects = []
    temporary_data = []
    skipped = []
    try:
        for obj in source_members:
            duplicate, copied_data, applied_ratio, skipped_reason = _duplicate_for_lod(obj, ratio, level)
            temporary_objects.append(duplicate)
            if copied_data is not None:
                temporary_data.append(copied_data)
            if skipped_reason:
                skipped.append({
                    "source": obj.name,
                    "role": str(getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"),
                    "reason": skipped_reason,
                    "requestedRatio": float(ratio),
                    "appliedRatio": applied_ratio,
                })

        filepath = Path(directory) / "lod" / f"{level.lower()}.glb"
        export_glb_objects(temporary_objects, filepath)
        if not filepath.exists() or filepath.stat().st_size <= 0:
            raise RuntimeError(f"{level} export did not create a GLB file")

        depsgraph = bpy.context.evaluated_depsgraph_get()
        triangles = sum(_evaluated_triangles(obj, depsgraph) for obj in temporary_objects)
        return filepath, triangles, skipped
    finally:
        _remove_temporary(temporary_objects, temporary_data)


def export_family_lods(root, directory, primary_uri="family.glb", enabled=True):
    """Export LOD1/LOD2 derivatives and return manifest-ready metadata.

    If the source is already below a target, that LOD aliases LOD0 instead of
    writing a duplicate GLB. Failures are returned as warnings so callers may
    keep the valid LOD0 family package.
    """
    runtime_cost, mobile_budget = family_runtime_cost(root)
    budget = mobile_budget.get("budget", {})
    source_triangles = int(runtime_cost.get("triangles", 0) or 0)
    lod0_target = int(budget.get("lod0TargetTriangles", source_triangles) or source_triangles)
    lods = {
        "LOD0": {
            "uri": str(primary_uri),
            "generated": False,
            "triangles": source_triangles,
            "targetTriangles": lod0_target,
            "meetsTarget": source_triangles <= lod0_target,
            "ratio": 1.0,
        }
    }
    result = {
        "enabled": bool(enabled),
        "lods": lods,
        "createdFiles": [],
        "warnings": [],
        "runtimeCost": runtime_cost,
        "mobileBudget": mobile_budget,
    }
    if not enabled:
        return result

    levels = (
        (
            "LOD1",
            float(mobile_budget.get("suggestedLod1Ratio", 1.0)),
            int(budget.get("lod1TargetTriangles", source_triangles) or source_triangles),
        ),
        (
            "LOD2",
            float(mobile_budget.get("suggestedLod2Ratio", 1.0)),
            int(budget.get("lod2TargetTriangles", source_triangles) or source_triangles),
        ),
    )
    for level, ratio, target_triangles in levels:
        if ratio >= 0.98:
            lods[level] = {
                "uri": str(primary_uri),
                "generated": False,
                "aliasOf": "LOD0",
                "triangles": source_triangles,
                "targetTriangles": target_triangles,
                "meetsTarget": source_triangles <= target_triangles,
                "ratio": 1.0,
            }
            continue

        try:
            filepath, triangles, skipped = _export_level(root, directory, level, ratio)
            result["createdFiles"].append(filepath)
            meets_target = int(triangles) <= int(target_triangles)
            lods[level] = {
                "uri": filepath.relative_to(Path(directory)).as_posix(),
                "generated": True,
                "triangles": int(triangles),
                "targetTriangles": int(target_triangles),
                "meetsTarget": meets_target,
                "requestedRatio": ratio,
                "protectedOrSkippedMembers": skipped,
            }
            if not meets_target:
                result["warnings"].append(
                    f"{level} has {int(triangles):,} triangles; target is {int(target_triangles):,}"
                )
        except Exception as exc:
            result["warnings"].append(f"{level} generation failed: {exc}")

    return result
