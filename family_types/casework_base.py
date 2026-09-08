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


def _median(values):
    values = sorted(float(v) for v in values if float(v) > 0.0)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) * 0.5


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

    if sx <= 0.18 and sy >= 0.45 and sz >= 0.55 and abs(cx) >= 0.55:
        return ROLE_SIDE_LEFT if cx < 0.0 else ROLE_SIDE_RIGHT
    if sz <= 0.16 and sx >= 0.55 and sy >= 0.40:
        if cz >= 0.55:
            return ROLE_TOP
        if cz <= -0.55:
            return ROLE_BOTTOM
        return ROLE_SHELF
    if sy <= 0.16 and sx >= 0.55 and sz >= 0.55 and abs(cy) >= 0.50:
        return ROLE_BACK
    if sy <= 0.18 and sx >= 0.25 and sz >= 0.18 and abs(cy) >= 0.45:
        return ROLE_DOOR
    if sx >= 0.55 or sy >= 0.55 or sz >= 0.55:
        return ROLE_CARCASS
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    thicknesses = []
    shelves = 0
    toe_kicks = []

    for member in members:
        role = member.get("role")
        span = member.get("span", (0.0, 0.0, 0.0))
        if role in {ROLE_SIDE_LEFT, ROLE_SIDE_RIGHT}:
            thicknesses.append(abs(float(span[0])))
        elif role in {ROLE_TOP, ROLE_BOTTOM, ROLE_SHELF}:
            thicknesses.append(abs(float(span[2])))
            if role == ROLE_SHELF:
                shelves += 1
        elif role == ROLE_BACK:
            thicknesses.append(abs(float(span[1])))
        elif role == ROLE_TOE_KICK:
            toe_kicks.append(abs(float(span[2])))

    values = {}
    panel_thickness = _median(thicknesses)
    if panel_thickness is not None:
        values["panel_thickness"] = panel_thickness
    if shelves:
        values["shelf_count"] = shelves
    if toe_kicks:
        values["toe_kick_height"] = max(toe_kicks)
    return values


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
