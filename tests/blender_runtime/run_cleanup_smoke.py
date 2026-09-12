"""GPU-free Blender smoke test for leak-resistant batch datablock cleanup.

Verifies that post-snapshot Mesh -> Material -> Image dependencies and imported
Collections are removed without touching a pre-existing zero-user sentinel.

Run from repository root:

blender --background --factory-startup --python tests/blender_runtime/run_cleanup_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
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


def main():
    addon = load_addon()
    addon.register()
    sentinel = None
    try:
        clean_scene()

        # This zero-user image existed before the asset import. A global orphan
        # purge would delete it; snapshot cleanup must preserve it.
        sentinel = bpy.data.images.new("BFC_KEEP_SENTINEL", width=2, height=2)
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

        # Simulate the batch object's child-first cleanup. The remaining ID
        # dependency chain must be resolved by cleanup_new_datablocks().
        bpy.data.objects.remove(obj, do_unlink=True)
        result = addon.batch_cleanup.cleanup_new_datablocks(snapshot)

        assert_true(result.get("complete") is True, f"Cleanup left post-import IDs: {result}")
        assert_true(result.get("leftoverCount") == 0, f"Unexpected cleanup leftovers: {result}")
        assert_true("ImportedMesh" not in bpy.data.meshes, "Imported Mesh leaked")
        assert_true("ImportedMaterial" not in bpy.data.materials, "Imported Material leaked")
        assert_true("ImportedLooseMaterial" not in bpy.data.materials, "Loose Material leaked")
        assert_true("ImportedTexture" not in bpy.data.images, "Imported Image leaked")
        assert_true("ImportedAssetCollection" not in bpy.data.collections, "Imported Collection leaked")
        assert_true("BFC_KEEP_SENTINEL" in bpy.data.images, "Pre-existing sentinel was incorrectly purged")

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
