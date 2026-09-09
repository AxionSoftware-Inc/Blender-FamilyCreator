from .family_types.parameter_specs import property_name


HOSTING_PROFILES = {
    "DOOR": {
        "hostType": "WALL",
        "insertionPoint": "THRESHOLD_CENTER",
        "cutHost": True,
        "cutShape": "RECTANGLE",
        "facingDirection": (0.0, 1.0, 0.0),
        "upDirection": (0.0, 0.0, 1.0),
        "canFlipFacing": True,
        "canFlipHand": True,
    },
    "WINDOW": {
        "hostType": "WALL",
        "insertionPoint": "SILL_CENTER",
        "cutHost": True,
        "cutShape": "RECTANGLE",
        "facingDirection": (0.0, 1.0, 0.0),
        "upDirection": (0.0, 0.0, 1.0),
        "canFlipFacing": True,
        "canFlipHand": False,
    },
}


def supports_hosting(family_kind):
    return family_kind in HOSTING_PROFILES


def _semantic_float(root, name, fallback=0.0):
    try:
        return float(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return float(fallback)


def placement_origin_local(root, family_kind):
    # Family roots are centered on the source bounding box. Door threshold and
    # window sill insertion points live at the lower center of the opening.
    if family_kind in {"DOOR", "WINDOW"}:
        return (0.0, 0.0, -float(root.bfc_height) * 0.5)
    return (0.0, 0.0, 0.0)


def hosting_metadata(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    profile = HOSTING_PROFILES.get(family_kind)
    if profile is None:
        return None

    elevation = 0.0
    if family_kind == "WINDOW":
        elevation = max(_semantic_float(root, "sill_height", 0.9), 0.0)

    origin = placement_origin_local(root, family_kind)
    opening = {
        "shape": profile["cutShape"],
        "width": float(root.bfc_width),
        "height": float(root.bfc_height),
        "depth": float(root.bfc_depth),
    }

    return {
        "hostType": profile["hostType"],
        "cutHost": bool(profile["cutHost"]),
        "opening": opening,
        "insertionPoint": profile["insertionPoint"],
        "placementOriginLocal": [float(value) for value in origin],
        "elevationFromLevel": elevation,
        "facingDirection": [float(value) for value in profile["facingDirection"]],
        "upDirection": [float(value) for value in profile["upDirection"]],
        "canFlipFacing": bool(profile["canFlipFacing"]),
        "canFlipHand": bool(profile["canFlipHand"]),
    }
