from .. import core
from .common import (
    local_center,
    local_span,
    resize_family_axis_anchored,
    role_members,
    semantic_float,
    set_family_local_location,
)


def rebuild(root):
    seat_height = semantic_float(root, "seat_height", 0.0)
    if seat_height <= 0.0:
        return {"changed": False, "message": "Seat Height is Auto/zero; source geometry kept"}

    seats = role_members(root, {"SEAT"}, include_generated=True)
    if not seats:
        return {"changed": False, "message": "CHAIR has no SEAT member"}

    floor_z = -float(root.bfc_height) * 0.5
    old_top = max(float(core.local_bbox(obj, root)[1].z) for obj in seats)
    target_top = floor_z + seat_height
    delta = target_top - old_top

    for obj in seats:
        center = local_center(obj, root)
        set_family_local_location(root, obj, "Z", float(center.z) + delta)
        obj.bfc_rule_z = "MOVE"

    for obj in role_members(root, {"BACK", "ARM"}, include_generated=True):
        center = local_center(obj, root)
        set_family_local_location(root, obj, "Z", float(center.z) + delta)

    seat_bottom = min(float(core.local_bbox(obj, root)[0].z) for obj in seats)
    target_leg_height = max(seat_bottom - floor_z, 0.001)
    for obj in role_members(root, {"LEG"}, include_generated=True):
        resize_family_axis_anchored(root, obj, "Z", target_leg_height, anchor="MIN")
        obj.bfc_rule_z = "STRETCH"

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "seatHeight": seat_height,
        "message": f"Applied chair seat height {seat_height:.3f}",
    }
