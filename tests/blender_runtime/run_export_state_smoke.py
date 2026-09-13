"""GPU-free Blender smoke for state-safe transactional family export.

Checks:
- selection and active object are restored;
- hide_viewport, hide_render and hide_set are restored;
- primary GLB exists on success;
- a forced pre-commit GLB failure leaves an empty destination untouched;
- a failed overwrite preserves an existing valid manifest/GLB byte-for-byte;
- a forced commit-time failure rolls back the previous package;
- a successful re-export prunes obsolete manifest-managed assets only;
- renaming a family in the same destination replaces the old manifest contract;
- ambiguous destinations with multiple root manifests are rejected.

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


def package_bytes(manifest, glb):
    return Path(manifest).read_bytes(), Path(glb).read_bytes()


def force_primary_failure(addon, root, output):
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
                output,
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


def force_commit_failure(addon, root, output):
    original_replace = addon.typed.os.replace
    tripped = {"value": False}

    def flaky_replace(source, target):
        source_path = Path(source)
        target_path = Path(target)
        if (
            not tripped["value"]
            and "package" in source_path.parts
            and source_path.suffix.lower() == ".glb"
            and target_path.parent == Path(output)
        ):
            tripped["value"] = True
            raise OSError("forced package commit failure")
        return original_replace(source, target)

    addon.typed.os.replace = flaky_replace
    try:
        try:
            addon.typed.export_typed_family(
                root,
                output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
        except OSError as exc:
            assert_true("forced package commit failure" in str(exc), f"Unexpected commit failure: {exc}")
        else:
            raise AssertionError("Forced package commit failure did not propagate")
        assert_true(tripped["value"], "Commit failure hook never reached staged GLB promotion")
    finally:
        addon.typed.os.replace = original_replace


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

            old_manifest_bytes, old_glb_bytes = package_bytes(manifest, glb)

            force_primary_failure(addon, root, output)
            assert_true(Path(manifest).read_bytes() == old_manifest_bytes, "Failed overwrite changed old manifest")
            assert_true(Path(glb).read_bytes() == old_glb_bytes, "Failed overwrite changed old GLB")

            force_commit_failure(addon, root, output)
            assert_true(Path(manifest).read_bytes() == old_manifest_bytes, "Commit rollback changed old manifest")
            assert_true(Path(glb).read_bytes() == old_glb_bytes, "Commit rollback changed old GLB")

            failure_output = Path(tmp) / "forced-failure"
            force_primary_failure(addon, root, failure_output)
            assert_true(not failure_output.exists(), "Failed new export left a destination directory")
            assert_true(
                not list(Path(tmp).glob(".bfc-package-*")),
                "Temporary staging directory leaked after export failure",
            )

            # Managed-asset pruning: the first export owns a GLB. The second
            # manifest intentionally omits geometry. The old GLB must disappear,
            # but an unrelated user file beside the package must survive.
            prune_output = Path(tmp) / "managed-prune"
            prune_manifest, prune_glb = addon.typed.export_typed_family(
                root,
                prune_output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
            assert_true(prune_glb is not None and Path(prune_glb).is_file(), "Prune fixture GLB missing")
            notes = prune_output / "notes.txt"
            notes.write_text("keep me", encoding="utf-8")

            new_manifest, new_glb = addon.typed.export_typed_family(
                root,
                prune_output,
                export_glb=False,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
            assert_true(Path(new_manifest).is_file(), "Manifest missing after managed pruning")
            assert_true(new_glb is None, "GLB unexpectedly returned after export_glb=False")
            assert_true(not Path(prune_glb).exists(), "Obsolete manifest-managed GLB was not pruned")
            assert_true(notes.is_file(), "Unrelated package-side file was deleted")
            assert_true(notes.read_text(encoding="utf-8") == "keep me", "Unrelated file contents changed")

            # Manifest rename: manual export uses the user-selected directory
            # directly. If the family name changes, the old root manifest and
            # its managed GLB must be replaced rather than leaving two contracts.
            rename_output = Path(tmp) / "manifest-rename"
            root.bfc_family_name = "Export State"
            old_named_manifest, old_named_glb = addon.typed.export_typed_family(
                root,
                rename_output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )
            rename_notes = rename_output / "notes.txt"
            rename_notes.write_text("keep renamed package notes", encoding="utf-8")

            root.bfc_family_name = "Export Renamed"
            renamed_manifest, renamed_glb = addon.typed.export_typed_family(
                root,
                rename_output,
                export_glb=True,
                export_baked_types=False,
                export_thumbnail=False,
                export_lods=False,
            )

            root_manifests = list(rename_output.glob("*.family.json"))
            assert_true(len(root_manifests) == 1, f"Rename left multiple manifests: {root_manifests}")
            assert_true(root_manifests[0] == Path(renamed_manifest), "Renamed manifest is not the sole contract")
            assert_true(not Path(old_named_manifest).exists(), "Old renamed manifest was not removed")
            assert_true(not Path(old_named_glb).exists(), "Old renamed GLB was not removed")
            assert_true(renamed_glb is not None and Path(renamed_glb).is_file(), "Renamed GLB missing")
            assert_true(rename_notes.is_file(), "Unrelated file was removed during manifest rename")

            # Ambiguous destination safety: two pre-existing root manifests are
            # not safe to infer ownership from, so overwrite must be rejected.
            extra_manifest = rename_output / "ambiguous.family.json"
            extra_manifest.write_text("{}", encoding="utf-8")
            renamed_bytes = Path(renamed_manifest).read_bytes()
            try:
                addon.typed.export_typed_family(
                    root,
                    rename_output,
                    export_glb=False,
                    export_baked_types=False,
                    export_thumbnail=False,
                    export_lods=False,
                )
            except RuntimeError as exc:
                assert_true("multiple root manifests" in str(exc), f"Unexpected ambiguity error: {exc}")
            else:
                raise AssertionError("Ambiguous multi-manifest destination was not rejected")
            assert_true(Path(renamed_manifest).read_bytes() == renamed_bytes, "Ambiguous overwrite changed valid manifest")
            extra_manifest.unlink()
            root.bfc_family_name = "Export State"

        print("EXPORT_STATE_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
