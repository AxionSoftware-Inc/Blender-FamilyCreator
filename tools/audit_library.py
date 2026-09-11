"""Audit an exported Axion family library without opening Blender."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from library_audit import write_library_audit


def parse_args():
    parser = argparse.ArgumentParser(description="Audit Axion family-library asset integrity")
    parser.add_argument("--library", required=True, help="Exported family library root")
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a non-zero exit code when any warning is found",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.library).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Library directory does not exist: {root}")

    if args.output:
        output = Path(args.output).expanduser().resolve()
        payload = write_library_audit(root)[1]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        path = output
    else:
        path, payload = write_library_audit(root)

    print("=== Axion Library Audit ===")
    print(f"Library: {root}")
    print(f"Manifests: {payload['manifestCount']}")
    print(f"Valid families: {payload['validFamilyCount']}")
    print(f"Families with asset warnings: {payload['familiesWithAssetWarnings']}")
    print(f"Missing assets: {payload['missingAssetCount']}")
    print(f"Unsafe URIs: {payload['unsafeUriCount']}")
    print(f"Warnings: {payload['warningCount']}")
    print(f"Complete: {'YES' if payload['complete'] else 'NO'}")
    print(f"Report: {path}")

    for code, count in payload.get("warningCounts", {}).items():
        print(f"  {count:>4}  {code}")

    if args.fail_on_warning and not payload["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
