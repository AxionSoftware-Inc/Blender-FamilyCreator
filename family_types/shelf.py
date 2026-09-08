from .casework_base import infer_rule as _casework_rule


def infer_rule(axis, span_ratio, center_ratio, name=""):
    return _casework_rule(axis, span_ratio, center_ratio, name, editable_axes=("X", "Y", "Z"))
