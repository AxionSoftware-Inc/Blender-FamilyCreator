from .common import edge_member, name_has


def infer_rule(axis, span_ratio, center_ratio, name=""):
    if axis in {"X", "Y"}:
        if name_has(name, "leg", "foot", "post") or edge_member(span_ratio, center_ratio):
            return "MOVE"
        return "STRETCH" if span_ratio >= 0.34 else "FIXED"
    if axis == "Z":
        if name_has(name, "top", "surface", "slab") or (span_ratio <= 0.28 and center_ratio >= 0.45):
            return "MOVE"
        if name_has(name, "leg", "post", "frame") or span_ratio >= 0.48:
            return "STRETCH"
    return "FIXED"
