from .casework_base import classify_role as _classify_casework_role
from .casework_base import infer_rule as _casework_rule
from .casework_base import infer_semantic_parameters as _infer_casework_parameters


def classify_role(spans, centers, name=""):
    return _classify_casework_role(spans, centers, name=name)


def infer_semantic_parameters(members, family_dims):
    return _infer_casework_parameters(members, family_dims)


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    return _casework_rule(
        axis,
        span_ratio,
        center_ratio,
        name=name,
        editable_axes=("X", "Y", "Z"),
        role=role,
    )
