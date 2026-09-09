from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_BASIN = "BASIN"
ROLE_TUB = "TUB"
ROLE_RIM = "RIM"
ROLE_DRAIN = "DRAIN"
ROLE_FAUCET = "FAUCET"
ROLE_OVERFLOW = "OVERFLOW"
ROLE_PEDESTAL = "PEDESTAL"
ROLE_CONNECTOR = "CONNECTOR"
ROLE_HARDWARE = "HARDWARE"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name="", body_role=ROLE_BASIN):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "drain", "waste", "strainer", "plug"):
        return ROLE_DRAIN
    if name_has(name, "overflow"):
        return ROLE_OVERFLOW
    if name_has(name, "faucet", "tap", "mixer", "spout"):
        return ROLE_FAUCET
    if name_has(name, "trap", "connector", "outlet", "inlet", "pipe"):
        return ROLE_CONNECTOR
    if name_has(name, "rim", "lip", "edge", "flange"):
        return ROLE_RIM
    if name_has(name, "pedestal", "stand", "column"):
        return ROLE_PEDESTAL
    if name_has(name, "handle", "knob", "hardware"):
        return ROLE_HARDWARE
    if name_has(name, "decor", "trim", "cover"):
        return ROLE_DECOR
    if body_role == ROLE_TUB and name_has(name, "tub", "bath", "bathtub", "body", "shell"):
        return ROLE_TUB
    if body_role == ROLE_BASIN and name_has(name, "basin", "bowl", "sink", "body", "shell"):
        return ROLE_BASIN

    # Geometry fallbacks for generic imported object names. Large plan members
    # form the main vessel; very shallow upper members are usually rims.
    if sx >= 0.55 and sy >= 0.55:
        if sz <= 0.16 and cz >= 0.30:
            return ROLE_RIM
        return body_role
    if sx <= 0.18 and sy <= 0.18 and sz <= 0.25 and abs(cx) <= 0.25 and abs(cy) <= 0.25:
        return ROLE_DRAIN
    if sz >= 0.35 and sx <= 0.40 and sy <= 0.40 and cz <= 0.15:
        return ROLE_PEDESTAL
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", editable_axes=("X", "Y"), role=None):
    if axis not in editable_axes:
        return "FIXED"

    role = role or ROLE_UNKNOWN
    if role in {ROLE_BASIN, ROLE_TUB, ROLE_RIM}:
        return "STRETCH"
    if role in {ROLE_DRAIN, ROLE_FAUCET, ROLE_OVERFLOW, ROLE_CONNECTOR, ROLE_HARDWARE, ROLE_DECOR}:
        return "MOVE" if center_ratio >= 0.20 else "FIXED"
    if role == ROLE_PEDESTAL:
        return "MOVE" if center_ratio >= 0.20 else "FIXED"

    if name_has(name, "drain", "tap", "faucet", "mixer"):
        return "MOVE" if center_ratio >= 0.20 else "FIXED"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.42 else "FIXED"


def infer_semantic_parameters(members, family_dims, body_role=ROLE_BASIN):
    values = {}
    drains = [member for member in members if member.get("role") == ROLE_DRAIN]
    if drains:
        diameters = []
        for member in drains:
            span = member.get("span", (0.0, 0.0, 0.0))
            candidates = [float(span[0]), float(span[1])]
            positive = [value for value in candidates if value > 1e-6]
            if positive:
                diameters.append(min(positive))
        if diameters:
            values["drain_diameter"] = min(diameters)

    rims = [member for member in members if member.get("role") == ROLE_RIM]
    if rims:
        thicknesses = []
        for member in rims:
            span = member.get("span", (0.0, 0.0, 0.0))
            positive = [float(value) for value in span if float(value) > 1e-6]
            if positive:
                thicknesses.append(min(positive))
        if thicknesses:
            values["rim_thickness"] = min(thicknesses)
    return values
