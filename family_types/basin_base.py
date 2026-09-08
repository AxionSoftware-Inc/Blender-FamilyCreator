from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name="", editable_axes=("X", "Y")):
    if axis not in editable_axes:
        return "FIXED"
    if name_has(name, "drain", "tap", "faucet", "mixer"):
        return "MOVE" if center_ratio >= 0.20 else "FIXED"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.42 else "FIXED"
