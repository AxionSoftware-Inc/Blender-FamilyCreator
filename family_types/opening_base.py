from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name=""):
    if axis not in {"X", "Z"}:
        return "FIXED"
    if name_has(name, "handle", "hinge", "lock"):
        return "MOVE"
    if name_has(name, "jamb", "frame", "mullion", "rail", "stile") and edge_member(span_ratio, center_ratio):
        return "MOVE"
    if edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.36 else "FIXED"
