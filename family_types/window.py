import re

from .opening_base import (
    ROLE_FRAME_HEAD,
    ROLE_FRAME_LEFT,
    ROLE_FRAME_RIGHT,
    ROLE_FRAME_SILL,
    ROLE_GLASS,
    classify_role as _classify_opening_role,
    infer_rule as _opening_rule,
    infer_semantic_parameters as _infer_opening_parameters,
)


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

    # Only generic vendor names use the geometry-only glazing fallback. Explicit
    # semantic names such as "sash" must remain WINDOW_SASH.
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


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def _candidate_score(member, target):
    sx, _sy, sz = (float(value) for value in member.get("normalized_span", (0.0, 0.0, 0.0)))
    cx, _cy, cz = (float(value) for value in member.get("normalized_center", (0.0, 0.0, 0.0)))

    if target in {ROLE_FRAME_LEFT, ROLE_FRAME_RIGHT}:
        if target == ROLE_FRAME_LEFT and cx >= -0.20:
            return None
        if target == ROLE_FRAME_RIGHT and cx <= 0.20:
            return None
        if sx > 0.55 or sz < 0.22:
            return None
        orientation = sz / max(sx, 1e-9)
        if orientation < 1.15:
            return None
        edge_score = _clamp01((abs(cx) - 0.20) / 0.75)
        orientation_score = _clamp01((orientation - 1.0) / 2.5)
        size_score = _clamp01(sz / 0.55)
        return edge_score * 0.50 + orientation_score * 0.35 + size_score * 0.15

    if target in {ROLE_FRAME_HEAD, ROLE_FRAME_SILL}:
        if target == ROLE_FRAME_HEAD and cz <= 0.20:
            return None
        if target == ROLE_FRAME_SILL and cz >= -0.20:
            return None
        if sz > 0.55 or sx < 0.22:
            return None
        orientation = sx / max(sz, 1e-9)
        if orientation < 1.15:
            return None
        edge_score = _clamp01((abs(cz) - 0.20) / 0.75)
        orientation_score = _clamp01((orientation - 1.0) / 2.5)
        size_score = _clamp01(sx / 0.55)
        return edge_score * 0.50 + orientation_score * 0.35 + size_score * 0.15
    return None


def refine_roles(members, family_dims):
    """Fill missing window frame edges from family-level candidate comparison.

    First-pass bbox thresholds work well for clean semantic parts but vendor
    windows often use wider casing/trim pieces with generic Cube.xxx names. This
    pass preserves every confident role, then fills only missing frame edges
    from UNKNOWN parts (or generic WINDOW_SASH parts) that are strongly aligned
    with the corresponding family envelope edge. Explicit sash semantics and
    GLASS are never repurposed as frame members.
    """
    refined = [dict(member) for member in members]
    present = {str(member.get("role", "UNKNOWN") or "UNKNOWN") for member in refined}
    targets = (ROLE_FRAME_LEFT, ROLE_FRAME_RIGHT, ROLE_FRAME_HEAD, ROLE_FRAME_SILL)
    used = set()

    for target in targets:
        if target in present:
            continue

        scored = []
        for index, member in enumerate(refined):
            if index in used:
                continue
            role = str(member.get("role", "UNKNOWN") or "UNKNOWN")
            name = member.get("name", "")
            if role == "UNKNOWN":
                pass
            elif role == ROLE_WINDOW_SASH and _is_generic_name(name):
                pass
            else:
                continue

            score = _candidate_score(member, target)
            if score is not None:
                scored.append((score, index))

        if not scored:
            continue
        scored.sort(reverse=True)
        score, index = scored[0]
        if score < 0.56:
            continue

        # When two candidates are nearly tied for one edge, keep the asset in
        # review instead of guessing. Symmetric left/right members are handled
        # naturally because their center signs target different roles.
        if len(scored) > 1 and score - scored[1][0] < 0.035:
            continue

        refined[index]["role"] = target
        refined[index]["roleRefinement"] = "WINDOW_FRAME_EDGE_CANDIDATE"
        used.add(index)
        present.add(target)

    return refined


def infer_semantic_parameters(members, family_dims):
    return _infer_opening_parameters(members, family_dims)


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    return _opening_rule(axis, span_ratio, center_ratio, name=name, role=role)
