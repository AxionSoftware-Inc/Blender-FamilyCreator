from .common import resize_family_axis_anchored, role_members, semantic_float


def rebuild(root):
    thickness = semantic_float(root, "top_thickness", 0.0)
    if thickness <= 0.0:
        return {"changed": False, "message": "Top Thickness is Auto/zero; source thickness kept"}

    tops = role_members(root, {"TOP"}, include_generated=True)
    if not tops:
        return {"changed": False, "message": "TABLE has no TOP member"}

    for obj in tops:
        resize_family_axis_anchored(root, obj, "Z", thickness, anchor="MAX")
        obj.bfc_rule_z = "MOVE"

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "affected": len(tops),
        "topThickness": thickness,
        "message": f"Applied top thickness {thickness:.3f} to {len(tops)} table-top member(s)",
    }
