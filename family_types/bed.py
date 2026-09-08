from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_MATTRESS = "MATTRESS"
ROLE_BASE = "BASE"
ROLE_HEADBOARD = "HEADBOARD"
ROLE_FOOTBOARD = "FOOTBOARD"
ROLE_LEG = "LEG"
ROLE_SLAT = "SLAT"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "mattress", "bed_pad", "cushion"):
        return ROLE_MATTRESS
    if name_has(name, "headboard", "head_board", "head"):
        return ROLE_HEADBOARD
    if name_has(name, "footboard", "foot_board"):
        return ROLE_FOOTBOARD
    if name_has(name, "leg", "foot", "feet"):
        return ROLE_LEG
    if name_has(name, "slat", "lath"):
        return ROLE_SLAT
    if name_has(name, "base", "frame", "platform"):
        return ROLE_BASE
    if name_has(name, "pillow", "blanket", "duvet", "decor"):
        return ROLE_DECOR

    if sx >= 0.60 and sy >= 0.60 and sz <= 0.35 and cz >= 0.0:
        return ROLE_MATTRESS
    if sx >= 0.55 and sy <= 0.20 and sz >= 0.45 and abs(cy) >= 0.55:
        return ROLE_HEADBOARD if cy >= 0.0 else ROLE_FOOTBOARD
    if sx <= 0.20 and sy <= 0.20 and sz <= 0.45 and abs(cx) >= 0.55 and abs(cy) >= 0.55:
        return ROLE_LEG
    if sx >= 0.55 and sy <= 0.18 and sz <= 0.20:
        return ROLE_SLAT
    if sx >= 0.50 and sy >= 0.50:
        return ROLE_BASE
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    mattresses = [member for member in members if member.get("role") == ROLE_MATTRESS]
    if not mattresses:
        return {}
    heights = [abs(float(member["span"][2])) for member in mattresses]
    return {"mattress_height": sum(heights) / len(heights)}


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    if axis not in {"X", "Y"}:
        return "FIXED"

    role = role or ROLE_UNKNOWN

    if role in {ROLE_MATTRESS, ROLE_BASE}:
        return "STRETCH"
    if role in {ROLE_HEADBOARD, ROLE_FOOTBOARD}:
        return "STRETCH" if axis == "X" else "MOVE"
    if role == ROLE_LEG:
        return "MOVE"
    if role == ROLE_SLAT:
        return "STRETCH" if axis == "X" else "MOVE"
    if role == ROLE_DECOR:
        return "MOVE"

    if axis == "Y" and name_has(name, "head", "foot", "headboard", "footboard"):
        return "MOVE"
    if name_has(name, "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.34 else "FIXED"
