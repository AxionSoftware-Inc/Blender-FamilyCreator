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


def _median(values):
    values = sorted(float(v) for v in values if float(v) > 0.0)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) * 0.5


def _vertical_frame_like(sx, sz):
    return sx <= 0.36 and sz >= 0.35 and sx <= sz * 0.65


def _horizontal_frame_like(sx, sz):
    return sz <= 0.36 and sx >= 0.35 and sz <= sx * 0.65


def _frame_named(name):
    # Vendor assets frequently contain truncated/typo variants such as
    # "L fram _Part_02". Keep this narrower than a raw "fram" substring so
    # unrelated words do not become frame semantics.
    return name_has(name, "jamb", "stile", "frame", "casing", " fram ", "fram_", "fram-")


def classify_role(spans, centers, name="", panel_role=ROLE_PANEL):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "handle", "lever", "knob"):
        return ROLE_HANDLE
    if name_has(name, "hinge"):
        return ROLE_HINGE
    if name_has(name, "lock", "latch", "hardware", "bolt", "screw", "fastener", "clip"):
        return ROLE_HARDWARE
    if name_has(name, "glass", "glazing", "pane"):
        return ROLE_GLASS
    if name_has(name, "mullion", "muntin"):
        return ROLE_MULLION
    if name_has(name, "panel", "leaf", "door_leaf", "sash"):
        return panel_role

    if _frame_named(name):
        # A semantic frame-ish name is stronger evidence than geometry alone,
        # so allow a slightly more interior center than the generic fallback.
        # This covers curved/L-shaped frames whose bbox center is not at the
        # extreme family edge while retaining orientation checks.
        if abs(cx) >= 0.26 and _vertical_frame_like(sx, sz):
            return ROLE_FRAME_LEFT if cx < 0.0 else ROLE_FRAME_RIGHT
        if cz >= 0.26 and _horizontal_frame_like(sx, sz):
            return ROLE_FRAME_HEAD
        if cz <= -0.26 and _horizontal_frame_like(sx, sz):
            return ROLE_FRAME_SILL

    if name_has(name, "head", "header"):
        return ROLE_FRAME_HEAD
    if name_has(name, "sill", "threshold"):
        return ROLE_FRAME_SILL

    # Geometry-only fallback for BlenderKit/vendor assets with names like
    # Cube, Cube.001, Object.003. Imported frame profiles are often wider than
    # the old 20% thresholds, but still have a strong vertical/horizontal
    # aspect ratio. Combining edge position with dominant orientation avoids
    # mistaking half-width sash/pane objects for side frames.
    if abs(cx) >= 0.38 and _vertical_frame_like(sx, sz):
        return ROLE_FRAME_LEFT if cx < 0.0 else ROLE_FRAME_RIGHT
    if cz >= 0.38 and _horizontal_frame_like(sx, sz):
        return ROLE_FRAME_HEAD
    if cz <= -0.38 and _horizontal_frame_like(sx, sz):
        return ROLE_FRAME_SILL

    # Central vertical or horizontal bars are both represented as MULLION. The
    # rule inference below uses the member's span per axis to decide which axis
    # stretches and which one moves, so horizontal muntins do not need a
    # separate semantic role.
    if abs(cx) < 0.45 and sx <= 0.24 and sz >= 0.40 and sx <= sz * 0.55:
        return ROLE_MULLION
    if abs(cz) < 0.45 and sz <= 0.24 and sx >= 0.40 and sz <= sx * 0.55:
        return ROLE_MULLION

    # Tiny opening parts are commonly bolts, clips, glazing retainers or other
    # hardware. Treating them as HARDWARE is safer than stretching them as
    # structural members and materially improves vendor-model role coverage.
    if sx <= 0.10 and sz <= 0.15 and sy <= 0.35:
        return ROLE_HARDWARE

    if sx >= 0.35 and sz >= 0.35:
        return panel_role
    return ROLE_UNKNOWN


def infer_semantic_parameters(members, family_dims):
    frame_widths = []
    panel_thicknesses = []

    for member in members:
        role = member.get("role")
        span = member.get("span", (0.0, 0.0, 0.0))
        if role in {ROLE_FRAME_LEFT, ROLE_FRAME_RIGHT, ROLE_MULLION}:
            # For horizontal muntins X can be the long axis; use the smaller
            # profile dimension between X/Z when available.
            x = abs(float(span[0]))
            z = abs(float(span[2]))
            frame_widths.append(min(x, z) if x > 0.0 and z > 0.0 else max(x, z))
        elif role in {ROLE_FRAME_HEAD, ROLE_FRAME_SILL}:
            frame_widths.append(abs(float(span[2])))
        elif role in {ROLE_PANEL, "DOOR_LEAF", "WINDOW_SASH"}:
            panel_thicknesses.append(abs(float(span[1])))

    values = {}
    frame_width = _median(frame_widths)
    panel_thickness = _median(panel_thicknesses)
    if frame_width is not None:
        values["frame_width"] = frame_width
    if panel_thickness is not None:
        values["panel_thickness"] = panel_thickness
    return values


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
        # Orientation-aware without adding another role: the long axis stretches
        # while the short/offset axis moves with the opening.
        return "STRETCH" if span_ratio >= 0.40 else "MOVE"
    if role in {ROLE_PANEL, ROLE_GLASS, "DOOR_LEAF", "WINDOW_SASH"}:
        return "STRETCH"

    if name_has(name, "handle", "hinge", "lock", "bolt", "screw", "fastener", "clip"):
        return "MOVE"
    if (_frame_named(name) or name_has(name, "mullion", "rail")) and edge_member(span_ratio, center_ratio):
        return "MOVE"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.36 else "FIXED"
