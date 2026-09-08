import json

from . import core
from .family_types import get_family_type
from .family_types.strategies import classify_member_role, infer_member_rules


def family_profile(root):
    return get_family_type(getattr(root, "bfc_family_kind", "GENERIC"))


def capture_typed_family(root):
    """Capture base transforms and assign semantic roles/rules for the selected class."""
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    family_dims = (
        max(abs(root.bfc_base_width), 1e-9),
        max(abs(root.bfc_base_depth), 1e-9),
        max(abs(root.bfc_base_height), 1e-9),
    )

    root["bfc_applying"] = True
    try:
        for obj in core.family_members(root):
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
    finally:
        root["bfc_applying"] = False


def apply_family_kind(root, family_kind, recapture=True):
    spec = get_family_type(family_kind)
    root["bfc_applying"] = True
    try:
        root.bfc_family_kind = family_kind
        root.bfc_category = spec["category"]
    finally:
        root["bfc_applying"] = False

    if recapture:
        capture_typed_family(root)
        core.apply_family(root)
    return spec


def create_typed_family(context, objects, name, family_kind):
    root = core.create_family(context, objects, name)
    apply_family_kind(root, family_kind, recapture=True)
    return root


def typed_manifest_metadata(root):
    type_id = getattr(root, "bfc_family_kind", "GENERIC")
    spec = get_family_type(type_id)

    role_counts = {}
    for obj in core.family_members(root):
        role = getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"
        role_counts[role] = role_counts.get(role, 0) + 1

    return {
        "familyKind": type_id,
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
        for obj in core.family_members(root)
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
