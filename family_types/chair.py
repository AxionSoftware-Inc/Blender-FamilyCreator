from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_SEAT = "SEAT"
ROLE_BACK = "BACK"
ROLE_LEG = "LEG"
ROLE_ARM = "ARM"
ROLE_FRAME = "FRAME"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "leg", "foot", "feet", "caster"):
        return ROLE_LEG
    if name_has(name, "seat", "seat_pad", "cushion"):
        return ROLE_SEAT
    if name_has(name, "back", "backrest"):
        return ROLE_BACK
    if name_has(name, "arm", "armrest"):
        return ROLE_ARM
    if name_has(name, "frame", "rail", "support", "brace"):
        return ROLE_FRAME
    if name_has(name, "decor", "cap", "trim"):
        return ROLE_DECOR

    if sx <= 0.22 and sy <= 0.22 and sz >= 0.45 and cz <= 0.10:
        return ROLE_LEG
    if sx >= 0.45 and sy >= 0.40 and sz <= 0.25 and abs(cz) <= 0.35:
        return ROLE_SEAT
    if sx >= 0.40 and sz >= 0.35 and (abs(cy) >= 0.35 or cz >= 0.25):
        return ROLE_BACK
    if sx <= 0.30 and sy >= 0.35 and sz <= 0.35 and abs(cx) >= 0.55:
        return ROLE_ARM
    if sx >= 0.35 or sy >= 0.35 or sz >= 0.35:
        return ROLE_FRAME
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    seats = [member for member in members if member.get("role") == ROLE_SEAT]
    if not seats:
        return {}
    floor_z = -float(family_dims[2]) * 0.5
    seat_tops = [float(member["maxs"][2]) - floor_z for member in seats]
    return {"seat_height": sum(seat_tops) / len(seat_tops)}


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    role = role or ROLE_UNKNOWN

    if role == ROLE_LEG:
        if axis in {"X", "Y"}:
            return "MOVE"
        if axis == "Z":
            return "STRETCH"

    if role == ROLE_SEAT:
        if axis in {"X", "Y"}:
            return "STRETCH"
        if axis == "Z":
            return "MOVE"

    if role == ROLE_BACK:
        if axis == "X":
            return "STRETCH"
        if axis == "Y":
            return "MOVE"
        if axis == "Z":
            return "STRETCH"

    if role == ROLE_ARM:
        if axis in {"X", "Y"}:
            return "MOVE"
        if axis == "Z":
            return "STRETCH"

    if role == ROLE_FRAME:
        if axis in {"X", "Y"}:
            return "STRETCH" if span_ratio >= 0.38 else "MOVE"
        if axis == "Z":
            return "STRETCH" if span_ratio >= 0.45 else "MOVE"

    if role == ROLE_DECOR:
        return "MOVE"

    if axis in {"X", "Y"}:
        if name_has(name, "leg", "post", "arm") or edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.38 else "FIXED"
    if axis == "Z":
        if name_has(name, "seat"):
            return "MOVE"
        if name_has(name, "leg", "back", "post") or span_ratio >= 0.50:
            return "STRETCH"
    return "FIXED"
