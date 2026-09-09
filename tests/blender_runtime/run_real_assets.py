"""Run a real downloaded/vendor asset batch inside Blender and emit hardening metrics.

Example (PowerShell):

& 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe' `
  --background --factory-startup `
  --python tests/blender_runtime/run_real_assets.py -- `
  --input D:\\bim-assets `
  --output D:\\bim-family-library `
  --family-class AUTO_FOLDER
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_real_asset_hardening"


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


def blender_script_args():
    argv = list(sys.argv)
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


def parse_args():
    parser = argparse.ArgumentParser(description="Axion Family Creator real-asset hardening run")
    parser.add_argument("--input", required=True, help="Folder containing source .blend/.fbx/.obj/.glb/.gltf assets")
    parser.add_argument("--output", required=True, help="Library output folder")
    parser.add_argument(
        "--family-class",
        default="AUTO_FOLDER",
        help="Exact Family Class or AUTO_FOLDER (default)",
    )
    parser.add_argument("--non-recursive", action="store_true", help="Do not scan nested source folders")
    parser.add_argument("--no-glb", action="store_true", help="Skip GLB export")
    parser.add_argument("--no-baked-types", action="store_true", help="Skip saved Type GLB variants")
    parser.add_argument("--no-thumbnail", action="store_true", help="Skip preview thumbnail rendering")
    parser.add_argument("--no-auto-split", action="store_true", help="Disable conservative loose-part splitting")
    parser.add_argument("--stop-on-error", action="store_true", help="Abort on the first conversion failure")
    parser.add_argument("--max-loose-islands", type=int, default=32)
    return parser.parse_args(blender_script_args())


def main():
    args = parse_args()
    input_directory = Path(args.input).expanduser().resolve()
    output_directory = Path(args.output).expanduser().resolve()
    if not input_directory.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)

    addon = load_addon()
    batch_module = importlib.import_module(f"{ADDON_NAME}.batch")
    hardening_module = importlib.import_module(f"{ADDON_NAME}.hardening")
    addon.register()
    try:
        report = batch_module.batch_convert_directory(
            bpy.context,
            input_directory,
            output_directory,
            args.family_class,
            recursive=not args.non_recursive,
            export_glb=not args.no_glb,
            export_baked_types=not args.no_baked_types,
            export_thumbnail=not args.no_thumbnail,
            continue_on_error=not args.stop_on_error,
            auto_split_loose=not args.no_auto_split,
            max_loose_islands=max(2, int(args.max_loose_islands)),
        )
        hardening = hardening_module.build_hardening_report(report)
        hardening_path = output_directory / "hardening-report.json"
        hardening_path.write_text(json.dumps(hardening, indent=2, ensure_ascii=False), encoding="utf-8")

        summary = hardening["summary"]
        print("\n=== Axion Real Asset Hardening ===")
        print(f"Input: {input_directory}")
        print(f"Output: {output_directory}")
        print(f"Discovered: {summary['discovered']}")
        print(f"Converted: {summary['converted']}")
        print(f"Failed: {summary['failed']}")
        print(f"Automatic ready: {summary['automaticReady']}")
        print(f"Needs review: {summary['needsReview']}")
        print(f"Conversion success rate: {summary['conversionSuccessRate']:.1%}")
        print(f"Auto acceptance rate: {summary['autoAcceptanceRate']:.1%}")
        print(f"Hardening report: {hardening_path}")
        if hardening.get("reviewReasons"):
            print("Top review reasons:")
            for item in hardening["reviewReasons"][:10]:
                print(f"  {item['count']:>4}  {item['reason']}")
    finally:
        try:
            addon.unregister()
        except Exception:
            pass


if __name__ == "__main__":
    main()
