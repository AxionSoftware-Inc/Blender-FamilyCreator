"""Headless Blender entry point for Axion Family Creator batch conversion.

Example:

blender --background --factory-startup --python batch_cli.py -- \
  --input D:\\assets \
  --output D:\\family-library \
  --class AUTO_FOLDER \
  --recursive \
  --lods \
  --no-thumbnails \
  --strict
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parent
ADDON_NAME = "bfc_headless_batch"


def _script_args():
    argv = list(sys.argv)
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


def parse_args():
    parser = argparse.ArgumentParser(description="Axion Family Creator headless batch converter")
    parser.add_argument("--input", required=True, help="Source asset folder")
    parser.add_argument("--output", required=True, help="Output family-library folder")
    parser.add_argument("--class", dest="family_class", default="AUTO_FOLDER", help="Exact Family Class or AUTO_FOLDER")
    recursion = parser.add_mutually_exclusive_group()
    recursion.add_argument("--recursive", action="store_true", default=True, help="Scan nested folders (default)")
    recursion.add_argument("--non-recursive", action="store_false", dest="recursive", help="Scan only the input folder")
    parser.add_argument("--no-glb", action="store_true", help="Skip GLB export")
    parser.add_argument("--no-baked-types", action="store_true", help="Skip saved Type variants")
    parser.add_argument("--no-thumbnails", "--no-thumbnail", action="store_true", help="Skip preview rendering")
    parser.add_argument("--lods", action="store_true", help="Generate non-destructive mobile LOD1/LOD2 derivatives")
    parser.add_argument("--no-auto-split", action="store_true", help="Disable conservative loose-part splitting")
    parser.add_argument("--max-loose-islands", type=int, default=32)
    parser.add_argument("--stop-on-error", action="store_true", help="Abort after the first failed asset")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero if conversion failures, cleanup leftovers, rejected manifests, "
            "stale/failed-refresh packages, source-index errors, missing library assets or "
            "an incomplete library audit remain"
        ),
    )
    parser.add_argument("--json-summary", help="Optional compact summary output path")
    return parser.parse_args(_script_args())


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


def _summary(report):
    return {
        "input": report.get("input_directory"),
        "output": report.get("output_directory"),
        "requestedFamilyClass": report.get("family_kind"),
        "discovered": int(report.get("discovered", 0) or 0),
        "converted": int(report.get("converted", 0) or 0),
        "failed": int(report.get("failed", 0) or 0),
        "automaticReady": int(report.get("ready", 0) or 0),
        "needsReview": int(report.get("needs_review", 0) or 0),
        "thumbnailWarnings": int(report.get("thumbnail_warnings", 0) or 0),
        "lodWarnings": int(report.get("lod_warnings", 0) or 0),
        "cleanupWarnings": int(report.get("cleanup_warnings", 0) or 0),
        "cleanupLeftoverDatablocks": int(report.get("cleanup_leftover_datablocks", 0) or 0),
        "staleOutputCount": int(report.get("stale_output_count", 0) or 0),
        "staleOutputFamilyIds": list(report.get("stale_output_family_ids", ()) or ()),
        "failedRefreshPackageCount": int(report.get("failed_refresh_package_count", 0) or 0),
        "failedRefreshFamilyIds": list(report.get("failed_refresh_family_ids", ()) or ()),
        "sourceIndexComparable": bool(report.get("source_index_comparable", False)),
        "sourceIndexUpdated": bool(report.get("source_index_updated", False)),
        "sourceIndex": report.get("source_index_path"),
        "sourceIndexError": report.get("source_index_error"),
        "mobileBudgetStatusCounts": report.get("mobile_budget_status_counts", {}),
        "resolvedClassCounts": report.get("resolved_class_counts", {}),
        "batchReport": report.get("report_path"),
        "reviewQueue": report.get("review_queue_path"),
        "libraryIndex": report.get("library_index_path"),
        "libraryFamilyCount": report.get("library_family_count"),
        "libraryMissingAssetCount": report.get("library_missing_asset_count"),
        "libraryAssetWarningCount": report.get("library_asset_warning_count"),
        "libraryRejectedManifestCount": int(report.get("library_rejected_manifest_count", 0) or 0),
        "libraryIndexError": report.get("library_index_error"),
        "libraryAudit": report.get("library_audit_path"),
        "libraryAuditComplete": report.get("library_audit_complete"),
        "libraryAuditWarningCount": report.get("library_audit_warning_count"),
        "libraryAuditError": report.get("library_audit_error"),
        "aborted": bool(report.get("aborted", False)),
    }


def _strict_failures(summary):
    failures = []
    if summary["failed"]:
        failures.append(f"{summary['failed']} conversion failure(s)")
    if summary["cleanupWarnings"] or summary["cleanupLeftoverDatablocks"]:
        failures.append(
            f"cleanup warnings={summary['cleanupWarnings']}, "
            f"leftover datablocks={summary['cleanupLeftoverDatablocks']}"
        )
    if summary["staleOutputCount"]:
        failures.append(f"{summary['staleOutputCount']} stale output package(s) from removed/renamed sources")
    if summary["failedRefreshPackageCount"]:
        failures.append(
            f"{summary['failedRefreshPackageCount']} package(s) retained from an older successful run "
            "because the current refresh failed"
        )
    if summary.get("sourceIndexError"):
        failures.append(f"batch source index error: {summary['sourceIndexError']}")
    rejected = summary.get("libraryRejectedManifestCount")
    if isinstance(rejected, int) and rejected > 0:
        failures.append(f"{rejected} rejected library manifest(s)")
    missing = summary.get("libraryMissingAssetCount")
    if isinstance(missing, int) and missing > 0:
        failures.append(f"{missing} missing library asset(s)")
    if summary.get("libraryIndexError"):
        failures.append(f"library index error: {summary['libraryIndexError']}")
    if summary.get("libraryAuditError"):
        failures.append(f"library audit error: {summary['libraryAuditError']}")
    if summary.get("libraryAuditComplete") is False:
        failures.append(
            f"library audit incomplete ({summary.get('libraryAuditWarningCount', 0)} warning(s))"
        )
    return failures


def main():
    args = parse_args()
    input_directory = Path(args.input).expanduser().resolve()
    output_directory = Path(args.output).expanduser().resolve()
    if not input_directory.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)

    addon = load_addon()
    batch_module = importlib.import_module(f"{ADDON_NAME}.batch")
    family_types_module = importlib.import_module(f"{ADDON_NAME}.family_types")
    requested_class = str(args.family_class).strip().upper()
    allowed_classes = set(family_types_module.FAMILY_TYPES)
    if requested_class != batch_module.AUTO_FOLDER_CLASS and requested_class not in allowed_classes:
        choices = ", ".join([batch_module.AUTO_FOLDER_CLASS] + sorted(allowed_classes))
        raise SystemExit(f"Unknown Family Class '{requested_class}'. Allowed: {choices}")

    addon.register()
    try:
        report = batch_module.batch_convert_directory(
            bpy.context,
            input_directory,
            output_directory,
            requested_class,
            recursive=bool(args.recursive),
            export_glb=not args.no_glb,
            export_baked_types=not args.no_baked_types,
            export_thumbnail=not args.no_thumbnails,
            export_lods=bool(args.lods) and not args.no_glb,
            continue_on_error=not args.stop_on_error,
            auto_split_loose=not args.no_auto_split,
            max_loose_islands=max(2, int(args.max_loose_islands)),
        )
        summary = _summary(report)

        print("\n=== Axion Headless Batch ===")
        print(f"Input: {input_directory}")
        print(f"Output: {output_directory}")
        print(f"Discovered: {summary['discovered']}")
        print(f"Converted: {summary['converted']}")
        print(f"Failed: {summary['failed']}")
        print(f"Automatic ready: {summary['automaticReady']}")
        print(f"Needs review: {summary['needsReview']}")
        print(f"LOD warnings: {summary['lodWarnings']}")
        print(f"Cleanup warnings: {summary['cleanupWarnings']}")
        print(f"Cleanup leftover datablocks: {summary['cleanupLeftoverDatablocks']}")
        print(f"Stale output packages: {summary['staleOutputCount']}")
        print(f"Failed-refresh retained packages: {summary['failedRefreshPackageCount']}")
        print(f"Mobile budgets: {summary['mobileBudgetStatusCounts']}")
        print(f"Library families: {summary['libraryFamilyCount']}")
        print(f"Library rejected manifests: {summary['libraryRejectedManifestCount']}")
        print(f"Library missing assets: {summary['libraryMissingAssetCount']}")
        print(f"Library audit complete: {summary['libraryAuditComplete']}")
        print(f"Batch source index: {summary['sourceIndex']}")
        print(f"Batch report: {summary['batchReport']}")
        print(f"Library audit: {summary['libraryAudit']}")

        if summary["staleOutputFamilyIds"]:
            print("Stale package IDs:")
            for family_id in summary["staleOutputFamilyIds"]:
                print(f"- {family_id}")
        if summary["failedRefreshFamilyIds"]:
            print("Failed-refresh retained package IDs:")
            for family_id in summary["failedRefreshFamilyIds"]:
                print(f"- {family_id}")

        if args.json_summary:
            summary_path = Path(args.json_summary).expanduser().resolve()
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Summary: {summary_path}")

        if summary["failed"] and args.stop_on_error:
            raise SystemExit(2)
        if args.strict:
            strict_failures = _strict_failures(summary)
            if strict_failures:
                print("STRICT CHECK FAILED:")
                for failure in strict_failures:
                    print(f"- {failure}")
                raise SystemExit(3)
            print("Strict integrity check: PASS")
    finally:
        try:
            addon.unregister()
        except Exception:
            pass


if __name__ == "__main__":
    main()
