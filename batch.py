import json
from collections import Counter
from pathlib import Path

import bpy

from . import core
from .batch_cleanup import cleanup_new_datablocks, snapshot_datablocks
from .batch_source_index import (
    SOURCE_INDEX_FILENAME,
    build_source_index,
    compare_source_indexes,
    load_source_index,
    write_source_index,
)
from .catalog import build_library_index
from .core import SUPPORTED_TYPES
from .family_path import resolve_family_class_from_path
from .generators import rebuild_family_geometry, supports_generation
from .library_audit import write_library_audit
from .prepare import DEFAULT_MAX_LOOSE_ISLANDS, auto_prepare_objects
from .quality import validate_family
from .typed import create_typed_family, export_typed_family


SUPPORTED_ASSET_EXTENSIONS = {".blend", ".fbx", ".glb", ".gltf", ".obj"}
AUTO_FOLDER_CLASS = "AUTO_FOLDER"


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


def _relative_family_key(filepath, input_directory):
    filepath = Path(filepath)
    input_directory = Path(input_directory)
    try:
        relative = filepath.relative_to(input_directory)
    except ValueError:
        relative = Path(filepath.name)
    return relative.with_suffix("")


def _build_output_keys(assets, input_directory):
    base_keys = [_relative_family_key(path, input_directory) for path in assets]
    counts = Counter(str(key).lower() for key in base_keys)
    output_keys = {}

    for filepath, key in zip(assets, base_keys):
        if counts[str(key).lower()] > 1:
            suffix = filepath.suffix.lower().lstrip(".") or "asset"
            key = key.parent / f"{key.name}_{suffix}"
        output_keys[filepath] = key
    return output_keys


def _family_id_from_key(family_kind, key):
    key = Path(key)
    parts = [core.slugify(part) for part in key.parts if str(part).strip()]
    suffix = "/".join(part for part in parts if part)
    if not suffix:
        suffix = "family"
    return f"axion:{family_kind.lower()}:{suffix}"


def _resolve_requested_family_kind(requested_kind, filepath, input_directory):
    if requested_kind != AUTO_FOLDER_CLASS:
        return requested_kind
    resolved = resolve_family_class_from_path(filepath, input_directory)
    if resolved is None:
        relative = _relative_family_key(filepath, input_directory).as_posix()
        raise ValueError(
            f"Could not resolve exact Family Class from folders for '{relative}'. "
            "Place the asset under a recognized class folder such as sofas/, tables/, doors/ or windows/."
        )
    return resolved


def _snapshot_objects():
    return set(bpy.data.objects)


def _new_objects(before):
    return [obj for obj in bpy.data.objects if obj not in before]


def _object_type_counts(objects):
    counts = Counter(
        str(getattr(obj, "type", "UNKNOWN") or "UNKNOWN")
        for obj in objects
        if obj is not None
    )
    return dict(sorted(counts.items()))


def _unsupported_geometry_detail(objects):
    type_counts = _object_type_counts(objects)
    type_text = ", ".join(
        f"{object_type}={count}"
        for object_type, count in type_counts.items()
    ) or "none"
    collection_instances = sum(
        1
        for obj in objects
        if obj is not None and getattr(obj, "instance_collection", None) is not None
    )
    if collection_instances:
        return f"object types: {type_text}; collection instances={collection_instances}"
    return f"object types: {type_text}"


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


def _remove_objects(objects):
    unique = []
    seen = set()
    for obj in objects:
        if obj is None or obj in seen:
            continue
        seen.add(obj)
        unique.append(obj)

    unique.sort(key=lambda obj: len(obj.children_recursive))
    for obj in unique:
        if obj and obj.name in bpy.data.objects:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass


def _cleanup_import(imported, root=None):
    cleanup_objects = list(imported)
    if root is not None and root.name in bpy.data.objects:
        cleanup_objects.extend(list(root.children_recursive))
        cleanup_objects.append(root)
    _remove_objects(cleanup_objects)


def _prepare_imported(context, imported, auto_split_loose, max_loose_islands):
    if not auto_split_loose:
        return list(imported), {
            "enabled": False,
            "split_objects": 0,
            "output_objects": len(imported),
            "reports": [],
        }

    prepared = auto_prepare_objects(context, imported, max_islands=max_loose_islands)
    return prepared["objects"], {
        "enabled": True,
        "split_objects": prepared["split_objects"],
        "output_objects": prepared["output_objects"],
        "reports": prepared["reports"],
    }


def convert_asset(
    context,
    filepath,
    output_directory,
    family_kind,
    export_glb=True,
    export_baked_types=True,
    export_thumbnail=True,
    export_lods=False,
    output_key=None,
    auto_split_loose=True,
    max_loose_islands=DEFAULT_MAX_LOOSE_ISLANDS,
):
    filepath = Path(filepath)
    object_snapshot = _snapshot_objects()
    datablock_snapshot = snapshot_datablocks()
    imported = []
    root = None
    result = None

    try:
        imported = import_asset(filepath, context)
        prepared_objects, prepare_report = _prepare_imported(
            context,
            imported,
            auto_split_loose=auto_split_loose,
            max_loose_islands=max_loose_islands,
        )
        for obj in prepared_objects:
            if obj not in imported:
                imported.append(obj)

        geometry = [obj for obj in prepared_objects if obj.type in SUPPORTED_TYPES]
        if not geometry:
            detail = _unsupported_geometry_detail(prepared_objects)
            raise ValueError(f"No supported mesh/curve geometry found ({detail})")

        key = Path(output_key) if output_key is not None else Path(filepath.stem)
        family_id = _family_id_from_key(family_kind, key)

        root = create_typed_family(context, prepared_objects, filepath.stem, family_kind)
        root["bfc_family_id"] = family_id
        root["bfc_source_asset"] = str(filepath)
        root["bfc_source_key"] = key.as_posix()

        quality_before = validate_family(root)
        generator_result = None
        if supports_generation(family_kind):
            generator_result = rebuild_family_geometry(root)
        quality_after = validate_family(root)

        family_output = Path(output_directory) / family_kind.lower() / key
        manifest, glb = export_typed_family(
            root,
            family_output,
            export_glb=export_glb,
            export_baked_types=export_baked_types and export_glb,
            export_thumbnail=export_thumbnail,
            export_lods=export_lods and export_glb,
        )
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        result = {
            "source": str(filepath),
            "output_key": key.as_posix(),
            "family_id": family_id,
            "family": filepath.stem,
            "family_kind": family_kind,
            "prepare": prepare_report,
            "manifest": str(manifest),
            "glb": str(glb) if glb else None,
            "thumbnail": manifest_data.get("thumbnail"),
            "export_warnings": list(manifest_data.get("exportWarnings", [])),
            "baked_types": bool(export_baked_types and export_glb),
            "lods_enabled": bool(export_lods and export_glb),
            "geometry_lods": manifest_data.get("geometryLods"),
            "runtime_cost": manifest_data.get("runtimeCost"),
            "mobile_budget": manifest_data.get("mobileBudget"),
            "generator": generator_result,
            "quality_before": quality_before,
            "quality": quality_after,
            "needs_review": not bool(quality_after.get("automaticReady", False)),
        }
        return result
    finally:
        cleanup_error = None
        cleanup_report = None
        try:
            created_objects = _new_objects(object_snapshot)
            _cleanup_import(created_objects, root=root)
        except Exception as exc:
            cleanup_error = f"Object cleanup failed: {exc}"

        try:
            cleanup_report = cleanup_new_datablocks(datablock_snapshot)
        except Exception as exc:
            message = f"Datablock cleanup failed: {exc}"
            cleanup_error = f"{cleanup_error}; {message}" if cleanup_error else message

        if result is not None:
            if cleanup_report is None:
                cleanup_report = {
                    "passes": 0,
                    "removed": {},
                    "removedCount": 0,
                    "leftovers": {},
                    "leftoverCount": 0,
                    "complete": False,
                }
            result["cleanup"] = cleanup_report

            warning_parts = []
            if cleanup_error:
                warning_parts.append(cleanup_error)
            if not cleanup_report.get("complete", False):
                warning_parts.append(
                    f"{cleanup_report.get('leftoverCount', 0)} post-import Blender datablock(s) "
                    "remain in use after cleanup"
                )
            if warning_parts:
                result["cleanup_warning"] = "; ".join(warning_parts)


def _write_json(output_directory, filename, payload):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _review_queue_payload(report):
    review_items = []
    for item in report.get("results", []):
        if not item.get("needs_review"):
            continue
        quality = item.get("quality", {})
        review_items.append({
            "source": item.get("source"),
            "output_key": item.get("output_key"),
            "family_id": item.get("family_id"),
            "family": item.get("family"),
            "family_kind": item.get("family_kind"),
            "manifest": item.get("manifest"),
            "glb": item.get("glb"),
            "thumbnail": item.get("thumbnail"),
            "export_warnings": item.get("export_warnings", []),
            "geometry_lods": item.get("geometry_lods"),
            "runtime_cost": item.get("runtime_cost"),
            "mobile_budget": item.get("mobile_budget"),
            "cleanup": item.get("cleanup"),
            "cleanup_warning": item.get("cleanup_warning"),
            "score": quality.get("score"),
            "automaticReady": quality.get("automaticReady"),
            "roleCoverage": quality.get("roleCoverage"),
            "missingRoleGroups": quality.get("missingRoleGroups", []),
            "missingRecommendedRoleGroups": quality.get("missingRecommendedRoleGroups", []),
            "preflight": quality.get("preflight", {}),
            "warnings": quality.get("warnings", []),
            "errors": quality.get("errors", []),
            "generator": item.get("generator"),
            "prepare": item.get("prepare"),
        })

    return {
        "family_kind": report.get("family_kind"),
        "input_directory": report.get("input_directory"),
        "output_directory": report.get("output_directory"),
        "review_count": len(review_items),
        "items": review_items,
        "failed": list(report.get("errors", [])),
    }


def _finalize_report(output_directory, report):
    output_directory = Path(output_directory)
    previous_source_index_path = output_directory / SOURCE_INDEX_FILENAME
    previous_source_index = load_source_index(previous_source_index_path)
    current_source_index = build_source_index(report)

    report["ready"] = sum(1 for item in report.get("results", []) if not item.get("needs_review"))
    report["needs_review"] = sum(1 for item in report.get("results", []) if item.get("needs_review"))
    all_export_warnings = [
        warning
        for item in report.get("results", [])
        for warning in item.get("export_warnings", [])
    ]
    report["thumbnail_warnings"] = sum(
        1 for warning in all_export_warnings if str(warning).lower().startswith("thumbnail")
    )
    report["lod_warnings"] = sum(
        1 for warning in all_export_warnings if str(warning).lower().startswith("lod:")
    )
    report["cleanup_warnings"] = sum(
        1 for item in report.get("results", []) if item.get("cleanup_warning")
    )
    report["cleanup_leftover_datablocks"] = sum(
        int((item.get("cleanup") or {}).get("leftoverCount", 0) or 0)
        for item in report.get("results", [])
    )
    report["mobile_budget_status_counts"] = dict(sorted(Counter(
        (item.get("mobile_budget") or {}).get("status")
        for item in report.get("results", [])
        if (item.get("mobile_budget") or {}).get("status")
    ).items()))

    class_items = list(report.get("results", [])) + list(report.get("errors", []))
    report["resolved_class_counts"] = dict(sorted(Counter(
        item.get("family_kind")
        for item in class_items
        if item.get("family_kind")
    ).items()))

    review_payload = _review_queue_payload(report)
    review_path = _write_json(output_directory, "review-queue.json", review_payload)
    report["review_queue_path"] = str(review_path)

    catalog = None
    try:
        catalog_path, catalog = build_library_index(output_directory)
        report["library_index_path"] = str(catalog_path)
        report["library_family_count"] = int(catalog.get("familyCount", 0))
        report["library_missing_asset_count"] = int(catalog.get("missingAssetCount", 0))
        report["library_asset_warning_count"] = int(catalog.get("assetWarningCount", 0))
        report["library_index_error"] = None
    except Exception as exc:
        report["library_index_path"] = None
        report["library_family_count"] = None
        report["library_missing_asset_count"] = None
        report["library_asset_warning_count"] = None
        report["library_index_error"] = str(exc)

    if report.get("aborted"):
        source_diagnostics = {
            "comparable": False,
            "skippedReason": "ABORTED_BATCH",
            "staleFamilyIds": [],
            "failedRefreshFamilyIds": [],
            "staleCount": 0,
            "failedRefreshCount": 0,
        }
        report["source_index_updated"] = False
        report["source_index_path"] = (
            str(previous_source_index_path) if previous_source_index_path.is_file() else None
        )
        report["source_index_error"] = None
    else:
        catalog_ids = {
            str(item.get("familyId"))
            for item in ((catalog or {}).get("families", ()) or ())
            if isinstance(item, dict) and item.get("familyId")
        }
        source_diagnostics = compare_source_indexes(
            previous_source_index,
            current_source_index,
            catalog_family_ids=catalog_ids,
        )
        try:
            source_index_path = write_source_index(output_directory, current_source_index)
            report["source_index_path"] = str(source_index_path)
            report["source_index_updated"] = True
            report["source_index_error"] = None
        except Exception as exc:
            report["source_index_path"] = None
            report["source_index_updated"] = False
            report["source_index_error"] = str(exc)

    report["source_index_comparable"] = bool(source_diagnostics.get("comparable", False))
    report["stale_output_family_ids"] = list(source_diagnostics.get("staleFamilyIds", ()))
    report["failed_refresh_family_ids"] = list(source_diagnostics.get("failedRefreshFamilyIds", ()))
    report["stale_output_count"] = int(source_diagnostics.get("staleCount", 0) or 0)
    report["failed_refresh_package_count"] = int(source_diagnostics.get("failedRefreshCount", 0) or 0)
    if source_diagnostics.get("skippedReason"):
        report["source_index_diagnostic_skipped_reason"] = source_diagnostics.get("skippedReason")

    try:
        audit_path, audit = write_library_audit(output_directory)
        report["library_audit_path"] = str(audit_path)
        report["library_audit_complete"] = bool(audit.get("complete", False))
        report["library_audit_warning_count"] = int(audit.get("warningCount", 0))
        report["library_audit_error"] = None
    except Exception as exc:
        report["library_audit_path"] = None
        report["library_audit_complete"] = None
        report["library_audit_warning_count"] = None
        report["library_audit_error"] = str(exc)

    report_path = _write_json(output_directory, "batch-report.json", report)
    report["report_path"] = str(report_path)
    _write_json(output_directory, "batch-report.json", report)
    return report


def batch_convert_directory(
    context,
    input_directory,
    output_directory,
    family_kind,
    recursive=True,
    export_glb=True,
    export_baked_types=True,
    export_thumbnail=True,
    export_lods=False,
    continue_on_error=True,
    auto_split_loose=True,
    max_loose_islands=DEFAULT_MAX_LOOSE_ISLANDS,
):
    input_directory = Path(input_directory)
    assets = discover_assets(input_directory, recursive=recursive)
    if not assets:
        raise ValueError("No supported .blend/.fbx/.glb/.gltf/.obj assets found")

    output_keys = _build_output_keys(assets, input_directory)
    results = []
    errors = []
    for filepath in assets:
        actual_kind = None
        try:
            actual_kind = _resolve_requested_family_kind(family_kind, filepath, input_directory)
            results.append(
                convert_asset(
                    context,
                    filepath,
                    output_directory,
                    actual_kind,
                    export_glb=export_glb,
                    export_baked_types=export_baked_types,
                    export_thumbnail=export_thumbnail,
                    export_lods=export_lods,
                    output_key=output_keys[filepath],
                    auto_split_loose=auto_split_loose,
                    max_loose_islands=max_loose_islands,
                )
            )
        except Exception as exc:
            error = {
                "source": str(filepath),
                "output_key": output_keys[filepath].as_posix(),
                "error": str(exc),
            }
            if actual_kind is not None:
                error["family_kind"] = actual_kind
                error["family_id"] = _family_id_from_key(actual_kind, output_keys[filepath])
            errors.append(error)
            if not continue_on_error:
                report = {
                    "family_kind": family_kind,
                    "input_directory": str(input_directory),
                    "output_directory": str(output_directory),
                    "discovered": len(assets),
                    "converted": len(results),
                    "failed": len(errors),
                    "export_glb": bool(export_glb),
                    "export_baked_types": bool(export_baked_types and export_glb),
                    "export_thumbnail": bool(export_thumbnail),
                    "export_lods": bool(export_lods and export_glb),
                    "auto_split_loose": auto_split_loose,
                    "max_loose_islands": max_loose_islands,
                    "results": results,
                    "errors": errors,
                    "aborted": True,
                }
                _finalize_report(output_directory, report)
                raise

    report = {
        "family_kind": family_kind,
        "input_directory": str(input_directory),
        "output_directory": str(output_directory),
        "discovered": len(assets),
        "converted": len(results),
        "failed": len(errors),
        "export_glb": bool(export_glb),
        "export_baked_types": bool(export_baked_types and export_glb),
        "export_thumbnail": bool(export_thumbnail),
        "export_lods": bool(export_lods and export_glb),
        "auto_split_loose": auto_split_loose,
        "max_loose_islands": max_loose_islands,
        "results": results,
        "errors": errors,
        "aborted": False,
    }
    return _finalize_report(output_directory, report)
