import json
from pathlib import Path

import bpy

from . import core
from .core import SUPPORTED_TYPES
from .generators import rebuild_family_geometry, supports_generation
from .typed import create_typed_family, export_typed_family


SUPPORTED_ASSET_EXTENSIONS = {".blend", ".fbx", ".glb", ".gltf", ".obj"}


def discover_assets(directory, recursive=True):
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Input folder does not exist: {directory}")

    iterator = directory.rglob("*") if recursive else directory.glob("*")
    return sorted(
        path
        for path in iterator
        if path.is_file() and path.suffix.lower() in SUPPORTED_ASSET_EXTENSIONS
    )


def _snapshot_objects():
    return set(bpy.data.objects)


def _new_objects(before):
    return [obj for obj in bpy.data.objects if obj not in before]


def _import_blend(filepath, context):
    with bpy.data.libraries.load(str(filepath), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)

    imported = [obj for obj in data_to.objects if obj is not None]
    for obj in imported:
        if not obj.users_collection:
            context.collection.objects.link(obj)
    return imported


def import_asset(filepath, context):
    filepath = Path(filepath)
    extension = filepath.suffix.lower()
    before = _snapshot_objects()

    if extension == ".blend":
        _import_blend(filepath, context)
    elif extension == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(filepath))
    elif extension in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(filepath))
    elif extension == ".obj":
        bpy.ops.wm.obj_import(filepath=str(filepath))
    else:
        raise ValueError(f"Unsupported asset format: {extension}")

    return _new_objects(before)


def _collect_owned_datablocks(objects):
    owned = set()
    for obj in objects:
        data = getattr(obj, "data", None)
        if data is not None:
            owned.add(data)
            materials = getattr(data, "materials", None)
            if materials is not None:
                for material in materials:
                    if material is not None:
                        owned.add(material)
    return owned


def _remove_objects(objects):
    unique = []
    seen = set()
    for obj in objects:
        if obj is None or obj in seen:
            continue
        seen.add(obj)
        unique.append(obj)

    # Leaves have zero descendants, so ascending descendant count removes
    # children before parents and prevents generated/template survivors.
    unique.sort(key=lambda obj: len(obj.children_recursive))
    for obj in unique:
        if obj and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def _remove_owned_datablocks(datablocks):
    removable = [datablock for datablock in datablocks if datablock is not None and datablock.users == 0]
    if not removable:
        return

    try:
        bpy.data.batch_remove(ids=removable)
    except Exception:
        pass


def _cleanup_import(imported, root=None, owned_datablocks=None):
    cleanup_objects = list(imported)
    if root is not None:
        cleanup_objects.extend(list(root.children_recursive))
        cleanup_objects.append(root)
    _remove_objects(cleanup_objects)
    _remove_owned_datablocks(owned_datablocks or set())


def convert_asset(context, filepath, output_directory, family_kind, export_glb=True):
    filepath = Path(filepath)
    imported = import_asset(filepath, context)
    owned_datablocks = _collect_owned_datablocks(imported)
    root = None

    try:
        geometry = [obj for obj in imported if obj.type in SUPPORTED_TYPES]
        if not geometry:
            raise ValueError("No supported mesh/curve geometry found")

        root = create_typed_family(context, geometry, filepath.stem, family_kind)
        generator_result = None
        if supports_generation(family_kind):
            generator_result = rebuild_family_geometry(root)

        family_output = Path(output_directory) / family_kind.lower() / filepath.stem
        manifest, glb = export_typed_family(root, family_output, export_glb=export_glb)
        return {
            "source": str(filepath),
            "family": filepath.stem,
            "family_kind": family_kind,
            "manifest": str(manifest),
            "glb": str(glb) if glb else None,
            "generator": generator_result,
        }
    finally:
        _cleanup_import(imported, root=root, owned_datablocks=owned_datablocks)


def _write_batch_report(output_directory, report):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    report_path = output_directory / "batch-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def batch_convert_directory(
    context,
    input_directory,
    output_directory,
    family_kind,
    recursive=True,
    export_glb=True,
    continue_on_error=True,
):
    assets = discover_assets(input_directory, recursive=recursive)
    if not assets:
        raise ValueError("No supported .blend/.fbx/.glb/.gltf/.obj assets found")

    results = []
    errors = []
    for filepath in assets:
        try:
            results.append(
                convert_asset(
                    context,
                    filepath,
                    output_directory,
                    family_kind,
                    export_glb=export_glb,
                )
            )
        except Exception as exc:
            errors.append({"source": str(filepath), "error": str(exc)})
            if not continue_on_error:
                report = {
                    "family_kind": family_kind,
                    "input_directory": str(input_directory),
                    "output_directory": str(output_directory),
                    "discovered": len(assets),
                    "converted": len(results),
                    "failed": len(errors),
                    "results": results,
                    "errors": errors,
                    "aborted": True,
                }
                report["report_path"] = str(_write_batch_report(output_directory, report))
                raise

    report = {
        "family_kind": family_kind,
        "input_directory": str(input_directory),
        "output_directory": str(output_directory),
        "discovered": len(assets),
        "converted": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "aborted": False,
    }
    report["report_path"] = str(_write_batch_report(output_directory, report))
    return report
