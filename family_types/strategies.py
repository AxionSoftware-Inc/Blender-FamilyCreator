from .registry import get_family_type


def _generic_rule(span_ratio, center_ratio):
    if span_ratio >= 0.62:
        return "STRETCH"
    if span_ratio <= 0.38 and center_ratio >= 0.34:
        return "MOVE"
    return "FIXED"


def _name_has(name, *tokens):
    value = (name or "").lower()
    return any(token in value for token in tokens)


def _edge_member(span_ratio, center_ratio):
    return span_ratio <= 0.42 and center_ratio >= 0.32


def _axis_enabled(type_id, axis):
    return axis in get_family_type(type_id).get("editable_axes", ())


def infer_member_rule(type_id, axis, span_ratio, center_ratio, name=""):
    spec = get_family_type(type_id)
    strategy = spec.get("strategy", "GENERIC")

    if not _axis_enabled(type_id, axis):
        return "FIXED"

    # Upholstered seating is primarily width-driven. Arms/side panels keep
    # thickness and move outward; seat/back/body regions stretch between them.
    if strategy == "SOFA":
        if axis != "X":
            return "FIXED"
        if _name_has(name, "arm", "side", "leg", "foot") or _edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.28 else "FIXED"

    # Tables preserve leg/post sections. Top/apron members grow in plan, while
    # legs move to the new corners. Height growth mostly belongs to legs/posts.
    if strategy == "TABLE":
        if axis in {"X", "Y"}:
            if _name_has(name, "leg", "foot", "post") or _edge_member(span_ratio, center_ratio):
                return "MOVE"
            return "STRETCH" if span_ratio >= 0.34 else "FIXED"
        if axis == "Z":
            if _name_has(name, "top", "surface", "slab") or (span_ratio <= 0.28 and center_ratio >= 0.45):
                return "MOVE"
            if _name_has(name, "leg", "post", "frame") or span_ratio >= 0.48:
                return "STRETCH"
            return "FIXED"

    if strategy == "CHAIR":
        if axis in {"X", "Y"}:
            if _name_has(name, "leg", "post", "arm") or _edge_member(span_ratio, center_ratio):
                return "MOVE"
            return "STRETCH" if span_ratio >= 0.38 else "FIXED"
        if axis == "Z":
            if _name_has(name, "seat"):
                return "MOVE"
            if _name_has(name, "leg", "back", "post") or span_ratio >= 0.5:
                return "STRETCH"
            return "FIXED"

    if strategy == "BED":
        if _name_has(name, "head", "foot", "headboard", "footboard") and axis == "Y":
            return "MOVE"
        if _name_has(name, "leg", "foot") or _edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.34 else "FIXED"

    # Casework treats thin edge panels as anchored members and the central
    # carcass/shelves as stretchable. This keeps panel thickness from scaling.
    if strategy == "CASEWORK":
        if _name_has(name, "handle", "hinge", "knob", "hardware"):
            return "MOVE" if center_ratio >= 0.25 else "FIXED"
        if _edge_member(span_ratio, center_ratio):
            return "MOVE"
        if span_ratio >= 0.46:
            return "STRETCH"
        return "FIXED"

    # Doors/windows vary in width and height but never by depth in this v1
    # profile. Frame edge pieces move; glazing/panel spans stretch.
    if strategy == "OPENING":
        if _name_has(name, "handle", "hinge", "lock"):
            return "MOVE"
        if _name_has(name, "jamb", "frame", "mullion", "rail", "stile") and _edge_member(span_ratio, center_ratio):
            return "MOVE"
        if _edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.36 else "FIXED"

    # Stair geometry needs discrete tread/riser generation. For v1 only stair
    # width is safely parameterized; run/rise will get its own generator.
    if strategy == "STAIR":
        if axis == "X":
            if _name_has(name, "rail", "stringer") and _edge_member(span_ratio, center_ratio):
                return "MOVE"
            return "STRETCH" if span_ratio >= 0.30 else "FIXED"
        return "FIXED"

    if strategy == "FIXED_FIXTURE":
        return "FIXED"

    if strategy == "BASIN":
        if _name_has(name, "drain", "tap", "faucet", "mixer"):
            return "MOVE" if center_ratio >= 0.20 else "FIXED"
        if _edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.42 else "FIXED"

    return _generic_rule(span_ratio, center_ratio)


def infer_member_rules(type_id, spans, centers, name=""):
    rules = {}
    for axis, span_ratio, center_ratio in zip(("X", "Y", "Z"), spans, centers):
        rules[axis] = infer_member_rule(type_id, axis, span_ratio, center_ratio, name=name)
    return rules
