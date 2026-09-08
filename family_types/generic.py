from .common import generic_rule


def infer_rule(axis, span_ratio, center_ratio, name=""):
    return generic_rule(span_ratio, center_ratio)
