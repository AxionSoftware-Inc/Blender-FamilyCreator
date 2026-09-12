"""GPU-free Blender smoke for state-safe and transactional primary GLB export.

Checks:
- selection and active object are restored;
- hide_viewport, hide_render and hide_set are restored;
- primary GLB exists on success;
- a forced primary GLB failure removes the base manifest and partial GLB.

Run from repository root:

blender --background --factory-startup --python tests/blender_runtime/run_export_state_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_export_state_smoke"


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


def hide_get(obj):
    try:
        return bool(obj.hide_get())
    except Exception:
        return False


def main():
    addon = load_addon()
    addon.register()
    try:
        clean_scene()

        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.5))
        member = bpy.context.object
        member.name = "HiddenMember"
        root = addon.typed.create_typed_family(bpy.context, [member], "Export State", "GENERIC")
        root["bfc_family_id"] = "axion:generic:export-state"

        bpy.ops.mesh.primitive_cube_add(size=0.25, location=(3.0, 0.0, 0.0))
        sentinel = bpy.context.object
        sentinel.name = "SelectionSentinel"

        bpy.ops.object.select_all(action="DESELECT")
        sentinel.select_set(True)
        bpy.context.view_layer.objects.active = sentinel

        member.hide_render = True
        member.hide_viewport = False
        member.hide_set(True)
        expected = {
            "hideRender": True,
            "hideViewport": False,
            "hideSet": True,
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "success"
            manifest, glb = addon.typed.export_typed_family(
                root,
                output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
            assert_true(Path(manifest).is_file(), "Successful export manifest missing")
            assert_true(glb is not None and Path(glb).is_file(), "Successful primary GLB missing")

            selected_names = {obj.name for obj in bpy.context.selected_objects}
            assert_true(selected_names == {"SelectionSentinel"}, f"Selection was not restored: {selected_names}")
            assert_true(bpy.context.view_layer.objects.active == sentinel, "Active object was not restored")
            assert_true(bool(member.hide_render) == expected["hideRender"], "hide_render changed after export")
            assert_true(bool(member.hide_viewport) == expected["hideViewport"], "hide_viewport changed after export")
            assert_true(hide_get(member) == expected["hideSet"], "hide_set changed after export")

            failure_output = Path(tmp) / "forced-failure"
            original_export = addon.typed.export_glb_geometry

            def fail_primary(_root, filepath):
                filepath = Path(filepath)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(b"partial")
                raise RuntimeError("forced primary GLB failure")

            addon.typed.export_glb_geometry = fail_primary
            try:
                try:
                    addon.typed.export_typed_family(
                        root,
                        failure_output,
                        export_glb=True,
                        export_baked_types=False,
                        export_thumbnail=False,
                        export_lods=False,
                    )
                except RuntimeError as exc:
                    assert_true("forced primary GLB failure" in str(exc), f"Unexpected failure: {exc}")
                else:
                    raise AssertionError("Forced primary GLB failure did not propagate")
            finally:
                addon.typed.export_glb_geometry = original_export

            assert_true(not list(failure_output.glob("*.family.json")), "Failed export left a family manifest")
            assert_true(not list(failure_output.glob("*.glb")), "Failed export left a partial primary GLB")

        print("EXPORT_STATE_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
