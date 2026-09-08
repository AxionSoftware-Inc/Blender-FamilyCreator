from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name=""):
    if axis in {"X", "Y"}:
        if name_has(name, "leg", "post", "arm") or edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.38 else "FIXED"
    if axis == "Z":
        if name_has(name, "seat"):
            return "MOVE"
        if name_has(name, "leg", "back", "post") or span_ratio >= 0.50:
            return "STRETCH"
    return "FIXED"
