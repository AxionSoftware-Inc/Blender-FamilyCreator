"""Inspect Blender asset object types without rendering or exporting.

Run with Blender in background mode, for example:

    blender --background --factory-startup --python tools/inspect_blend_geometry.py -- asset.blend

Multiple .blend paths may be supplied. The tool only loads object datablocks long
enough to report their types and collection-instance structure. It never renders,
exports, modifies the source file, or saves a .blend file.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import bpy


SUPPORTED_FAMILY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}
_LIBRARY_DATABLOCK_NAMES = (
    "objects",
    "collections",
    "meshes",
    "curves",
    "hair_curves",
    "grease_pencils",
    "pointclouds",
    "volumes",
)


def _script_args():
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1 :]


def _count_library_datablocks(data_from):
    counts = {}
    for name in _LIBRARY_DATABLOCK_NAMES:
        values = getattr(data_from, name, None)
        if values is None:
            continue
        try:
            counts[name] = len(values)
        except TypeError:
            continue
    return dict(sorted(counts.items()))


def inspect_blend(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"File does not exist: {path}")
    if path.suffix.lower() != ".blend":
        raise ValueError(f"Expected a .blend file: {path}")

    with bpy.data.libraries.load(str(path), link=False) as (data_from, data_to):
        source_object_names = list(data_from.objects)
        library_counts = _count_library_datablocks(data_from)
        data_to.objects = source_object_names

    imported = [obj for obj in data_to.objects if obj is not None]
    type_counts = Counter(str(obj.type) for obj in imported)
    supported = [obj for obj in imported if obj.type in SUPPORTED_FAMILY_TYPES]
    collection_instances = [
        obj
        for obj in imported
        if getattr(obj, "instance_collection", None) is not None
    ]

    objects = []
    for obj in imported:
        instance_collection = getattr(obj, "instance_collection", None)
        objects.append({
            "name": str(obj.name),
            "type": str(obj.type),
            "dataType": type(getattr(obj, "data", None)).__name__ if getattr(obj, "data", None) is not None else None,
            "instanceCollection": str(instance_collection.name) if instance_collection is not None else None,
            "modifierTypes": [str(modifier.type) for modifier in getattr(obj, "modifiers", ())],
        })

    return {
        "source": str(path),
        "sourceObjectCount": len(source_object_names),
        "loadedObjectCount": len(imported),
        "supportedFamilyGeometryCount": len(supported),
        "objectTypeCounts": dict(sorted(type_counts.items())),
        "collectionInstanceCount": len(collection_instances),
        "libraryDatablockCounts": library_counts,
        "objects": objects,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Inspect .blend object types without render/export side effects."
    )
    parser.add_argument("blend_files", nargs="+", help="One or more .blend files")
    args = parser.parse_args(_script_args())

    reports = []
    for source in args.blend_files:
        try:
            reports.append({"ok": True, **inspect_blend(source)})
        except Exception as exc:
            reports.append({
                "ok": False,
                "source": str(source),
                "error": f"{type(exc).__name__}: {exc}",
            })

    print(json.dumps({"reports": reports}, indent=2, ensure_ascii=False))
    if any(not report.get("ok", False) for report in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
