from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_FRAME_LEFT = "FRAME_LEFT"
ROLE_FRAME_RIGHT = "FRAME_RIGHT"
ROLE_FRAME_HEAD = "FRAME_HEAD"
ROLE_FRAME_SILL = "FRAME_SILL"
ROLE_PANEL = "PANEL"
ROLE_GLASS = "GLASS"
ROLE_MULLION = "MULLION"
ROLE_HANDLE = "HANDLE"
ROLE_HINGE = "HINGE"
ROLE_HARDWARE = "HARDWARE"


def classify_role(spans, centers, name="", panel_role=ROLE_PANEL):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "handle", "lever", "knob"):
        return ROLE_HANDLE
    if name_has(name, "hinge"):
        return ROLE_HINGE
    if name_has(name, "lock", "latch", "hardware"):
        return ROLE_HARDWARE
    if name_has(name, "glass", "glazing", "pane"):
        return ROLE_GLASS
    if name_has(name, "mullion", "muntin"):
        return ROLE_MULLION
    if name_has(name, "panel", "leaf", "door_leaf", "sash"):
        return panel_role

    if name_has(name, "jamb", "stile", "frame", "casing"):
        if abs(cx) >= 0.45 and sx <= 0.35:
            return ROLE_FRAME_LEFT if cx < 0.0 else ROLE_FRAME_RIGHT
        if cz >= 0.45 and sz <= 0.35:
            return ROLE_FRAME_HEAD
        if cz <= -0.45 and sz <= 0.35:
            return ROLE_FRAME_SILL

    if name_has(name, "head", "header"):
        return ROLE_FRAME_HEAD
    if name_has(name, "sill", "threshold"):
        return ROLE_FRAME_SILL

    # Geometry fallback for generic imported object names.
    if sx <= 0.20 and sz >= 0.55 and abs(cx) >= 0.55:
        return ROLE_FRAME_LEFT if cx < 0.0 else ROLE_FRAME_RIGHT
    if sx >= 0.55 and sz <= 0.20 and cz >= 0.50:
        return ROLE_FRAME_HEAD
    if sx >= 0.55 and sz <= 0.20 and cz <= -0.50:
        return ROLE_FRAME_SILL
    if sx <= 0.18 and sz >= 0.50:
        return ROLE_MULLION
    if sx >= 0.45 and sz >= 0.45:
        return panel_role
    return ROLE_UNKNOWN


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    if axis not in {"X", "Z"}:
        return "FIXED"

    role = role or ROLE_UNKNOWN

    if role in {ROLE_HANDLE, ROLE_HINGE, ROLE_HARDWARE}:
        return "MOVE"
    if role in {ROLE_FRAME_LEFT, ROLE_FRAME_RIGHT}:
        return "MOVE" if axis == "X" else "STRETCH"
    if role in {ROLE_FRAME_HEAD, ROLE_FRAME_SILL}:
        return "STRETCH" if axis == "X" else "MOVE"
    if role == ROLE_MULLION:
        return "MOVE" if axis == "X" else "STRETCH"
    if role in {ROLE_PANEL, ROLE_GLASS, "DOOR_LEAF", "WINDOW_SASH"}:
        return "STRETCH"

    if name_has(name, "handle", "hinge", "lock"):
        return "MOVE"
    if name_has(name, "jamb", "frame", "mullion", "rail", "stile") and edge_member(span_ratio, center_ratio):
        return "MOVE"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.36 else "FIXED"
