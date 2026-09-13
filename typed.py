import json
import os
import shutil
import tempfile
from pathlib import Path

from . import core
from .family_types import get_family_type
from .family_types.parameter_specs import get_parameter_specs, property_name
from .family_types.strategies import (
    classify_member_role,
    infer_member_rules,
    infer_semantic_parameters,
    refine_member_roles,
)
from .generators import rebuild_family_geometry, supports_generation
from .geometry_export import export_glb_geometry
from .hierarchy import create_family_preserving_hierarchy
from .hosting import hosting_metadata
from .lod import export_family_lods
from .materials import family_material_metadata
from .package_assets import manifest_asset_uris
from .quality import validate_family
from .runtime_cost import family_runtime_cost
from .runtime_proxy import runtime_proxy_metadata
from .schema import assert_valid_manifest
from .thumbnail import DEFAULT_THUMBNAIL_SIZE, render_family_thumbnail
from .variants import export_baked_type_variants


class PackageRollbackError(RuntimeError):
    """A package commit failed and rollback could not fully restore old files.

    `recovery_directory` is deliberately preserved on disk so the remaining
    staged/backup files can be inspected or restored manually.
    """

    def __init__(self, message, recovery_directory):
        super().__init__(message)
        self.recovery_directory = Path(recovery_directory)


def family_profile(root):
    return get_family_type(getattr(root, "bfc_family_kind", "GENERIC"))


def family_identifier(root, family_kind=None):
    family_kind = family_kind or getattr(root, "bfc_family_kind", "GENERIC")
    explicit = str(root.get("bfc_family_id", "") or "").strip()
    if explicit:
        return explicit
    return f"axion:{family_kind.lower()}:{core.slugify(root.bfc_family_name)}"


def _axis_default(root, axis):
    return {
        "X": float(root.bfc_base_width),
        "Y": float(root.bfc_base_depth),
        "Z": float(root.bfc_base_height),
    }[axis]


def ensure_semantic_parameters(root, family_kind=None):
    family_kind = family_kind or getattr(root, "bfc_family_kind", "GENERIC")
    specs = get_parameter_specs(family_kind)

    for parameter, spec in specs.items():
        prop = property_name(parameter)
        if prop not in root:
            if "default_axis" in spec:
                default = _axis_default(root, spec["default_axis"])
            else:
                default = spec.get("default", 0)
            root[prop] = int(default) if spec.get("type") == "INT" else float(default)

        ui_args = {"description": spec.get("description", parameter)}
        if "min" in spec:
            ui_args["min"] = spec["min"]
        if "max" in spec:
            ui_args["max"] = spec["max"]
        try:
            root.id_properties_ui(prop).update(**ui_args)
        except Exception:
            pass
    return specs


def semantic_parameter_values(root, family_kind=None):
    family_kind = family_kind or getattr(root, "bfc_family_kind", "GENERIC")
    specs = ensure_semantic_parameters(root, family_kind)
    values = {}
    for parameter, spec in specs.items():
        value = root.get(property_name(parameter), 0)
        values[parameter] = int(value) if spec.get("type") == "INT" else float(value)
    return values


def apply_semantic_parameter_values(root, values, family_kind=None):
    family_kind = family_kind or getattr(root, "bfc_family_kind", "GENERIC")
    specs = ensure_semantic_parameters(root, family_kind)
    for parameter, value in (values or {}).items():
        if parameter not in specs:
            continue
        spec = specs[parameter]
        prop = property_name(parameter)
        root[prop] = int(value) if spec.get("type") == "INT" else float(value)


def apply_inferred_semantic_parameter_values(root, values, family_kind=None):
    family_kind = family_kind or getattr(root, "bfc_family_kind", "GENERIC")
    specs = ensure_semantic_parameters(root, family_kind)
    for parameter, value in (values or {}).items():
        if parameter not in specs or value is None:
            continue
        spec = specs[parameter]
        prop = property_name(parameter)
        current = root.get(prop, 0)
        if float(current) > 0.0:
            continue
        root[prop] = int(value) if spec.get("type") == "INT" else float(value)


def capture_typed_family(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    family_dims = (
        max(abs(root.bfc_base_width), 1e-9),
        max(abs(root.bfc_base_depth), 1e-9),
        max(abs(root.bfc_base_height), 1e-9),
    )
    member_infos = []
    member_objects = []

    root["bfc_applying"] = True
    try:
        for obj in core.family_members(root):
            if bool(obj.get(core.GENERATED_FLAG, False)):
                continue

            core.analyze_member(root, obj)
            mins, maxs = core.local_bbox(obj, root)
            span = maxs - mins
            center = (mins + maxs) * 0.5

            spans = []
            signed_centers = []
            for index in range(3):
                size = family_dims[index]
                spans.append(abs(span[index]) / size)
                half = size * 0.5
                signed = center[index] / half if half > 1e-9 else 0.0
                signed_centers.append(signed)

            role = classify_member_role(family_kind, spans, signed_centers, name=obj.name)
            member_objects.append(obj)
            member_infos.append({
                "name": obj.name,
                "role": role,
                "mins": tuple(float(v) for v in mins),
                "maxs": tuple(float(v) for v in maxs),
                "span": tuple(float(v) for v in span),
                "center": tuple(float(v) for v in center),
                "normalized_span": tuple(float(v) for v in spans),
                "normalized_center": tuple(float(v) for v in signed_centers),
            })

        member_infos = refine_member_roles(family_kind, member_infos, family_dims)

        for obj, info in zip(member_objects, member_infos):
            role = info.get("role", "UNKNOWN") or "UNKNOWN"
            spans = info.get("normalized_span", (0.0, 0.0, 0.0))
            signed_centers = info.get("normalized_center", (0.0, 0.0, 0.0))
            absolute_centers = tuple(abs(float(value)) for value in signed_centers)

            obj.bfc_member_role = role
            refinement = str(info.get("roleRefinement", "") or "").strip()
            if refinement:
                obj["bfc_role_refinement"] = refinement
            elif "bfc_role_refinement" in obj:
                del obj["bfc_role_refinement"]

            rules = infer_member_rules(
                family_kind,
                spans,
                absolute_centers,
                name=obj.name,
                role=role,
            )
            obj.bfc_rule_x = rules["X"]
            obj.bfc_rule_y = rules["Y"]
            obj.bfc_rule_z = rules["Z"]
    finally:
        root["bfc_applying"] = False

    inferred = infer_semantic_parameters(family_kind, member_infos, family_dims)
    apply_inferred_semantic_parameter_values(root, inferred, family_kind)
    return member_infos


def apply_family_kind(root, family_kind, recapture=True):
    spec = get_family_type(family_kind)
    root["bfc_applying"] = True
    try:
        root.bfc_family_kind = family_kind
        root.bfc_category = spec["category"]
        ensure_semantic_parameters(root, family_kind)
    finally:
        root["bfc_applying"] = False

    if recapture:
        capture_typed_family(root)
        core.apply_family(root)
    return spec


def create_typed_family(context, objects, name, family_kind):
    root = create_family_preserving_hierarchy(context, objects, name)
    apply_family_kind(root, family_kind, recapture=True)
    save_typed_type(root, "Default", overwrite=True)
    return root


def save_typed_type(root, name, overwrite=False):
    core.save_type(root, name, overwrite=overwrite)
    data = core.read_types(root)
    data[name]["semanticParameters"] = semantic_parameter_values(root)
    core.write_types(root, data)
    return data[name]


def apply_typed_type(root, name):
    data = core.read_types(root)
    if name not in data:
        raise ValueError(f"Type '{name}' not found")

    values = data[name]
    root["bfc_applying"] = True
    try:
        root.bfc_width = float(values["width"])
        root.bfc_depth = float(values["depth"])
        root.bfc_height = float(values["height"])
        apply_semantic_parameter_values(root, values.get("semanticParameters", {}))
        root.bfc_type_name = name
    finally:
        root["bfc_applying"] = False

    core.apply_family(root)
    if supports_generation(root.bfc_family_kind):
        rebuild_family_geometry(root)


def typed_manifest_metadata(root):
    type_id = getattr(root, "bfc_family_kind", "GENERIC")
    spec = get_family_type(type_id)

    role_counts = {}
    for obj in core.exportable_family_members(root):
        role = getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"
        role_counts[role] = role_counts.get(role, 0) + 1

    runtime_cost, mobile_budget = family_runtime_cost(root)
    metadata = {
        "familyId": family_identifier(root, type_id),
        "familyKind": type_id,
        "units": {"length": "meter"},
        "coordinateSystems": {
            "family": "RIGHT_HANDED_Z_UP",
            "geometry": "GLTF_RIGHT_HANDED_Y_UP",
        },
        "semanticParameters": semantic_parameter_values(root, type_id),
        "materials": family_material_metadata(root),
        "runtimeProxy": runtime_proxy_metadata(root),
        "runtimeCost": runtime_cost,
        "mobileBudget": mobile_budget,
        "quality": validate_family(root),
        "generator": {
            "supported": supports_generation(type_id),
            "revision": int(root.get("bfc_generator_revision", 0)),
        },
        "familyProfile": {
            "label": spec["label"],
            "group": spec["group"],
            "category": spec["category"],
            "strategy": spec["strategy"],
            "logicModule": spec.get("logic_module"),
            "editableAxes": list(spec.get("editable_axes", ())),
            "axisParameters": dict(spec.get("axis_parameters", {})),
            "axisAnchors": dict(spec.get("axis_anchors", {})),
            "parameters": list(spec.get("parameters", ())),
            "roleCounts": role_counts,
        },
    }

    source_asset = str(root.get("bfc_source_asset", "") or "").strip()
    source_key = str(root.get("bfc_source_key", "") or "").strip()
    if source_asset or source_key:
        metadata["source"] = {
            "asset": source_asset or None,
            "key": source_key or None,
        }

    hosting = hosting_metadata(root)
    if hosting is not None:
        metadata["hosting"] = hosting
    return metadata


def _inject_member_roles(root, data):
    member_metadata = {
        obj.name: {
            "role": (getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"),
            "roleRefinement": str(obj.get("bfc_role_refinement", "") or "").strip(),
        }
        for obj in core.exportable_family_members(root)
    }
    for member in data.get("members", []):
        metadata = member_metadata.get(member.get("name"), {})
        member["role"] = metadata.get("role", "UNKNOWN")
        refinement = metadata.get("roleRefinement")
        if refinement:
            member["roleRefinement"] = refinement


def _thumbnail_path(directory, root):
    return Path(directory) / f"{core.slugify(root.bfc_family_name)}.thumbnail.png"


def _primary_glb_path(directory, root):
    return Path(directory) / f"{core.slugify(root.bfc_family_name)}.glb"


def _manifest_sort_key(path, stage_directory):
    relative = path.relative_to(stage_directory).as_posix()
    is_manifest = path.name.endswith(".family.json")
    return (1 if is_manifest else 0, relative)


def _existing_directories(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return set()
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_dir()
    }


def _remove_new_empty_directories(directory, existing_directories, destination_existed):
    directory = Path(directory)
    if not directory.exists():
        return
    directories = sorted(
        (path for path in directory.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in directories:
        relative = path.relative_to(directory).as_posix()
        if relative in existing_directories:
            continue
        try:
            if not any(path.iterdir()):
                path.rmdir()
        except Exception:
            pass
    if not destination_existed:
        try:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        except Exception:
            pass


def _read_manifest_assets(path):
    path = Path(path)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return manifest_asset_uris(data)


def _commit_staged_package(stage_directory, destination_directory):
    """Commit a validated package and rollback replaced/removed managed files.

    The staged manifest is the source of truth for the new managed asset set.
    A destination package may contain at most one root family manifest. That
    previous manifest is replaced transactionally even when the family name (and
    therefore manifest filename) changed. Files never referenced by either
    manifest remain untouched.
    """
    stage_directory = Path(stage_directory)
    destination_directory = Path(destination_directory)
    destination_parent = destination_directory.parent
    destination_parent.mkdir(parents=True, exist_ok=True)

    staged_files = sorted(
        (path for path in stage_directory.rglob("*") if path.is_file()),
        key=lambda path: _manifest_sort_key(path, stage_directory),
    )
    if not staged_files:
        raise RuntimeError("Staged family package contains no files")

    manifest_files = [path for path in staged_files if path.name.endswith(".family.json")]
    if len(manifest_files) != 1:
        raise RuntimeError(f"Staged family package must contain exactly one manifest, got {len(manifest_files)}")

    staged_manifest = manifest_files[0]
    try:
        staged_manifest_data = json.loads(staged_manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Could not read staged family manifest: {exc}") from exc

    new_asset_uris = manifest_asset_uris(staged_manifest_data)
    staged_asset_files = {
        path.relative_to(stage_directory).as_posix()
        for path in staged_files
        if path != staged_manifest
    }
    missing_staged_assets = sorted(new_asset_uris - staged_asset_files)
    unreferenced_staged_assets = sorted(staged_asset_files - new_asset_uris)
    if missing_staged_assets:
        raise RuntimeError(
            "Staged manifest references missing package asset(s): "
            + ", ".join(missing_staged_assets[:8])
        )
    if unreferenced_staged_assets:
        raise RuntimeError(
            "Staged package contains unreferenced managed file(s): "
            + ", ".join(unreferenced_staged_assets[:8])
        )

    existing_manifests = []
    if destination_directory.is_dir():
        existing_manifests = sorted(
            path for path in destination_directory.glob("*.family.json") if path.is_file()
        )
    if len(existing_manifests) > 1:
        names = ", ".join(path.name for path in existing_manifests[:8])
        raise RuntimeError(
            "Destination family package contains multiple root manifests; refusing ambiguous overwrite: "
            + names
        )

    previous_manifest_target = existing_manifests[0] if existing_manifests else None
    old_asset_uris = (
        _read_manifest_assets(previous_manifest_target)
        if previous_manifest_target is not None
        else set()
    )
    obsolete_asset_uris = sorted(old_asset_uris - new_asset_uris)

    destination_existed = destination_directory.exists()
    existing_directories = _existing_directories(destination_directory)
    backup_root = stage_directory.parent / "__bfc_backup__"
    backups = {}
    touched_targets = []

    def backup_existing(target):
        if target in backups or not target.exists():
            return
        relative = target.relative_to(destination_directory)
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        os.replace(target, backup)
        backups[target] = backup

    try:
        if previous_manifest_target is not None:
            backup_existing(previous_manifest_target)
            touched_targets.append(previous_manifest_target)

        for uri in obsolete_asset_uris:
            target = destination_directory / Path(uri)
            if target.exists() and target.is_file() and target not in touched_targets:
                backup_existing(target)
                touched_targets.append(target)

        for source in staged_files:
            relative = source.relative_to(stage_directory)
            target = destination_directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)

            if target not in touched_targets:
                backup_existing(target)
                touched_targets.append(target)
            os.replace(source, target)
    except Exception as commit_error:
        rollback_errors = []
        for target in reversed(touched_targets):
            try:
                if target.exists() and target.is_file():
                    target.unlink()
            except Exception as exc:
                rollback_errors.append(f"remove {target}: {exc}")

            backup = backups.get(target)
            if backup is not None and backup.exists():
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(backup, target)
                except Exception as exc:
                    rollback_errors.append(f"restore {target}: {exc}")

        _remove_new_empty_directories(
            destination_directory,
            existing_directories,
            destination_existed,
        )

        if rollback_errors:
            recovery_root = stage_directory.parent
            preview = "; ".join(rollback_errors[:5])
            if len(rollback_errors) > 5:
                preview += f"; +{len(rollback_errors) - 5} more"
            raise PackageRollbackError(
                (
                    f"Family package commit failed: {commit_error}; rollback incomplete: {preview}; "
                    f"recovery files preserved at {recovery_root}"
                ),
                recovery_directory=recovery_root,
            ) from commit_error
        raise


def _build_staged_typed_package(
    root,
    stage_directory,
    export_glb,
    export_baked_types,
    export_thumbnail,
    export_lods,
    thumbnail_size,
):
    stage_directory = Path(stage_directory)
    manifest_path, _ = core.export_family(root, stage_directory, export_glb=False)
    glb_path = None

    if export_glb:
        glb_path = _primary_glb_path(stage_directory, root)
        export_glb_geometry(root, glb_path)
        if not glb_path.exists() or glb_path.stat().st_size <= 0:
            raise RuntimeError("Primary GLB export did not create a non-empty file")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data.update(typed_manifest_metadata(root))
    _inject_member_roles(root, data)

    if glb_path is not None:
        variant_result = export_baked_type_variants(
            root,
            stage_directory,
            glb_path,
            export_all_types=bool(export_baked_types),
        )
        data["geometryVariants"] = variant_result["variants"]
        data["geometryStrategy"] = {
            "mode": "BAKED_TYPE_VARIANTS" if len(data["geometryVariants"]) > 1 else "BAKED_ACTIVE_TYPE",
            "activeType": str(root.bfc_type_name),
            "variantCount": len(data["geometryVariants"]),
        }

        if export_lods:
            primary = data["geometryVariants"].get(str(root.bfc_type_name), {})
            primary_uri = primary.get("uri", Path(glb_path).name)
            lod_result = export_family_lods(
                root,
                stage_directory,
                primary_uri=primary_uri,
                enabled=True,
            )
            data["geometryLods"] = lod_result["lods"]
            data["lodStrategy"] = {
                "mode": "NON_DESTRUCTIVE_DECIMATE",
                "source": "LOD0",
                "levelCount": len(lod_result["lods"]),
                "protectedRoles": sorted({
                    item.get("role")
                    for level in lod_result["lods"].values()
                    for item in level.get("protectedOrSkippedMembers", [])
                    if item.get("role")
                }),
            }
            data["runtimeCost"] = lod_result["runtimeCost"]
            data["mobileBudget"] = lod_result["mobileBudget"]
            for warning in lod_result.get("warnings", ()):
                data.setdefault("exportWarnings", []).append(f"LOD: {warning}")

    if export_thumbnail:
        thumbnail_path = _thumbnail_path(stage_directory, root)
        try:
            data["thumbnail"] = render_family_thumbnail(
                root,
                thumbnail_path,
                size=thumbnail_size,
            )
        except Exception as exc:
            try:
                thumbnail_path.unlink(missing_ok=True)
            except Exception:
                pass
            data.setdefault("exportWarnings", []).append(
                f"Thumbnail render failed: {exc}"
            )

    assert_valid_manifest(data)
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path, glb_path


def export_typed_family(
    root,
    directory,
    export_glb=True,
    export_baked_types=False,
    export_thumbnail=False,
    export_lods=False,
    thumbnail_size=DEFAULT_THUMBNAIL_SIZE,
):
    """Export one family package through a validate-before-overwrite transaction.

    Normal staging/build/commit failures clean temporary files. If the commit
    fails *and* rollback itself is incomplete, the temporary recovery directory
    is intentionally kept so old backups are not destroyed by context cleanup.
    """
    destination = Path(directory)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_root = Path(tempfile.mkdtemp(
        prefix=".bfc-package-",
        dir=str(destination.parent),
    ))
    preserve_recovery = False
    try:
        stage_directory = temporary_root / "package"
        stage_directory.mkdir(parents=True, exist_ok=True)

        staged_manifest, staged_glb = _build_staged_typed_package(
            root,
            stage_directory,
            export_glb=bool(export_glb),
            export_baked_types=bool(export_baked_types),
            export_thumbnail=bool(export_thumbnail),
            export_lods=bool(export_lods),
            thumbnail_size=thumbnail_size,
        )

        manifest_relative = staged_manifest.relative_to(stage_directory)
        glb_relative = staged_glb.relative_to(stage_directory) if staged_glb is not None else None

        _commit_staged_package(stage_directory, destination)
    except PackageRollbackError:
        preserve_recovery = True
        raise
    finally:
        if not preserve_recovery:
            shutil.rmtree(temporary_root, ignore_errors=True)

    manifest_path = destination / manifest_relative
    glb_path = destination / glb_relative if glb_relative is not None else None
    return manifest_path, glb_path
