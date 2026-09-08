from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_TOP = "TOP"
ROLE_LEG = "LEG"
ROLE_APRON = "APRON"
ROLE_SUPPORT = "SUPPORT"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "leg", "foot", "feet", "post"):
        return ROLE_LEG
    if name_has(name, "top", "tabletop", "surface", "slab", "worktop"):
        return ROLE_TOP
    if name_has(name, "apron", "skirt", "rail"):
        return ROLE_APRON
    if name_has(name, "brace", "support", "crossbar", "stretcher"):
        return ROLE_SUPPORT
    if name_has(name, "decor", "cap", "plug"):
        return ROLE_DECOR

    if sz <= 0.18 and sx >= 0.60 and sy >= 0.45 and cz >= 0.35:
        return ROLE_TOP
    if sx <= 0.22 and sy <= 0.22 and sz >= 0.50:
        return ROLE_LEG
    if sz <= 0.25 and cz >= 0.15 and ((sx >= 0.50 and sy <= 0.25) or (sy >= 0.50 and sx <= 0.25)):
        return ROLE_APRON
    if (sx >= 0.45 or sy >= 0.45) and sz <= 0.30:
        return ROLE_SUPPORT
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    tops = [member for member in members if member.get("role") == ROLE_TOP]
    if not tops:
        return {}
    thicknesses = [abs(float(member["span"][2])) for member in tops]
    return {"top_thickness": sum(thicknesses) / len(thicknesses)}


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    role = role or ROLE_UNKNOWN

    if role == ROLE_TOP:
        if axis in {"X", "Y"}:
            return "STRETCH"
        if axis == "Z":
            return "MOVE"

    if role == ROLE_LEG:
        if axis in {"X", "Y"}:
            return "MOVE"
        if axis == "Z":
            return "STRETCH"

    if role in {ROLE_APRON, ROLE_SUPPORT}:
        if axis in {"X", "Y"}:
            return "STRETCH" if span_ratio >= 0.38 else "MOVE"
        if axis == "Z":
            return "MOVE"

    if role == ROLE_DECOR:
        return "MOVE"

    if axis in {"X", "Y"}:
        if name_has(name, "leg", "foot", "post") or edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.34 else "FIXED"
    if axis == "Z":
        if name_has(name, "top", "surface", "slab") or (span_ratio <= 0.28 and center_ratio >= 0.45):
            return "MOVE"
        if name_has(name, "leg", "post", "frame") or span_ratio >= 0.48:
            return "STRETCH"
    return "FIXED"
