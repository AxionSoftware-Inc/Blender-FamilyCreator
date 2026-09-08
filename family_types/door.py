from .opening_base import infer_rule as _opening_rule


def infer_rule(axis, span_ratio, center_ratio, name=""):
    return _opening_rule(axis, span_ratio, center_ratio, name)
