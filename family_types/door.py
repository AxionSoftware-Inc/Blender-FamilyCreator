from .opening_base import classify_role as _classify_opening_role
from .opening_base import infer_rule as _opening_rule
from .opening_base import infer_semantic_parameters as _infer_opening_parameters


ROLE_DOOR_LEAF = "DOOR_LEAF"


def classify_role(spans, centers, name=""):
    return _classify_opening_role(spans, centers, name=name, panel_role=ROLE_DOOR_LEAF)


def infer_semantic_parameters(members, family_dims):
    return _infer_opening_parameters(members, family_dims)


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    return _opening_rule(axis, span_ratio, center_ratio, name=name, role=role)
