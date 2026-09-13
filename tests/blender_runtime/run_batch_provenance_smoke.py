"""GPU-free Blender smoke for repeated-batch source provenance.

Checks:
- a successful run writes the multi-scope batch-source-index registry;
- removing/renaming a source on the same scoped rerun reports a stale package
  without deleting it automatically;
- a catalog-build failure preserves the previous canonical source baseline;
- alternating another input scope does not erase the first scope's provenance;
- a current refresh failure preserves the old valid package and reports it as a
  failed-refresh retained package;
- rejected catalog manifests preserve the previous provenance baseline;
- a corrupt canonical source registry is reported and preserved byte-for-byte
  rather than silently replaced by the next successful conversion.

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
            other_source = root / "source-other"
            output = root / "library"
            asset_a = source / "a.blend"
            asset_b = source / "b.blend"
            other_asset = other_source / "other.blend"
            write_simple_blend(asset_a, "AssetA")
            write_simple_blend(asset_b, "AssetB")
            write_simple_blend(other_asset, "OtherAsset")

            first = run_batch(addon, source, output)
            assert_true(first.get("failed") == 0, f"Initial provenance batch failed: {first.get('errors')}")
            assert_true(first.get("converted") == 2, f"Expected two initial conversions: {first}")
            assert_true(first.get("source_index_updated") is True, f"Source index not written: {first}")
            source_index_path = Path(first.get("source_index_path"))
            assert_true(source_index_path.is_file(), "batch-source-index.json missing")
            first_index = json.loads(source_index_path.read_text(encoding="utf-8"))
            assert_true(first_index.get("schemaVersion") == 2, f"Expected source registry v2: {first_index}")
            assert_true(first_index.get("scopeCount") == 1, f"Unexpected first scope count: {first_index}")
            assert_true(
                (first_index.get("latestScope") or {}).get("sourceCount") == 2,
                f"Unexpected first source snapshot: {first_index}",
            )

            asset_b.unlink()
            second = run_batch(addon, source, output)
            assert_true(second.get("failed") == 0, f"Second provenance batch failed: {second.get('errors')}")
            assert_true(second.get("source_index_comparable") is True, f"Same-root source indexes did not compare: {second}")
            assert_true(second.get("stale_output_count") == 1, f"Removed source was not flagged stale: {second}")
            stale_ids = second.get("stale_output_family_ids", [])
            assert_true(stale_ids == ["axion:generic:b"], f"Unexpected stale package IDs: {stale_ids}")
            stale_manifest = output / "generic" / "b" / "b.family.json"
            assert_true(stale_manifest.is_file(), "Stale package was deleted automatically")

            baseline_bytes = source_index_path.read_bytes()
            original_catalog_builder = addon.batch.build_library_index

            def failing_catalog(_output):
                raise RuntimeError("forced catalog build failure")

            addon.batch.build_library_index = failing_catalog
            try:
                catalog_failure = run_batch(addon, source, output)
            finally:
                addon.batch.build_library_index = original_catalog_builder

            assert_true(
                "forced catalog build failure" in str(catalog_failure.get("library_index_error", "")),
                f"Catalog failure was not reported: {catalog_failure}",
            )
            assert_true(
                catalog_failure.get("source_index_updated") is False,
                f"Source baseline changed despite missing catalog: {catalog_failure}",
            )
            assert_true(
                catalog_failure.get("source_index_diagnostic_skipped_reason") == "LIBRARY_INDEX_UNAVAILABLE",
                f"Unexpected source diagnostic state: {catalog_failure}",
            )
            assert_true(source_index_path.read_bytes() == baseline_bytes, "Catalog failure overwrote source registry")

            other = run_batch(addon, other_source, output)
            assert_true(other.get("failed") == 0, f"Alternate scope batch failed: {other.get('errors')}")
            assert_true(other.get("source_index_updated") is True, f"Alternate scope was not persisted: {other}")
            registry = json.loads(source_index_path.read_text(encoding="utf-8"))
            assert_true(registry.get("scopeCount") == 2, f"Alternate scope erased provenance: {registry}")

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

            assert_true(third.get("source_index_comparable") is True, f"Original scope baseline was lost: {third}")
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

            final_registry = json.loads(source_index_path.read_text(encoding="utf-8"))
            assert_true(final_registry.get("scopeCount") == 2, f"Final registry lost a scope: {final_registry}")

            # A structurally invalid pre-existing package makes catalog identity
            # incomplete. Do not advance the canonical source baseline from such
            # a run even if the current source conversion itself succeeds.
            rejected_baseline = source_index_path.read_bytes()
            invalid_package = output / "broken"
            invalid_package.mkdir(parents=True, exist_ok=True)
            invalid_manifest = invalid_package / "broken.family.json"
            invalid_manifest.write_text(
                json.dumps({
                    "schema": "axion.family",
                    "schemaVersion": 2,
                    "familyId": "axion:generic:broken",
                    "familyKind": "GENERIC",
                    "name": "Broken",
                }),
                encoding="utf-8",
            )
            rejected_run = run_batch(addon, source, output)
            assert_true(rejected_run.get("failed") == 0, f"Conversion should still succeed: {rejected_run}")
            assert_true(
                rejected_run.get("library_rejected_manifest_count") == 1,
                f"Invalid package was not rejected by catalog: {rejected_run}",
            )
            assert_true(
                rejected_run.get("source_index_updated") is False,
                f"Rejected catalog unexpectedly advanced source provenance: {rejected_run}",
            )
            assert_true(
                rejected_run.get("source_index_diagnostic_skipped_reason") == "LIBRARY_INDEX_REJECTED_MANIFESTS",
                f"Rejected catalog skip reason missing: {rejected_run}",
            )
            assert_true(
                source_index_path.read_bytes() == rejected_baseline,
                "Rejected catalog run overwrote source registry",
            )
            invalid_manifest.unlink()
            invalid_package.rmdir()

            # Corrupt the canonical registry itself. The next conversion may
            # still refresh family packages, but provenance must not be silently
            # replaced because doing so would destroy the only evidence needed
            # for safe stale-output comparisons.
            corrupt_bytes = b'{"schema":"axion.family.batch-source-index","schemaVersion":2,bad-json'
            source_index_path.write_bytes(corrupt_bytes)
            corrupt_run = run_batch(addon, source, output)
            assert_true(corrupt_run.get("failed") == 0, f"Conversion should still succeed: {corrupt_run}")
            assert_true(
                corrupt_run.get("source_index_updated") is False,
                f"Corrupt provenance was unexpectedly overwritten: {corrupt_run}",
            )
            assert_true(
                corrupt_run.get("source_index_diagnostic_skipped_reason") == "SOURCE_INDEX_INVALID",
                f"Corrupt provenance was not explicitly diagnosed: {corrupt_run}",
            )
            assert_true(
                "Could not read existing" in str(corrupt_run.get("source_index_error", "")),
                f"Corrupt provenance error missing: {corrupt_run}",
            )
            assert_true(
                source_index_path.read_bytes() == corrupt_bytes,
                "Corrupt canonical provenance was silently replaced",
            )

        print("BATCH_PROVENANCE_SMOKE: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
