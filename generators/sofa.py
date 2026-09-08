from .. import core
from ..family_types.parameter_specs import property_name
from .common import (
    choose_center_prototype,
    clear_generated,
    duplicate_template,
    evenly_spaced_centers,
    local_center,
    local_span,
    prepare_template_group,
    resize_family_axis_anchored,
    role_members,
    semantic_float,
    set_family_local_location,
    unmark_templates,
)


GROUP = "SOFA_SEATS"
SEAT_ROLE = "SEAT"


def _semantic_int(root, name, fallback=0):
    value = root.get(property_name(name), fallback)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _apply_arm_width(root):
    arm_width = semantic_float(root, "arm_width", 0.0)
    if arm_width <= 0.0:
        return 0

    affected = 0
    for obj in role_members(root, {"ARM_LEFT"}, include_generated=True):
        resize_family_axis_anchored(root, obj, "X", arm_width, anchor="MIN")
        affected += 1
    for obj in role_members(root, {"ARM_RIGHT"}, include_generated=True):
        resize_family_axis_anchored(root, obj, "X", arm_width, anchor="MAX")
        affected += 1
    for obj in role_members(root, {"ARM"}, include_generated=True):
        resize_family_axis_anchored(root, obj, "X", arm_width, anchor="CENTER")
        affected += 1
    return affected


def _apply_seat_height(root, seats):
    seat_height = semantic_float(root, "seat_height", 0.0)
    if seat_height <= 0.0 or not seats:
        return 0.0

    floor_z = -float(root.bfc_height) * 0.5
    old_top = max(float(core.local_bbox(obj, root)[1].z) for obj in seats)
    target_top = floor_z + seat_height
    delta = target_top - old_top
    if abs(delta) <= 1e-9:
        return 0.0

    for obj in seats:
        center = local_center(obj, root)
        set_family_local_location(root, obj, "Z", float(center.z) + delta)
    return delta


def _inner_bounds(root):
    half = float(root.bfc_width) * 0.5
    arm_width = max(semantic_float(root, "arm_width", 0.0), 0.0)
    left = -half + arm_width
    right = half - arm_width

    for obj in role_members(root, {"ARM_LEFT"}, include_generated=False):
        _mins, maxs = core.local_bbox(obj, root)
        left = max(left, float(maxs.x))
    for obj in role_members(root, {"ARM_RIGHT"}, include_generated=False):
        mins, _maxs = core.local_bbox(obj, root)
        right = min(right, float(mins.x))
    return left, right


def rebuild(root):
    clear_generated(root, GROUP)
    arm_affected = _apply_arm_width(root)

    templates = prepare_template_group(root, {SEAT_ROLE}, GROUP)
    if not templates:
        if arm_affected:
            root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
            return {
                "changed": True,
                "affected": arm_affected,
                "message": "Applied Sofa Arm Width; no SEAT role found for repetition",
            }
        return {
            "changed": False,
            "message": "SOFA generator needs at least one member classified as SEAT",
        }

    seat_delta = _apply_seat_height(root, templates)
    source_count = len(templates)
    target_count = _semantic_int(root, "seat_count", source_count)
    if target_count <= 0:
        target_count = source_count
        root[property_name("seat_count")] = int(target_count)

    prototype = choose_center_prototype(templates, root, axis=0)
    seat_width = float(local_span(prototype, root).x)
    inner_left, inner_right = _inner_bounds(root)
    usable = inner_right - inner_left
    if usable <= 0.0:
        unmark_templates(templates)
        return {
            "changed": bool(arm_affected or abs(seat_delta) > 1e-9),
            "message": "SOFA has no usable width between arms",
        }

    slot = usable / float(target_count)
    if seat_width > slot * 1.08:
        unmark_templates(templates)
        return {
            "changed": bool(arm_affected or abs(seat_delta) > 1e-9),
            "message": (
                f"Requested {target_count} seats do not fit current sofa width. "
                "Increase Width or reduce Seat Count."
            ),
        }

    first_center = inner_left + slot * 0.5
    last_center = inner_right - slot * 0.5
    centers = evenly_spaced_centers(target_count, first_center, last_center)

    generated = []
    for index, center in enumerate(centers, start=1):
        clone = duplicate_template(
            root,
            prototype,
            GROUP,
            f"{root.bfc_family_name}_Seat_{index:02d}",
            role=SEAT_ROLE,
        )
        set_family_local_location(root, clone, "X", center)
        clone.bfc_rule_x = "MOVE"
        clone.bfc_rule_y = "FIXED"
        clone.bfc_rule_z = "FIXED"
        generated.append(clone)

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "generated": len(generated),
        "affected": arm_affected,
        "group": GROUP,
        "seatCount": target_count,
        "seatHeight": semantic_float(root, "seat_height", 0.0),
        "armWidth": semantic_float(root, "arm_width", 0.0),
        "message": f"Generated {target_count} sofa seat modules and applied sofa semantic geometry",
    }
