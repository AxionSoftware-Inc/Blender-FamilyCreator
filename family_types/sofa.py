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
    """Classify one sofa member from its normalized envelope and object name.

    `centers` is signed family-space center ratios in X/Y/Z where +/-1 is
    approximately the outer family edge. Names are treated as hints, not a
    requirement, so unnamed Blender assets still get useful behavior.
    """
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

    # Geometry-only fallbacks for poorly named downloaded assets.
    # Narrow pieces near the X edges are usually arms, legs, or side panels.
    if sx <= 0.24 and abs(cx) >= 0.62:
        if sz <= 0.45 and cz <= -0.15:
            return ROLE_LEG
        return ROLE_ARM_LEFT if cx < 0.0 else ROLE_ARM_RIGHT

    # Wide, shallow, low members are likely seat/base elements.
    if sx >= 0.45 and sy >= 0.35 and sz <= 0.35 and cz <= 0.20:
        return ROLE_SEAT

    # Wide members toward the rear/top are likely back rests.
    if sx >= 0.40 and (abs(cy) >= 0.35 or cz >= 0.15) and sz >= 0.25:
        return ROLE_BACK

    if sx >= 0.50:
        return ROLE_BASE
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    if axis != "X":
        return "FIXED"

    role = role or ROLE_UNKNOWN
    if role in {ROLE_ARM_LEFT, ROLE_ARM_RIGHT, ROLE_ARM, ROLE_LEG, ROLE_DECOR}:
        return "MOVE"

    # A monolithic seat/back/base should stretch. Small individual cushions
    # should preserve their size and move with their normalized X position.
    if role in {ROLE_SEAT, ROLE_BACK}:
        return "STRETCH" if span_ratio >= 0.52 else "MOVE"
    if role == ROLE_BASE:
        return "STRETCH" if span_ratio >= 0.34 else "MOVE"

    if name_has(name, "arm", "side", "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.28 else "FIXED"
