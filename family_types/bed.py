from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name=""):
    if axis not in {"X", "Y"}:
        return "FIXED"
    if axis == "Y" and name_has(name, "head", "foot", "headboard", "footboard"):
        return "MOVE"
    if name_has(name, "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.34 else "FIXED"
