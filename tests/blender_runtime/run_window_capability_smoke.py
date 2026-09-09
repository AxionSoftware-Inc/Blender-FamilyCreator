"""Blender 5.2 smoke test for valid baked Window families without separate frames.

Run from repository root:

& 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_window_capability_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_window_capability_smoke"


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


def cube(name, dimensions, location=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def main():
    addon = load_addon()
    addon.register()
    try:
        clean_scene()
        objects = [
            cube("sash_left", (0.58, 0.08, 1.10), (-0.31, 0.0, 0.0)),
            cube("sash_right", (0.58, 0.08, 1.10), (0.31, 0.0, 0.0)),
            cube("sash_center", (0.05, 0.08, 1.10), (0.0, 0.0, 0.0)),
            cube("glass_left", (0.52, 0.025, 0.98), (-0.31, 0.0, 0.0)),
            cube("glass_right", (0.52, 0.025, 0.98), (0.31, 0.0, 0.0)),
        ]
        root = addon.typed.create_typed_family(
            bpy.context,
            objects,
            "Runtime Baked Window",
            "WINDOW",
        )
        quality = addon.quality.validate_family(root)
        if not quality.get("automaticReady", False):
            raise AssertionError(f"Baked Window should be automaticReady: {quality}")

        capabilities = quality.get("semanticCapabilities", {})
        if capabilities.get("separateFrame") is not False:
            raise AssertionError(f"Expected separateFrame=False: {capabilities}")
        if capabilities.get("parametricFrameWidth") is not False:
            raise AssertionError(f"Expected parametricFrameWidth=False: {capabilities}")
        if capabilities.get("separateGlass") is not True:
            raise AssertionError(f"Expected separateGlass=True: {capabilities}")

        result = addon.generators.rebuild_family_geometry(root)
        if result.get("changed"):
            raise AssertionError(f"Baked Window generator should not alter geometry: {result}")
        if result.get("reasonCode") != "NO_SEPARATE_FRAME":
            raise AssertionError(f"Expected NO_SEPARATE_FRAME: {result}")

        print("WINDOW_CAPABILITY_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
