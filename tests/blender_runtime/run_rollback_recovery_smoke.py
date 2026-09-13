"""GPU-free smoke for preserving recovery files after incomplete rollback.

This exercises the outer export lifecycle without requiring a real filesystem
permission failure: the commit stage is replaced with a deterministic fixture
that creates a backup marker and raises PackageRollbackError. export_typed_family
must preserve that recovery directory instead of deleting it during cleanup.

Run from repository root with Blender 5.2:

blender --background --factory-startup --python tests/blender_runtime/run_rollback_recovery_smoke.py
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_rollback_recovery_smoke"


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
    recovery_root = None
    original_commit = addon.typed._commit_staged_package
    try:
        clean_scene()
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        member = bpy.context.object
        root = addon.typed.create_typed_family(
            bpy.context,
            [member],
            "Rollback Recovery",
            "GENERIC",
        )
        root["bfc_family_id"] = "axion:generic:rollback-recovery"

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "family"

            def incomplete_commit(stage_directory, _destination_directory):
                nonlocal recovery_root
                recovery_root = Path(stage_directory).parent
                backup = recovery_root / "__bfc_backup__" / "rollback-recovery.glb"
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(b"previous-valid-package-bytes")
                raise addon.typed.PackageRollbackError(
                    f"forced incomplete rollback; recovery files preserved at {recovery_root}",
                    recovery_directory=recovery_root,
                )

            addon.typed._commit_staged_package = incomplete_commit
            try:
                addon.typed.export_typed_family(
                    root,
                    output,
                    export_glb=False,
                    export_baked_types=False,
                    export_thumbnail=False,
                    export_lods=False,
                )
            except addon.typed.PackageRollbackError as exc:
                assert_true(exc.recovery_directory == recovery_root, "Recovery path was not propagated")
                assert_true(recovery_root is not None and recovery_root.is_dir(), "Recovery directory was deleted")
                marker = recovery_root / "__bfc_backup__" / "rollback-recovery.glb"
                assert_true(marker.read_bytes() == b"previous-valid-package-bytes", "Backup marker was not preserved")
                assert_true("recovery files preserved" in str(exc), "Recovery path message is missing")
            else:
                raise AssertionError("PackageRollbackError did not propagate")
            finally:
                addon.typed._commit_staged_package = original_commit

            assert_true(recovery_root is not None and recovery_root.exists(), "Recovery root vanished after export")
            shutil.rmtree(recovery_root, ignore_errors=True)
            recovery_root = None

        print("ROLLBACK_RECOVERY_SMOKE: PASS")
    finally:
        addon.typed._commit_staged_package = original_commit
        if recovery_root is not None:
            shutil.rmtree(recovery_root, ignore_errors=True)
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
