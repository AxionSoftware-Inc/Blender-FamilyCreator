from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name=""):
    if axis != "X":
        return "FIXED"
    if name_has(name, "arm", "side", "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.28 else "FIXED"
