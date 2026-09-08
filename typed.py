import json

from . import core
from .family_types import get_family_type, infer_member_rules


def family_profile(root):
    return get_family_type(getattr(root, "bfc_family_kind", "GENERIC"))


def capture_typed_family(root):
    """Capture base transforms and assign rules using the selected family type."""
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    family_dims = (
        max(abs(root.bfc_base_width), 1e-9),
        max(abs(root.bfc_base_depth), 1e-9),
        max(abs(root.bfc_base_height), 1e-9),
    )

    root["bfc_applying"] = True
    try:
        for obj in core.family_members(root):
            # Reuse the generic capture to store stable base transforms/bounds.
            core.analyze_member(root, obj)

            mins, maxs = core.local_bbox(obj, root)
            span = maxs - mins
            center = (mins + maxs) * 0.5

            spans = []
            centers = []
            for index in range(3):
                size = family_dims[index]
                spans.append(abs(span[index]) / size)
                half = size * 0.5
                centers.append(abs(center[index]) / half if half > 1e-9 else 0.0)

            rules = infer_member_rules(family_kind, spans, centers, name=obj.name)
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
    return {
        "familyKind": type_id,
        "familyProfile": {
            "label": spec["label"],
            "group": spec["group"],
            "category": spec["category"],
            "strategy": spec["strategy"],
            "editableAxes": list(spec.get("editable_axes", ())),
            "parameters": list(spec.get("parameters", ())),
        },
    }


def export_typed_family(root, directory, export_glb=True):
    manifest_path, glb_path = core.export_family(root, directory, export_glb)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data.update(typed_manifest_metadata(root))
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path, glb_path
