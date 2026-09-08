from .. import core
from ..family_types.parameter_specs import property_name
from .common import (
    choose_center_prototype,
    clear_generated,
    duplicate_template,
    prepare_template_group,
    role_members,
    set_family_local_location,
    unmark_templates,
)


GROUP = "SHELF_LEVELS"
SHELF_ROLE = "SHELF"


def _semantic_int(root, name, fallback=0):
    try:
        return int(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return int(fallback)


def _vertical_bounds(root):
    bottom = -float(root.bfc_height) * 0.5
    top = float(root.bfc_height) * 0.5

    bottoms = role_members(root, {"BOTTOM"}, include_generated=False)
    tops = role_members(root, {"TOP"}, include_generated=False)
    if bottoms:
        bottom = max(float(core.local_bbox(obj, root)[1].z) for obj in bottoms)
    if tops:
        top = min(float(core.local_bbox(obj, root)[0].z) for obj in tops)
    return bottom, top


def rebuild(root):
    clear_generated(root, GROUP)
    templates = prepare_template_group(root, {SHELF_ROLE}, GROUP)
    if not templates:
        return {
            "changed": False,
            "message": "SHELF generator needs at least one member classified as SHELF",
        }

    source_count = len(templates)
    target_count = _semantic_int(root, "shelf_count", source_count)
    if target_count <= 0:
        target_count = source_count
        root[property_name("shelf_count")] = int(target_count)

    bottom, top = _vertical_bounds(root)
    if top <= bottom:
        unmark_templates(templates)
        return {"changed": False, "message": "Invalid shelf interior height"}

    prototype = choose_center_prototype(templates, root, axis=2)
    gap = (top - bottom) / float(target_count + 1)
    positions = [bottom + gap * (index + 1) for index in range(target_count)]

    generated = []
    for index, z in enumerate(positions, start=1):
        clone = duplicate_template(
            root,
            prototype,
            GROUP,
            f"{root.bfc_family_name}_Shelf_{index:02d}",
            role=SHELF_ROLE,
        )
        set_family_local_location(root, clone, "Z", z)
        clone.bfc_rule_x = "STRETCH"
        clone.bfc_rule_y = "STRETCH"
        clone.bfc_rule_z = "MOVE"
        generated.append(clone)

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "generated": len(generated),
        "group": GROUP,
        "shelfCount": target_count,
        "message": f"Generated {target_count} shelf levels",
    }
