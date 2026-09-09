from .common import edge_member, name_has


ROLE_UNKNOWN = "UNKNOWN"
ROLE_MATTRESS = "MATTRESS"
ROLE_BASE = "BASE"
ROLE_HEADBOARD = "HEADBOARD"
ROLE_FOOTBOARD = "FOOTBOARD"
ROLE_LEG = "LEG"
ROLE_SLAT = "SLAT"
ROLE_DECOR = "DECOR"


def classify_role(spans, centers, name=""):
    sx, sy, sz = spans
    cx, cy, cz = centers

    if name_has(name, "mattress", "bed_pad", "cushion"):
        return ROLE_MATTRESS
    if name_has(name, "headboard", "head_board", "head"):
        return ROLE_HEADBOARD
    if name_has(name, "footboard", "foot_board"):
        return ROLE_FOOTBOARD
    if name_has(name, "leg", "foot", "feet"):
        return ROLE_LEG
    if name_has(name, "slat", "lath"):
        return ROLE_SLAT
    if name_has(name, "base", "frame", "platform"):
        return ROLE_BASE
    if name_has(name, "pillow", "blanket", "duvet", "decor"):
        return ROLE_DECOR

    # Vendor assets commonly use generic names such as Cube.014.  The original
    # mattress fallback required cz >= 0, which is too strict when a tall
    # headboard shifts the family envelope upward.  Prefer the upper broad,
    # shallow horizontal slab as the mattress while keeping lower broad slabs
    # as the bed base/platform.
    if sx >= 0.52 and sy >= 0.52 and sz <= 0.48:
        if cz >= -0.32:
            return ROLE_MATTRESS
        return ROLE_BASE

    if sx >= 0.50 and sy <= 0.24 and sz >= 0.42 and abs(cy) >= 0.42:
        return ROLE_HEADBOARD if cy >= 0.0 else ROLE_FOOTBOARD
    if sx <= 0.24 and sy <= 0.24 and sz <= 0.50 and abs(cx) >= 0.45 and abs(cy) >= 0.45:
        return ROLE_LEG
    if sx >= 0.45 and sy <= 0.22 and sz <= 0.24:
        return ROLE_SLAT
    if sx >= 0.45 and sy >= 0.45:
        return ROLE_BASE
    return ROLE_UNKNOWN


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def refine_roles(members, family_dims):
    """Select a mattress from broad horizontal candidates when pass one misses it.

    Real beds can have a tall headboard, joined bedding and a low origin that
    make one-object bbox thresholds ambiguous.  This pass compares all broad
    candidates and promotes only the strongest *relative* upper slab.  Explicit
    bedding/decor and structural names remain protected, and a sole BASE is not
    silently relabeled as a mattress.
    """
    refined = [dict(member) for member in members]
    if any(member.get("role") == ROLE_MATTRESS for member in refined):
        return refined

    candidates = []
    for index, member in enumerate(refined):
        role = member.get("role", ROLE_UNKNOWN)
        if role not in {ROLE_UNKNOWN, ROLE_BASE}:
            continue

        name = str(member.get("name", "") or "")
        if name_has(
            name,
            "head",
            "footboard",
            "leg",
            "slat",
            "pillow",
            "blanket",
            "duvet",
            "decor",
        ):
            continue

        sx, sy, sz = member.get("normalized_span", (0.0, 0.0, 0.0))
        _cx, _cy, cz = member.get("normalized_center", (0.0, 0.0, 0.0))
        sx, sy, sz, cz = map(float, (sx, sy, sz, cz))
        if sx < 0.32 or sy < 0.32 or sz < 0.05 or sz > 0.70:
            continue

        footprint = sx * sy
        top_edge = cz + sz
        flatness = min(sx, sy) / max(sz, 1e-9)
        top_score = _clamp01((top_edge + 0.75) / 1.75)
        flat_score = _clamp01((flatness - 0.8) / 3.2)
        footprint_score = _clamp01(footprint / 0.55)
        thickness_score = _clamp01(1.0 - abs(sz - 0.24) / 0.45)
        score = (
            footprint_score * 0.40
            + top_score * 0.30
            + flat_score * 0.20
            + thickness_score * 0.10
        )
        candidates.append({
            "index": index,
            "role": role,
            "score": score,
            "top": top_edge,
            "footprint": footprint,
            "thickness": sz,
        })

    if not candidates:
        return refined

    candidates.sort(key=lambda item: (item["score"], item["top"]), reverse=True)
    best = candidates[0]
    if best["score"] < 0.52:
        return refined

    if len(candidates) == 1:
        # A single broad BASE can be a mattress-less bed frame; keep review in
        # that case. Only promote a lone unresolved upper slab.
        if (
            best["role"] != ROLE_UNKNOWN
            or best["footprint"] < 0.28
            or best["thickness"] > 0.42
            or best["top"] < -0.05
        ):
            return refined
    else:
        runner_up = candidates[1]
        relative_separation = (
            best["top"] - runner_up["top"] >= 0.06
            or best["score"] - runner_up["score"] >= 0.06
        )
        if not relative_separation and best["role"] != ROLE_UNKNOWN:
            return refined

    refined[best["index"]]["role"] = ROLE_MATTRESS
    refined[best["index"]]["roleRefinement"] = "BED_MATTRESS_CANDIDATE"
    return refined


def infer_semantic_parameters(members, family_dims):
    mattresses = [member for member in members if member.get("role") == ROLE_MATTRESS]
    if not mattresses:
        return {}
    heights = [abs(float(member["span"][2])) for member in mattresses]
    return {"mattress_height": sum(heights) / len(heights)}


def infer_rule(axis, span_ratio, center_ratio, name="", role=None):
    if axis not in {"X", "Y"}:
        return "FIXED"

    role = role or ROLE_UNKNOWN

    if role in {ROLE_MATTRESS, ROLE_BASE}:
        return "STRETCH"
    if role in {ROLE_HEADBOARD, ROLE_FOOTBOARD}:
        return "STRETCH" if axis == "X" else "MOVE"
    if role == ROLE_LEG:
        return "MOVE"
    if role == ROLE_SLAT:
        return "STRETCH" if axis == "X" else "MOVE"
    if role == ROLE_DECOR:
        return "MOVE"

    if axis == "Y" and name_has(name, "head", "foot", "headboard", "footboard"):
        return "MOVE"
    if name_has(name, "leg", "foot") or edge_member(span_ratio, center_ratio):
        return "MOVE"
    return "STRETCH" if span_ratio >= 0.34 else "FIXED"
