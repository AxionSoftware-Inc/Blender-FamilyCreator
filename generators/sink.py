from .common import resize_family_axis_anchored, role_members, semantic_float


def rebuild(root):
    diameter = semantic_float(root, "drain_diameter", 0.0)
    drains = role_members(root, {"DRAIN"}, include_generated=False)
    if diameter <= 0.0:
        return {"changed": False, "message": "Sink drain diameter is Auto/zero"}
    if not drains:
        return {"changed": False, "message": "Sink generator needs a member classified as DRAIN"}

    affected = 0
    for obj in drains:
        resize_family_axis_anchored(root, obj, "X", diameter, anchor="CENTER")
        resize_family_axis_anchored(root, obj, "Y", diameter, anchor="CENTER")
        obj.bfc_rule_x = "FIXED"
        obj.bfc_rule_y = "FIXED"
        obj.bfc_rule_z = "FIXED"
        affected += 1

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "affected": affected,
        "drainDiameter": diameter,
        "message": f"Applied sink drain diameter to {affected} member(s)",
    }
