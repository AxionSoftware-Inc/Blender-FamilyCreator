from .basin_base import infer_rule as _basin_rule


def infer_rule(axis, span_ratio, center_ratio, name=""):
    return _basin_rule(axis, span_ratio, center_ratio, name, editable_axes=("X", "Y"))
