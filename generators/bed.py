from .common import resize_family_axis_anchored, role_members, semantic_float


def rebuild(root):
    mattress_height = semantic_float(root, "mattress_height", 0.0)
    if mattress_height <= 0.0:
        return {"changed": False, "message": "Mattress Height is Auto/zero; source geometry kept"}

    mattresses = role_members(root, {"MATTRESS"}, include_generated=True)
    if not mattresses:
        return {"changed": False, "message": "BED has no MATTRESS member"}

    for obj in mattresses:
        resize_family_axis_anchored(root, obj, "Z", mattress_height, anchor="MIN")

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "affected": len(mattresses),
        "mattressHeight": mattress_height,
        "message": f"Applied mattress height {mattress_height:.3f}",
    }
