from .fixture_base import fixed_rule


def infer_rule(axis, span_ratio, center_ratio, name=""):
    return fixed_rule(axis, span_ratio, center_ratio, name)
