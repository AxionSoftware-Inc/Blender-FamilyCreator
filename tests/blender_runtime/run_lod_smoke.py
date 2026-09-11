"""GPU-safe Blender runtime smoke test for non-destructive LOD export.

Run from repository root:

& 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_lod_smoke.py

No thumbnail or render operation is used.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_lod_smoke"


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


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def main():
    addon = load_addon()
    typed = importlib.import_module(f"{ADDON_NAME}.typed")
    library_audit = importlib.import_module(f"{ADDON_NAME}.library_audit")
    catalog_module = importlib.import_module(f"{ADDON_NAME}.catalog")
    addon.register()
    try:
        clean_scene()
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=7, radius=1.0, location=(0.0, 0.0, 1.0))
        source = bpy.context.object
        source.name = "Body"
        source_polygons = len(source.data.polygons)
        source_mesh = source.data

        root = typed.create_typed_family(
            bpy.context,
            [source],
            "Runtime LOD Smoke",
            "GENERIC",
        )
        root["bfc_family_id"] = "axion:generic:runtime-lod-smoke"

        object_count_before = len(bpy.data.objects)
        mesh_count_before = len(bpy.data.meshes)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "library" / "generic" / "runtime-lod-smoke"
            manifest_path, glb_path = typed.export_typed_family(
                root,
                output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=True,
            )
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            lods = data.get("geometryLods", {})

            assert_true(glb_path is not None and Path(glb_path).is_file(), "LOD smoke primary GLB missing")
            assert_true(set(lods) == {"LOD0", "LOD1", "LOD2"}, f"Unexpected LOD levels: {list(lods)}")
            assert_true(lods["LOD1"].get("generated") is True, "LOD1 was expected to be generated")
            assert_true(lods["LOD2"].get("generated") is True, "LOD2 was expected to be generated")
            assert_true(lods["LOD1"]["triangles"] < lods["LOD0"]["triangles"], "LOD1 did not reduce triangles")
            assert_true(lods["LOD2"]["triangles"] < lods["LOD1"]["triangles"], "LOD2 did not reduce below LOD1")

            for level in ("LOD1", "LOD2"):
                uri = lods[level]["uri"]
                lod_path = output / uri
                assert_true(lod_path.is_file() and lod_path.stat().st_size > 0, f"{level} GLB missing")

            assert_true(data.get("runtimeCost", {}).get("triangles", 0) > 180000, "Smoke model did not exceed Generic mobile target")
            assert_true(data.get("mobileBudget", {}).get("status") == "OVER_TARGET", "Unexpected mobile budget status")

            library_root = Path(tmp) / "library"
            audit = library_audit.audit_library(library_root)
            assert_true(audit.get("complete") is True, f"Library audit failed: {audit.get('warnings')}")
            _catalog_path, catalog = catalog_module.build_library_index(library_root)
            assert_true(catalog.get("missingAssetCount") == 0, "Catalog reports missing LOD assets")
            assert_true(catalog.get("familiesWithLods") == 1, "Catalog did not index LOD family")

        assert_true(source.data == source_mesh, "Source mesh datablock was replaced")
        assert_true(len(source.data.polygons) == source_polygons, "Source polygon count changed during LOD export")
        assert_true(len(bpy.data.objects) == object_count_before, "Temporary LOD objects leaked")
        assert_true(len(bpy.data.meshes) == mesh_count_before, "Temporary LOD mesh datablocks leaked")
        assert_true(
            not any(obj.name.startswith("__BFC_LOD") for obj in bpy.data.objects),
            "Temporary LOD object remains in scene",
        )
        print("LOD_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
