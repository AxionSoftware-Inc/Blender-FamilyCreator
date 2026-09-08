from pathlib import Path

import bpy

from .core import SUPPORTED_TYPES
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
        # Blender 4.x native OBJ importer.
        bpy.ops.wm.obj_import(filepath=str(filepath))
    else:
        raise ValueError(f"Unsupported asset format: {extension}")

    return _new_objects(before)


def _remove_objects(objects):
    for obj in list(objects):
        if obj and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def _purge_unused_data():
    # Remove only zero-user datablocks created by repeated imports. Keep this
    # conservative so batch conversion never touches live scene data in use.
    datablock_collections = (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.images,
    )
    for collection in datablock_collections:
        for datablock in list(collection):
            if datablock.users == 0:
                collection.remove(datablock)


def convert_asset(context, filepath, output_directory, family_kind, export_glb=True):
    filepath = Path(filepath)
    imported = import_asset(filepath, context)
    geometry = [obj for obj in imported if obj.type in SUPPORTED_TYPES]
    if not geometry:
        _remove_objects(imported)
        raise ValueError("No supported mesh/curve geometry found")

    root = None
    try:
        root = create_typed_family(context, geometry, filepath.stem, family_kind)
        family_output = Path(output_directory) / family_kind.lower() / filepath.stem
        manifest, glb = export_typed_family(root, family_output, export_glb=export_glb)
        return {
            "source": str(filepath),
            "family": filepath.stem,
            "family_kind": family_kind,
            "manifest": str(manifest),
            "glb": str(glb) if glb else None,
        }
    finally:
        cleanup = list(imported)
        if root is not None:
            cleanup.append(root)
        _remove_objects(cleanup)
        _purge_unused_data()


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
                raise

    return {
        "family_kind": family_kind,
        "input_directory": str(input_directory),
        "output_directory": str(output_directory),
        "converted": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
