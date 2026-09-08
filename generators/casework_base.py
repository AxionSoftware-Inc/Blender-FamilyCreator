from .. import core
from .common import (
    local_center,
    resize_family_axis_anchored,
    role_members,
    semantic_float,
)


def apply_casework_parameters(root, *, include_toe_kick=False):
    changed = 0
    panel_thickness = semantic_float(root, "panel_thickness", 0.0)

    if panel_thickness > 0.0:
        for obj in role_members(root, {"SIDE_LEFT"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "X", panel_thickness, anchor="MIN")
            changed += 1
        for obj in role_members(root, {"SIDE_RIGHT"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "X", panel_thickness, anchor="MAX")
            changed += 1
        for obj in role_members(root, {"TOP"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Z", panel_thickness, anchor="MAX")
            changed += 1
        for obj in role_members(root, {"BOTTOM"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Z", panel_thickness, anchor="MIN")
            changed += 1
        for obj in role_members(root, {"SHELF"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Z", panel_thickness, anchor="CENTER")
            changed += 1
        for obj in role_members(root, {"BACK"}, include_generated=True):
            center = local_center(obj, root)
            anchor = "MIN" if center.y < 0.0 else "MAX"
            resize_family_axis_anchored(root, obj, "Y", panel_thickness, anchor=anchor)
            changed += 1
        for obj in role_members(root, {"DOOR", "DRAWER_FRONT"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Y", panel_thickness, anchor="CENTER")
            changed += 1

    toe_kick_height = 0.0
    if include_toe_kick:
        toe_kick_height = semantic_float(root, "toe_kick_height", 0.0)
        if toe_kick_height > 0.0:
            for obj in role_members(root, {"TOE_KICK"}, include_generated=True):
                resize_family_axis_anchored(root, obj, "Z", toe_kick_height, anchor="MIN")
                changed += 1

    return {
        "changed": changed > 0,
        "affected": changed,
        "panelThickness": panel_thickness,
        "toeKickHeight": toe_kick_height,
    }
