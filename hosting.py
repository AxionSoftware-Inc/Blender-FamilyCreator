from . import core
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
    if family_kind in {"DOOR", "WINDOW"}:
        return (0.0, 0.0, -float(root.bfc_height) * 0.5)
    return (0.0, 0.0, 0.0)


def _role_centers_x(root, roles):
    values = []
    for obj in core.family_members(root):
        if bool(obj.get(core.GENERATED_FLAG, False)):
            continue
        role = getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"
        if role not in roles:
            continue
        mins, maxs = core.local_bbox(obj, root)
        values.append(float((mins.x + maxs.x) * 0.5))
    return values


def infer_door_hinge_side(root):
    hinges = _role_centers_x(root, {"HINGE"})
    if hinges:
        return "LEFT" if sum(hinges) / len(hinges) < 0.0 else "RIGHT"

    # Handles normally sit opposite the hinge side, which gives a useful
    # fallback for downloaded doors that merged hinge hardware into the frame.
    handles = _role_centers_x(root, {"HANDLE"})
    if handles:
        return "RIGHT" if sum(handles) / len(handles) < 0.0 else "LEFT"
    return "UNKNOWN"


def _plan_representation(root, family_kind):
    if family_kind == "DOOR":
        hinge_side = infer_door_hinge_side(root)
        return {
            "type": "DOOR_SWING",
            "openingWidth": float(root.bfc_width),
            "leafLength": float(root.bfc_width),
            "hingeSide": hinge_side,
            "swingAngleDegrees": 90.0,
            "swingDirection": "UNKNOWN",
        }
    if family_kind == "WINDOW":
        return {
            "type": "WINDOW_OPENING",
            "openingWidth": float(root.bfc_width),
            "frameDepth": float(root.bfc_depth),
        }
    return None


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

    data = {
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
    plan = _plan_representation(root, family_kind)
    if plan is not None:
        data["planRepresentation"] = plan
    return data
