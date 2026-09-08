from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_SIDE_LEFT = "SIDE_LEFT"
ROLE_SIDE_RIGHT = "SIDE_RIGHT"
ROLE_TOP = "TOP"
ROLE_BOTTOM = "BOTTOM"
ROLE_BACK = "BACK"
ROLE_SHELF = "SHELF"
ROLE_DOOR = "DOOR"
ROLE_DRAWER_FRONT = "DRAWER_FRONT"
ROLE_HANDLE = "HANDLE"
ROLE_HARDWARE = "HARDWARE"
ROLE_TOE_KICK = "TOE_KICK"
ROLE_CARCASS = "CARCASS"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "handle", "knob", "pull"):
        return ROLE_HANDLE
    if name_has(name, "hinge", "hardware", "runner", "slide"):
        return ROLE_HARDWARE
    if name_has(name, "drawer", "drawer_front"):
        return ROLE_DRAWER_FRONT
    if name_has(name, "toe", "kick", "plinth", "socle"):
        return ROLE_TOE_KICK
    if name_has(name, "back", "rear"):
        return ROLE_BACK
    if name_has(name, "shelf"):
        return ROLE_SHELF
    if name_has(name, "door", "front", "shutter"):
        return ROLE_DOOR
    if name_has(name, "left") and name_has(name, "side", "panel", "carcass"):
        return ROLE_SIDE_LEFT
    if name_has(name, "right") and name_has(name, "side", "panel", "carcass"):
        return ROLE_SIDE_RIGHT
    if name_has(name, "top", "cap"):
        return ROLE_TOP
    if name_has(name, "bottom", "base_panel", "floor_panel"):
        return ROLE_BOTTOM

    # Geometry fallback. Thin vertical panels at X edges are side panels.
    if sx <= 0.18 and sy >= 0.45 and sz >= 0.55 and abs(cx) >= 0.55:
        return ROLE_SIDE_LEFT if cx < 0.0 else ROLE_SIDE_RIGHT
    # Thin horizontal panels at top/bottom.
    if sz <= 0.16 and sx >= 0.55 and sy >= 0.40:
        if cz >= 0.55:
            return ROLE_TOP
        if cz <= -0.55:
            return ROLE_BOTTOM
        return ROLE_SHELF
    # Thin rear panel spanning width/height.
    if sy <= 0.16 and sx >= 0.55 and sz >= 0.55 and abs(cy) >= 0.50:
        return ROLE_BACK
    # Front leaves/drawer fronts are shallow in Y and live near the front.
    if sy <= 0.18 and sx >= 0.25 and sz >= 0.18 and abs(cy) >= 0.45:
        return ROLE_DOOR
    if sx >= 0.55 or sy >= 0.55 or sz >= 0.55:
        return ROLE_CARCASS
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", editable_axes=("X", "Y", "Z"), role=None):
    if axis not in editable_axes:
        return "FIXED"

    role = role or ROLE_UNKNOWN

    if role in {ROLE_HANDLE, ROLE_HARDWARE}:
        return "MOVE"
    if role in {ROLE_SIDE_LEFT, ROLE_SIDE_RIGHT}:
        if axis == "X":
            return "MOVE"
        return "STRETCH"
    if role in {ROLE_TOP, ROLE_BOTTOM, ROLE_SHELF}:
        if axis == "Z":
            return "MOVE"
        return "STRETCH"
    if role == ROLE_BACK:
        if axis == "Y":
            return "MOVE"
        return "STRETCH"
    if role == ROLE_DOOR:
        if axis == "Y":
            return "MOVE"
        return "STRETCH"
    if role == ROLE_DRAWER_FRONT:
        if axis == "X":
            return "STRETCH"
        return "MOVE"
    if role == ROLE_TOE_KICK:
        if axis == "X":
            return "STRETCH"
        return "FIXED" if axis == "Z" else "MOVE"
    if role == ROLE_CARCASS:
        return "STRETCH"

    if name_has(name, "handle", "hinge", "knob", "hardware"):
        return "MOVE" if center_ratio >= 0.25 else "FIXED"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    if span_ratio >= 0.46:
        return "STRETCH"
    return "FIXED"
