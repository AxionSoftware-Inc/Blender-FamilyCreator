import json

from . import core
from .family_types import get_family_type
from .family_types.parameter_specs import get_parameter_specs, property_name
from .family_types.strategies import (
    classify_member_role,
    infer_member_rules,
    infer_semantic_parameters,
)
from .generators import rebuild_family_geometry, supports_generation
from .quality import validate_family


def family_profile(root):
    return get_family_type(getattr(root, "bfc_family_kind", "GENERIC"))


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
    """Capture source/template members, never generated copies."""
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    family_dims = (
        max(abs(root.bfc_base_width), 1e-9),
        max(abs(root.bfc_base_depth), 1e-9),
        max(abs(root.bfc_base_height), 1e-9),
    )
    member_infos = []

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
            absolute_centers = []
            signed_centers = []
            for index in range(3):
                size = family_dims[index]
                spans.append(abs(span[index]) / size)
                half = size * 0.5
                signed = center[index] / half if half > 1e-9 else 0.0
                signed_centers.append(signed)
                absolute_centers.append(abs(signed))

            role = classify_member_role(
                family_kind,
                spans,
                signed_centers,
                name=obj.name,
            )
            obj.bfc_member_role = role

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
    root = core.create_family(context, objects, name)
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

    return {
        "familyKind": type_id,
        "semanticParameters": semantic_parameter_values(root, type_id),
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


def _inject_member_roles(root, data):
    roles = {
        obj.name: (getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN")
        for obj in core.exportable_family_members(root)
    }
    for member in data.get("members", []):
        member["role"] = roles.get(member.get("name"), "UNKNOWN")


def export_typed_family(root, directory, export_glb=True):
    manifest_path, glb_path = core.export_family(root, directory, export_glb)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data.update(typed_manifest_metadata(root))
    _inject_member_roles(root, data)
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path, glb_path
