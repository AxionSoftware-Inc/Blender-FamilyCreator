"""GPU-free Blender smoke test for leak-resistant batch datablock cleanup.

Verifies:
- post-snapshot Mesh -> Material -> Image dependency cleanup;
- imported Collection cleanup;
- pre-existing zero-user data survives;
- `convert_asset()` cleans partial objects/datablocks even when an importer
  raises after allocating Blender IDs;
- cleanup-diagnostic failure does not mask a successful family conversion.

Run from repository root:

blender --background --factory-startup --python tests/blender_runtime/run_cleanup_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_cleanup_smoke"


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


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def test_direct_snapshot_cleanup(addon, sentinel):
    snapshot = addon.batch_cleanup.snapshot_datablocks()

    imported_collection = bpy.data.collections.new("ImportedAssetCollection")
    bpy.context.scene.collection.children.link(imported_collection)

    mesh = bpy.data.meshes.new("ImportedMesh")
    mesh.from_pydata(
        [(-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    obj = bpy.data.objects.new("ImportedObject", mesh)
    imported_collection.objects.link(obj)

    material = bpy.data.materials.new("ImportedMaterial")
    material.use_nodes = True
    image = bpy.data.images.new("ImportedTexture", width=4, height=4)
    texture_node = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture_node.image = image
    mesh.materials.append(material)

    loose_material = bpy.data.materials.new("ImportedLooseMaterial")
    assert_true(loose_material.users == 0, "Loose test material unexpectedly has users")

    bpy.data.objects.remove(obj, do_unlink=True)
    result = addon.batch_cleanup.cleanup_new_datablocks(snapshot)

    assert_true(result.get("complete") is True, f"Cleanup left post-import IDs: {result}")
    assert_true(result.get("leftoverCount") == 0, f"Unexpected cleanup leftovers: {result}")
    assert_true("ImportedMesh" not in bpy.data.meshes, "Imported Mesh leaked")
    assert_true("ImportedMaterial" not in bpy.data.materials, "Imported Material leaked")
    assert_true("ImportedLooseMaterial" not in bpy.data.materials, "Loose Material leaked")
    assert_true("ImportedTexture" not in bpy.data.images, "Imported Image leaked")
    assert_true("ImportedAssetCollection" not in bpy.data.collections, "Imported Collection leaked")
    assert_true(sentinel.name in bpy.data.images, "Pre-existing sentinel was incorrectly purged")


def test_partial_import_failure_cleanup(addon, sentinel):
    original_import_asset = addon.batch.import_asset

    def failing_import(_filepath, context):
        collection = bpy.data.collections.new("PartialFailureCollection")
        context.scene.collection.children.link(collection)

        mesh = bpy.data.meshes.new("PartialFailureMesh")
        mesh.from_pydata(
            [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
            [],
            [(0, 1, 2)],
        )
        mesh.update()
        obj = bpy.data.objects.new("PartialFailureObject", mesh)
        collection.objects.link(obj)

        material = bpy.data.materials.new("PartialFailureMaterial")
        image = bpy.data.images.new("PartialFailureImage", width=8, height=8)
        material.use_nodes = True
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        mesh.materials.append(material)

        raise RuntimeError("forced partial importer failure")

    addon.batch.import_asset = failing_import
    try:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                addon.batch.convert_asset(
                    bpy.context,
                    Path(tmp) / "forced.fbx",
                    Path(tmp) / "output",
                    "GENERIC",
                    export_glb=False,
                    export_baked_types=False,
                    export_thumbnail=False,
                    export_lods=False,
                )
            except RuntimeError as exc:
                assert_true("forced partial importer failure" in str(exc), f"Unexpected importer failure: {exc}")
            else:
                raise AssertionError("Forced partial importer failure did not propagate")
    finally:
        addon.batch.import_asset = original_import_asset

    assert_true("PartialFailureObject" not in bpy.data.objects, "Partial importer Object leaked")
    assert_true("PartialFailureMesh" not in bpy.data.meshes, "Partial importer Mesh leaked")
    assert_true("PartialFailureMaterial" not in bpy.data.materials, "Partial importer Material leaked")
    assert_true("PartialFailureImage" not in bpy.data.images, "Partial importer Image leaked")
    assert_true("PartialFailureCollection" not in bpy.data.collections, "Partial importer Collection leaked")
    assert_true(sentinel.name in bpy.data.images, "Pre-existing sentinel was removed after importer failure")


def test_cleanup_diagnostic_failure_is_nonfatal(addon, sentinel):
    original_import_asset = addon.batch.import_asset
    original_cleanup = addon.batch.cleanup_new_datablocks
    recovery_snapshot = addon.batch_cleanup.snapshot_datablocks()

    def simple_import(_filepath, context):
        mesh = bpy.data.meshes.new("CleanupWarningMesh")
        mesh.from_pydata(
            [(-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.0, 0.5, 0.8)],
            [],
            [(0, 1, 2)],
        )
        mesh.update()
        obj = bpy.data.objects.new("CleanupWarningObject", mesh)
        context.collection.objects.link(obj)
        return [obj]

    def broken_cleanup(_snapshot):
        raise RuntimeError("forced cleanup diagnostic failure")

    addon.batch.import_asset = simple_import
    addon.batch.cleanup_new_datablocks = broken_cleanup
    try:
        with tempfile.TemporaryDirectory() as tmp:
            result = addon.batch.convert_asset(
                bpy.context,
                Path(tmp) / "success.obj",
                Path(tmp) / "output",
                "GENERIC",
                export_glb=False,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
            assert_true(result.get("manifest"), f"Successful conversion result missing: {result}")
            assert_true(
                "forced cleanup diagnostic failure" in str(result.get("cleanup_warning", "")),
                f"Cleanup diagnostic warning missing: {result}",
            )
            assert_true(result.get("cleanup", {}).get("complete") is False, f"Cleanup state should be incomplete: {result}")
    finally:
        addon.batch.import_asset = original_import_asset
        addon.batch.cleanup_new_datablocks = original_cleanup

    recovery = original_cleanup(recovery_snapshot)
    assert_true(recovery.get("complete") is True, f"Recovery cleanup failed: {recovery}")
    assert_true("CleanupWarningObject" not in bpy.data.objects, "Cleanup-warning Object leaked")
    assert_true("CleanupWarningMesh" not in bpy.data.meshes, "Cleanup-warning Mesh leaked")
    assert_true(sentinel.name in bpy.data.images, "Pre-existing sentinel was removed by recovery cleanup")


def main():
    addon = load_addon()
    addon.register()
    sentinel = None
    try:
        clean_scene()

        # A global orphan purge would delete this zero-user image. Snapshot
        # cleanup must preserve it because it existed before the conversion.
        sentinel = bpy.data.images.new("BFC_KEEP_SENTINEL", width=2, height=2)

        test_direct_snapshot_cleanup(addon, sentinel)
        test_partial_import_failure_cleanup(addon, sentinel)
        test_cleanup_diagnostic_failure_is_nonfatal(addon, sentinel)

        print("CLEANUP_SMOKE: PASS")
    finally:
        if sentinel is not None and sentinel.name in bpy.data.images:
            bpy.data.images.remove(sentinel)
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
