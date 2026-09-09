from pathlib import Path

from . import core
from .family_types.parameter_specs import get_parameter_specs, property_name
from .generators import rebuild_family_geometry, supports_generation
from .geometry_export import export_glb_geometry


def _semantic_values(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    specs = get_parameter_specs(family_kind)
    values = {}
    for name, spec in specs.items():
        raw = root.get(property_name(name), 0)
        values[name] = int(raw) if spec.get("type") == "INT" else float(raw)
    return values


def snapshot_family_state(root):
    return {
        "typeName": str(getattr(root, "bfc_type_name", "Default") or "Default"),
        "width": float(root.bfc_width),
        "depth": float(root.bfc_depth),
        "height": float(root.bfc_height),
        "semanticParameters": _semantic_values(root),
        "generatorRevision": int(root.get("bfc_generator_revision", 0)),
    }


def _write_semantic(root, values):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    specs = get_parameter_specs(family_kind)
    for name, spec in specs.items():
        if name not in values:
            continue
        value = values[name]
        root[property_name(name)] = int(value) if spec.get("type") == "INT" else float(value)


def apply_state(root, state, fallback_semantic=None):
    semantic = dict(fallback_semantic or {})
    semantic.update(state.get("semanticParameters", {}) or {})

    root["bfc_applying"] = True
    try:
        root.bfc_width = float(state["width"])
        root.bfc_depth = float(state["depth"])
        root.bfc_height = float(state["height"])
        _write_semantic(root, semantic)
        root.bfc_type_name = str(state.get("typeName", root.bfc_type_name) or "Default")
    finally:
        root["bfc_applying"] = False

    core.apply_family(root)
    generator_result = None
    if supports_generation(getattr(root, "bfc_family_kind", "GENERIC")):
        generator_result = rebuild_family_geometry(root)
    return generator_result


def _saved_type_state(name, values, semantic_fallback):
    return {
        "typeName": str(name),
        "width": float(values["width"]),
        "depth": float(values["depth"]),
        "height": float(values["height"]),
        "semanticParameters": dict(values.get("semanticParameters", {}) or semantic_fallback),
    }


def _variant_filenames(type_names):
    used = set()
    result = {}
    for type_name in type_names:
        base = core.slugify(type_name) or "type"
        candidate = base
        index = 2
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate)
        result[type_name] = f"{candidate}.glb"
    return result


def export_baked_type_variants(
    root,
    directory,
    primary_glb_path,
    export_all_types=True,
):
    directory = Path(directory)
    primary_glb_path = Path(primary_glb_path)
    original = snapshot_family_state(root)
    saved_types = core.read_types(root)
    active_name = original["typeName"]

    variants = {
        active_name: {
            "uri": primary_glb_path.relative_to(directory).as_posix(),
            "baked": True,
            "primary": True,
        }
    }
    created_files = []

    if not export_all_types or len(saved_types) <= 1:
        return {
            "variants": variants,
            "current": original,
            "createdFiles": created_files,
        }

    other_names = [name for name in saved_types if name != active_name]
    filenames = _variant_filenames(other_names)
    variants_dir = directory / "variants"

    try:
        for type_name in other_names:
            values = saved_types[type_name]
            state = _saved_type_state(type_name, values, original["semanticParameters"])
            generator_result = apply_state(
                root,
                state,
                fallback_semantic=original["semanticParameters"],
            )

            variant_path = variants_dir / filenames[type_name]
            export_glb_geometry(root, variant_path)
            created_files.append(variant_path)
            variants[type_name] = {
                "uri": variant_path.relative_to(directory).as_posix(),
                "baked": True,
                "primary": False,
                "generatorChanged": bool(generator_result and generator_result.get("changed")),
            }
    except Exception:
        for path in created_files:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        raise
    finally:
        apply_state(root, original, fallback_semantic=original["semanticParameters"])
        root["bfc_generator_revision"] = int(original["generatorRevision"])

    return {
        "variants": variants,
        "current": original,
        "createdFiles": created_files,
    }
