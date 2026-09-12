"""Headless Blender entry point for Axion Family Creator batch conversion.

Example:

blender --background --factory-startup --python batch_cli.py -- \
  --input D:\\assets \
  --output D:\\family-library \
  --class AUTO_FOLDER \
  --recursive \
  --lods \
  --no-thumbnails
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
        "mobileBudgetStatusCounts": report.get("mobile_budget_status_counts", {}),
        "resolvedClassCounts": report.get("resolved_class_counts", {}),
        "batchReport": report.get("report_path"),
        "reviewQueue": report.get("review_queue_path"),
        "libraryIndex": report.get("library_index_path"),
        "libraryFamilyCount": report.get("library_family_count"),
        "libraryMissingAssetCount": report.get("library_missing_asset_count"),
        "libraryAssetWarningCount": report.get("library_asset_warning_count"),
        "libraryIndexError": report.get("library_index_error"),
        "libraryAudit": report.get("library_audit_path"),
        "libraryAuditComplete": report.get("library_audit_complete"),
        "libraryAuditWarningCount": report.get("library_audit_warning_count"),
        "libraryAuditError": report.get("library_audit_error"),
        "aborted": bool(report.get("aborted", False)),
    }


def main():
    args = parse_args()
    input_directory = Path(args.input).expanduser().resolve()
    output_directory = Path(args.output).expanduser().resolve()
    if not input_directory.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)

    addon = load_addon()
    batch_module = importlib.import_module(f"{ADDON_NAME}.batch")
    addon.register()
    try:
        report = batch_module.batch_convert_directory(
            bpy.context,
            input_directory,
            output_directory,
            str(args.family_class).upper(),
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
        print(f"Mobile budgets: {summary['mobileBudgetStatusCounts']}")
        print(f"Library families: {summary['libraryFamilyCount']}")
        print(f"Library missing assets: {summary['libraryMissingAssetCount']}")
        print(f"Library audit complete: {summary['libraryAuditComplete']}")
        print(f"Batch report: {summary['batchReport']}")
        print(f"Library audit: {summary['libraryAudit']}")

        if args.json_summary:
            summary_path = Path(args.json_summary).expanduser().resolve()
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Summary: {summary_path}")

        if summary["failed"] and args.stop_on_error:
            raise SystemExit(2)
    finally:
        try:
            addon.unregister()
        except Exception:
            pass


if __name__ == "__main__":
    main()
