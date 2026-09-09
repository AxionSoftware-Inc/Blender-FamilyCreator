def anchored_axis_bounds(base_size, current_size, anchor="CENTER"):
    base_size = max(float(base_size), 1e-9)
    current_size = max(float(current_size), 1e-9)
    if anchor == "MIN":
        minimum = -base_size * 0.5
        return minimum, minimum + current_size
    if anchor == "MAX":
        maximum = base_size * 0.5
        return maximum - current_size, maximum
    half = current_size * 0.5
    return -half, half


def envelope_from_dimensions(base_dimensions, dimensions, anchors=None):
    anchors = anchors or {}
    axes = ("X", "Y", "Z")
    mins = []
    maxs = []
    for index, axis in enumerate(axes):
        minimum, maximum = anchored_axis_bounds(
            base_dimensions[index],
            dimensions[index],
            anchors.get(axis, "CENTER"),
        )
        mins.append(float(minimum))
        maxs.append(float(maximum))
    center = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
    size = [maxs[i] - mins[i] for i in range(3)]
    return {
        "min": mins,
        "max": maxs,
        "center": center,
        "size": size,
    }


def _actual_family_bounds(root):
    from . import core

    members = core.exportable_family_members(root)
    if not members:
        return None

    bounds = [core.local_bbox(obj, root) for obj in members]
    mins = [min(float(bound[0][axis]) for bound in bounds) for axis in range(3)]
    maxs = [max(float(bound[1][axis]) for bound in bounds) for axis in range(3)]
    center = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
    size = [maxs[i] - mins[i] for i in range(3)]
    return {"min": mins, "max": maxs, "center": center, "size": size}


def runtime_proxy_metadata(root):
    from . import core
    from .family_types import get_family_type

    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    profile = get_family_type(family_kind)
    anchors = dict(profile.get("axis_anchors", {}))
    base = (
        float(root.bfc_base_width),
        float(root.bfc_base_depth),
        float(root.bfc_base_height),
    )
    current_dimensions = (
        float(root.bfc_width),
        float(root.bfc_depth),
        float(root.bfc_height),
    )

    actual = _actual_family_bounds(root)
    if actual is None:
        actual = envelope_from_dimensions(base, current_dimensions, anchors)

    type_bounds = {}
    for type_name, values in core.read_types(root).items():
        if not isinstance(values, dict):
            continue
        dimensions = (
            float(values.get("width", current_dimensions[0])),
            float(values.get("depth", current_dimensions[1])),
            float(values.get("height", current_dimensions[2])),
        )
        type_bounds[type_name] = envelope_from_dimensions(base, dimensions, anchors)

    return {
        "coordinateSystem": "RIGHT_HANDED_Z_UP",
        "selection": {
            "shape": "AABB",
            "min": actual["min"],
            "max": actual["max"],
            "center": actual["center"],
            "size": actual["size"],
        },
        "collision": {
            "shape": "AABB",
            "coarse": True,
            "center": actual["center"],
            "size": actual["size"],
        },
        "planFootprint": {
            "shape": "RECTANGLE",
            "min": [actual["min"][0], actual["min"][1]],
            "max": [actual["max"][0], actual["max"][1]],
            "baseZ": actual["min"][2],
        },
        "typeBounds": type_bounds,
    }
