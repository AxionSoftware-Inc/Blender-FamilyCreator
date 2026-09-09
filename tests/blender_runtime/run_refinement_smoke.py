"""Blender runtime smoke test for family-level BED/WINDOW role refinement.

Run from repository root:

& 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_refinement_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_refinement_smoke"


def load_addon():
    spec = importlib.util.spec_from_file_location(
        ADDON_NAME,
        REPO_ROOT / "__init__.py",
        submodule_search_locations=[str(REPO_ROOT)],
    )
    addon = importlib.util.module_from_spec(spec)
    sys.modules[ADDON_NAME] = addon
    spec.loader.exec_module(addon)
    return addon


def clean_scene():
    if bpy.context.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def cube(name, dimensions, location):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def bed_refinement(addon):
    clean_scene()
    objects = [
        cube("Cube.001", (2.0, 2.0, 0.20), (0.0, 0.0, 0.12)),
        cube("Cube.002", (1.85, 1.90, 0.32), (0.0, 0.0, 0.48)),
        cube("Headboard", (2.05, 0.14, 2.50), (0.0, 0.93, 1.25)),
    ]
    root = addon.typed.create_typed_family(bpy.context, objects, "Runtime Bed Refinement", "BED")
    members = addon.core.family_members(root)
    mattress = [obj for obj in members if getattr(obj, "bfc_member_role", "") == "MATTRESS"]
    assert_true(mattress, "BED second-pass did not produce MATTRESS")
    assert_true(
        any(obj.get("bfc_role_refinement") == "BED_MATTRESS_CANDIDATE" for obj in mattress),
        "BED MATTRESS was not marked as family-level refinement",
    )
    quality = addon.quality.validate_family(root)
    assert_true(
        quality.get("roleRefinementCounts", {}).get("BED_MATTRESS_CANDIDATE", 0) >= 1,
        "BED refinement diagnostics missing from quality",
    )


def window_refinement(addon):
    clean_scene()
    objects = [
        # Thick, generic frame/casing pieces intentionally exceed first-pass
        # opening-base profile thresholds but remain strong edge candidates.
        cube("Cube.001", (0.66, 0.24, 1.10), (-0.72, 0.0, 0.0)),
        cube("Cube.002", (0.66, 0.24, 1.10), (0.72, 0.0, 0.0)),
        cube("Cube.003", (1.42, 0.24, 0.48), (0.0, 0.0, 0.56)),
        cube("Cube.004", (1.42, 0.24, 0.48), (0.0, 0.0, -0.56)),
        cube("Glass", (1.05, 0.04, 0.75), (0.0, 0.0, 0.0)),
    ]
    root = addon.typed.create_typed_family(bpy.context, objects, "Runtime Window Refinement", "WINDOW")
    members = addon.core.family_members(root)
    roles = {getattr(obj, "bfc_member_role", "UNKNOWN") for obj in members}
    assert_true("GLASS" in roles, "WINDOW explicit GLASS was lost")
    assert_true(
        bool({"FRAME_LEFT", "FRAME_RIGHT", "FRAME_HEAD", "FRAME_SILL"} & roles),
        "WINDOW second-pass did not produce any frame edge",
    )
    refinements = [
        obj for obj in members
        if obj.get("bfc_role_refinement") == "WINDOW_FRAME_EDGE_CANDIDATE"
    ]
    assert_true(refinements, "WINDOW frame refinement diagnostics missing")
    quality = addon.quality.validate_family(root)
    assert_true(
        quality.get("roleRefinementCounts", {}).get("WINDOW_FRAME_EDGE_CANDIDATE", 0) >= 1,
        "WINDOW refinement counts missing from quality",
    )


def main():
    addon = load_addon()
    addon.register()
    try:
        bed_refinement(addon)
        window_refinement(addon)
        print("SEMANTIC_REFINEMENT_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
