from .basin_base import (
    ROLE_TUB,
    classify_role as _classify_role,
    infer_rule as _basin_rule,
    infer_semantic_parameters as _infer_semantic_parameters,
)


def classify_role(spans, centers, name=""):
    return _classify_role(spans, centers, name=name, body_role=ROLE_TUB)


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    return _basin_rule(
        axis,
        span_ratio,
        center_ratio,
        name,
        editable_axes=("X", "Y"),
        role=role,
    )


def infer_semantic_parameters(members, family_dims):
    return _infer_semantic_parameters(members, family_dims, body_role=ROLE_TUB)
