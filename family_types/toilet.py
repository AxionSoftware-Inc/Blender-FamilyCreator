from .common import name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_BOWL = "BOWL"
ROLE_TANK = "TANK"
ROLE_SEAT = "SEAT"
ROLE_LID = "LID"
ROLE_BASE = "BASE"
ROLE_CONNECTOR = "CONNECTOR"
ROLE_FLUSH = "FLUSH"
ROLE_HARDWARE = "HARDWARE"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "connector", "outlet", "waste", "trap", "pipe", "drain"):
        return ROLE_CONNECTOR
    if name_has(name, "flush", "button", "lever"):
        return ROLE_FLUSH
    if name_has(name, "lid", "cover"):
        return ROLE_LID
    if name_has(name, "seat", "ring"):
        return ROLE_SEAT
    if name_has(name, "tank", "cistern"):
        return ROLE_TANK
    if name_has(name, "bowl", "pan"):
        return ROLE_BOWL
    if name_has(name, "base", "pedestal", "foot"):
        return ROLE_BASE
    if name_has(name, "hinge", "hardware", "bolt"):
        return ROLE_HARDWARE

    # Geometry-only fallbacks. A broad lower body is usually the bowl/base;
    # a rear upper volume is usually the cistern. Thin upper members are seat/lid.
    if sx >= 0.40 and sy >= 0.45 and sz >= 0.30 and cz <= 0.15:
        return ROLE_BOWL
    if sx >= 0.35 and sy <= 0.45 and sz >= 0.35 and abs(cy) >= 0.30 and cz >= 0.20:
        return ROLE_TANK
    if sx >= 0.35 and sy >= 0.40 and sz <= 0.14 and cz >= 0.05:
        return ROLE_SEAT
    if sx <= 0.20 and sy <= 0.20 and sz <= 0.25 and abs(cy) >= 0.25:
        return ROLE_CONNECTOR
    if sx >= 0.25 and sy >= 0.25 and cz <= -0.25:
        return ROLE_BASE
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    # Toilet geometry stays fixed-proportion. Connector height is handled by
    # its semantic generator rather than scaling the fixture body.
    return "FIXED"


def infer_semantic_parameters(members, family_dims):
    connectors = [member for member in members if member.get("role") == ROLE_CONNECTOR]
    if not connectors:
        return {}

    base_height = float(family_dims[2])
    heights = []
    for member in connectors:
        center = member.get("center", (0.0, 0.0, 0.0))
        heights.append(float(center[2]) + base_height * 0.5)
    return {"connector_height": max(min(heights), base_height) if heights else 0.0}
