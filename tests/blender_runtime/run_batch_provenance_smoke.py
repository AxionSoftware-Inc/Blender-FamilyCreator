"""GPU-free Blender smoke for repeated-batch source provenance.

Checks:
- a successful run writes batch-source-index.json;
- removing/renaming a source on the same scoped rerun reports a stale package
  without deleting it automatically;
- a current refresh failure preserves the old valid package and reports it as a
  failed-refresh retained package.

Run from repository root:

blender --background --factory-startup --python tests/blender_runtime/run_batch_provenance_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_batch_provenance_smoke"


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
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def write_simple_blend(path, name, x_offset=0.0):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(
        [
            (-0.5 + x_offset, -0.5, 0.0),
            (0.5 + x_offset, -0.5, 0.0),
            (0.5 + x_offset, 0.5, 0.0),
            (-0.5 + x_offset, 0.5, 0.0),
            (-0.5 + x_offset, -0.5, 1.0),
            (0.5 + x_offset, -0.5, 1.0),
            (0.5 + x_offset, 0.5, 1.0),
            (-0.5 + x_offset, 0.5, 1.0),
        ],
        [],
        [
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (4, 0, 3, 7),
        ],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        bpy.data.libraries.write(str(path), {obj, mesh})
    finally:
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.name in bpy.data.meshes and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def run_batch(addon, source, output):
    return addon.batch.batch_convert_directory(
        bpy.context,
        source,
        output,
        "GENERIC",
        recursive=True,
        export_glb=False,
        export_baked_types=False,
        export_thumbnail=False,
        export_lods=False,
        continue_on_error=True,
        auto_split_loose=False,
    )


def main():
    addon = load_addon()
    addon.register()
    try:
        clean_scene()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            output = root / "library"
            asset_a = source / "a.blend"
            asset_b = source / "b.blend"
            write_simple_blend(asset_a, "AssetA")
            write_simple_blend(asset_b, "AssetB")

            first = run_batch(addon, source, output)
            assert_true(first.get("failed") == 0, f"Initial provenance batch failed: {first.get('errors')}")
            assert_true(first.get("converted") == 2, f"Expected two initial conversions: {first}")
            assert_true(first.get("source_index_updated") is True, f"Source index not written: {first}")
            source_index_path = Path(first.get("source_index_path"))
            assert_true(source_index_path.is_file(), "batch-source-index.json missing")
            first_index = json.loads(source_index_path.read_text(encoding="utf-8"))
            assert_true(first_index.get("sourceCount") == 2, f"Unexpected first source index: {first_index}")

            # Remove one source without pruning output. The second run must flag
            # exactly one stale package while leaving it discoverable for manual
            # review/pruning.
            asset_b.unlink()
            second = run_batch(addon, source, output)
            assert_true(second.get("failed") == 0, f"Second provenance batch failed: {second.get('errors')}")
            assert_true(second.get("source_index_comparable") is True, f"Same-root source indexes did not compare: {second}")
            assert_true(second.get("stale_output_count") == 1, f"Removed source was not flagged stale: {second}")
            stale_ids = second.get("stale_output_family_ids", [])
            assert_true(stale_ids == ["axion:generic:b"], f"Unexpected stale package IDs: {stale_ids}")
            stale_manifest = output / "generic" / "b" / "b.family.json"
            assert_true(stale_manifest.is_file(), "Stale package was deleted automatically")

            # Force the remaining source's current refresh to fail. The old
            # package should remain valid and the report must distinguish this
            # from a removed-source stale package.
            old_manifest = output / "generic" / "a" / "a.family.json"
            old_bytes = old_manifest.read_bytes()
            original_convert = addon.batch.convert_asset

            def failing_convert(*_args, **_kwargs):
                raise RuntimeError("forced refresh failure")

            addon.batch.convert_asset = failing_convert
            try:
                third = run_batch(addon, source, output)
            finally:
                addon.batch.convert_asset = original_convert

            assert_true(third.get("failed") == 1, f"Forced refresh failure was not reported: {third}")
            assert_true(third.get("stale_output_count") == 0, f"Current failed source was incorrectly marked removed: {third}")
            assert_true(
                third.get("failed_refresh_package_count") == 1,
                f"Retained old package was not marked failed-refresh: {third}",
            )
            assert_true(
                third.get("failed_refresh_family_ids") == ["axion:generic:a"],
                f"Unexpected failed-refresh IDs: {third}",
            )
            assert_true(old_manifest.is_file(), "Failed refresh deleted the old package")
            assert_true(old_manifest.read_bytes() == old_bytes, "Failed refresh changed old manifest bytes")

        print("BATCH_PROVENANCE_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
