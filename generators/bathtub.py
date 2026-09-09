from .common import local_span, resize_family_axis_anchored, role_members, semantic_float


AXES = ("X", "Y", "Z")


def _rim_profile_axis(root, obj):
    span = local_span(obj, root)
    values = [abs(float(span.x)), abs(float(span.y)), abs(float(span.z))]
    positive = [(value, index) for index, value in enumerate(values) if value > 1e-6]
    if not positive:
        return None
    _value, index = min(positive)
    return AXES[index]


def rebuild(root):
    thickness = semantic_float(root, "rim_thickness", 0.0)
    rims = role_members(root, {"RIM"}, include_generated=False)
    if thickness <= 0.0:
        return {"changed": False, "message": "Bathtub rim thickness is Auto/zero"}
    if not rims:
        return {"changed": False, "message": "Bathtub generator needs a member classified as RIM"}

    affected = 0
    axes = {}
    for obj in rims:
        axis = _rim_profile_axis(root, obj)
        if axis is None:
            continue
        resize_family_axis_anchored(root, obj, axis, thickness, anchor="CENTER")
        axes[obj.name] = axis
        affected += 1

    if not affected:
        return {"changed": False, "message": "Bathtub rim members have no measurable profile axis"}

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "affected": affected,
        "rimThickness": thickness,
        "profileAxes": axes,
        "message": f"Applied bathtub rim thickness to {affected} member(s)",
    }
