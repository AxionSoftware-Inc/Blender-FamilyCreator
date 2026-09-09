import re

from .opening_base import ROLE_GLASS
from .opening_base import classify_role as _classify_opening_role
from .opening_base import infer_rule as _opening_rule
from .opening_base import infer_semantic_parameters as _infer_opening_parameters


ROLE_WINDOW_SASH = "WINDOW_SASH"
_GENERIC_OBJECT_NAME = re.compile(
    r"^(?:cube|object|mesh|plane|cylinder|sphere|cone|curve|circle)(?:[._ -]?\d+)?$",
    re.IGNORECASE,
)


def _is_generic_name(name):
    value = str(name or "").strip()
    return not value or bool(_GENERIC_OBJECT_NAME.match(value))


def classify_role(spans, centers, name=""):
    role = _classify_opening_role(spans, centers, name=name, panel_role=ROLE_WINDOW_SASH)

    # When names are generic, a broad X/Z member with very small depth is much
    # more likely to be glazing than a structural sash.  This distinction is
    # optional for readiness (WINDOW_SASH is also valid), but it improves role
    # coverage and material/runtime semantics for BlenderKit-style assets.
    sx, sy, sz = spans
    if (
        role == ROLE_WINDOW_SASH
        and _is_generic_name(name)
        and sy <= 0.18
        and sx >= 0.40
        and sz >= 0.40
    ):
        return ROLE_GLASS
    return role


def infer_semantic_parameters(members, family_dims):
    return _infer_opening_parameters(members, family_dims)


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    return _opening_rule(axis, span_ratio, center_ratio, name=name, role=role)
