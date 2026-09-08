from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name="", editable_axes=("X", "Y", "Z")):
    if axis not in editable_axes:
        return "FIXED"
    if name_has(name, "handle", "hinge", "knob", "hardware"):
        return "MOVE" if center_ratio >= 0.25 else "FIXED"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    if span_ratio >= 0.46:
        return "STRETCH"
    return "FIXED"
