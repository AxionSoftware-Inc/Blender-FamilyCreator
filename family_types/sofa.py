from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_ARM_LEFT = "ARM_LEFT"
ROLE_ARM_RIGHT = "ARM_RIGHT"
ROLE_ARM = "ARM"
ROLE_SEAT = "SEAT"
ROLE_BACK = "BACK"
ROLE_LEG = "LEG"
ROLE_BASE = "BASE"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name=""):
    """Classify one sofa member from its normalized envelope and object name."""
    sx, sy, sz = spans
    cx, cy, cz = centers
    lowered = (name or "").lower()

    if name_has(lowered, "leg", "foot", "feet", "caster"):
        return ROLE_LEG
    if name_has(lowered, "pillow", "cushion_decor", "decor", "throw"):
        return ROLE_DECOR
    if name_has(lowered, "back", "backrest"):
        return ROLE_BACK
    if name_has(lowered, "seat", "cushion", "pad"):
        return ROLE_SEAT
    if name_has(lowered, "base", "frame", "plinth", "rail"):
        return ROLE_BASE

    if name_has(lowered, "left", "_l", ".l", "-l") and name_has(lowered, "arm", "side"):
        return ROLE_ARM_LEFT
    if name_has(lowered, "right", "_r", ".r", "-r") and name_has(lowered, "arm", "side"):
        return ROLE_ARM_RIGHT
    if name_has(lowered, "arm", "side"):
        if cx < -0.25:
            return ROLE_ARM_LEFT
        if cx > 0.25:
            return ROLE_ARM_RIGHT
        return ROLE_ARM

    if sx <= 0.24 and abs(cx) >= 0.62:
        if sz <= 0.45 and cz <= -0.15:
            return ROLE_LEG
        return ROLE_ARM_LEFT if cx < 0.0 else ROLE_ARM_RIGHT

    if sx >= 0.45 and sy >= 0.35 and sz <= 0.35 and cz <= 0.20:
        return ROLE_SEAT

    if sx >= 0.40 and (abs(cy) >= 0.35 or cz >= 0.15) and sz >= 0.25:
        return ROLE_BACK

    if sx >= 0.50:
        return ROLE_BASE
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    seats = [member for member in members if member.get("role") == ROLE_SEAT]
    arms = [
        member
        for member in members
        if member.get("role") in {ROLE_ARM_LEFT, ROLE_ARM_RIGHT, ROLE_ARM}
    ]

    values = {}
    if seats:
        values["seat_count"] = len(seats)
        floor_z = -float(family_dims[2]) * 0.5
        seat_tops = [float(member["maxs"][2]) - floor_z for member in seats]
        values["seat_height"] = sum(seat_tops) / len(seat_tops)

    if arms:
        arm_widths = [abs(float(member["span"][0])) for member in arms]
        values["arm_width"] = sum(arm_widths) / len(arm_widths)

    return values


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    if axis != "X":
        return "FIXED"

    role = role or ROLE_UNKNOWN
    if role in {ROLE_ARM_LEFT, ROLE_ARM_RIGHT, ROLE_ARM, ROLE_LEG, ROLE_DECOR}:
        return "MOVE"

    if role in {ROLE_SEAT, ROLE_BACK}:
        return "STRETCH" if span_ratio >= 0.52 else "MOVE"
    if role == ROLE_BASE:
        return "STRETCH" if span_ratio >= 0.34 else "MOVE"

    if name_has(name, "arm", "side", "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.28 else "FIXED"
