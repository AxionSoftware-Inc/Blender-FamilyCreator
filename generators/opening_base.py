from .common import resize_family_axis_anchored, role_members, semantic_float


def apply_opening_parameters(root, *, panel_role=None, panel_thickness_parameter=None):
    changed = 0
    frame_width = semantic_float(root, "frame_width", 0.0)

    if frame_width > 0.0:
        for obj in role_members(root, {"FRAME_LEFT"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "X", frame_width, anchor="MIN")
            changed += 1
        for obj in role_members(root, {"FRAME_RIGHT"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "X", frame_width, anchor="MAX")
            changed += 1
        for obj in role_members(root, {"FRAME_HEAD"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Z", frame_width, anchor="MAX")
            changed += 1
        for obj in role_members(root, {"FRAME_SILL"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "Z", frame_width, anchor="MIN")
            changed += 1
        for obj in role_members(root, {"MULLION"}, include_generated=True):
            resize_family_axis_anchored(root, obj, "X", frame_width, anchor="CENTER")
            changed += 1

    panel_thickness = 0.0
    if panel_role and panel_thickness_parameter:
        panel_thickness = semantic_float(root, panel_thickness_parameter, 0.0)
        if panel_thickness > 0.0:
            for obj in role_members(root, {panel_role}, include_generated=True):
                resize_family_axis_anchored(root, obj, "Y", panel_thickness, anchor="CENTER")
                changed += 1

    return {
        "changed": changed > 0,
        "affected": changed,
        "frameWidth": frame_width,
        "panelThickness": panel_thickness,
    }
