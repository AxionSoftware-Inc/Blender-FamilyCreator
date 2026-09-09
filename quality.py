from . import core
from .preflight import inspect_family


REQUIRED_ROLE_GROUPS = {
    "SOFA": (("SEAT",),),
    "TABLE": (("TOP",),),
    "CHAIR": (("SEAT",),),
    "BED": (("MATTRESS",),),
    "CABINET": (("SIDE_LEFT", "SIDE_RIGHT", "CARCASS", "TOP", "BOTTOM"),),
    "WARDROBE": (("SIDE_LEFT", "SIDE_RIGHT", "CARCASS", "TOP", "BOTTOM"),),
    "SHELF": (("SHELF",),),
    "KITCHEN_BASE": (("SIDE_LEFT", "SIDE_RIGHT", "CARCASS", "TOP", "BOTTOM"),),
    "KITCHEN_WALL": (("SIDE_LEFT", "SIDE_RIGHT", "CARCASS", "TOP", "BOTTOM"),),
    "DOOR": (("DOOR_LEAF", "PANEL"), ("FRAME_LEFT", "FRAME_RIGHT", "FRAME_HEAD")),
    "WINDOW": (("GLASS", "WINDOW_SASH", "PANEL"), ("FRAME_LEFT", "FRAME_RIGHT", "FRAME_HEAD")),
    "STAIR": (("TREAD",),),
    "TOILET": (("BOWL", "BASE"),),
    "SINK": (("BASIN",),),
    "BATHTUB": (("TUB",),),
}


RECOMMENDED_ROLE_GROUPS = {
    "SOFA": (("ARM_LEFT", "ARM_RIGHT", "ARM"),),
    "TABLE": (("LEG", "SUPPORT"),),
    "CHAIR": (("LEG", "FRAME"),),
    "BED": (("BASE",),),
    "DOOR": (("HANDLE", "HARDWARE", "HINGE"),),
    "WINDOW": (("GLASS",),),
    "STAIR": (("RISER", "STRINGER"),),
    "TOILET": (("CONNECTOR",),),
    "SINK": (("DRAIN", "CONNECTOR"),),
    "BATHTUB": (("RIM",), ("DRAIN", "CONNECTOR")),
}


def _source_members(root):
    return [
        obj
        for obj in core.family_members(root)
        if not bool(obj.get(core.GENERATED_FLAG, False))
    ]


def _missing_groups(role_counts, groups):
    missing = []
    for alternatives in groups:
        if not any(role_counts.get(role, 0) > 0 for role in alternatives):
            missing.append(list(alternatives))
    return missing


def validate_family(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    members = _source_members(root)
    roles = [getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN" for obj in members]
    role_counts = {}
    refinement_counts = {}
    for obj, role in zip(members, roles):
        role_counts[role] = role_counts.get(role, 0) + 1
        refinement = str(obj.get("bfc_role_refinement", "") or "").strip()
        if refinement:
            refinement_counts[refinement] = refinement_counts.get(refinement, 0) + 1

    known = sum(count for role, count in role_counts.items() if role != "UNKNOWN")
    total = len(members)
    coverage = float(known) / float(total) if total else 0.0

    required_groups = REQUIRED_ROLE_GROUPS.get(family_kind, ())
    recommended_groups = RECOMMENDED_ROLE_GROUPS.get(family_kind, ())
    missing_groups = _missing_groups(role_counts, required_groups)
    missing_recommended = _missing_groups(role_counts, recommended_groups)

    warnings = []
    errors = []
    if total == 0:
        errors.append("Family has no source geometry members")
    if coverage < 0.65 and total > 0:
        warnings.append(f"Only {coverage:.0%} of source members have semantic roles")
    for group in missing_groups:
        errors.append("Missing required role: " + " or ".join(group))
    for group in missing_recommended:
        warnings.append("Recommended role not detected: " + " or ".join(group))

    preflight = inspect_family(root)
    warnings.extend(preflight.get("warnings", ()))
    for message in preflight.get("severe", ()):
        warnings.append("Preflight: " + message)

    requirement_score = 1.0 if not required_groups else (
        float(len(required_groups) - len(missing_groups)) / float(len(required_groups))
    )
    recommendation_score = 1.0 if not recommended_groups else (
        float(len(recommended_groups) - len(missing_recommended)) / float(len(recommended_groups))
    )
    base_score = (coverage * 50.0) + (requirement_score * 40.0) + (recommendation_score * 10.0)
    preflight_penalty = min(
        25.0,
        len(preflight.get("warnings", ())) * 3.0 + len(preflight.get("severe", ())) * 10.0,
    )
    score = int(round(max(0.0, base_score - preflight_penalty)))
    ready = not errors
    review_recommended = bool(
        errors
        or missing_recommended
        or coverage < 0.80
        or preflight.get("reviewRecommended", False)
    )

    return {
        "familyKind": family_kind,
        "ready": ready,
        "automaticReady": ready and not review_recommended,
        "reviewRecommended": review_recommended,
        "score": score,
        "sourceMembers": total,
        "roleCoverage": coverage,
        "roleCounts": role_counts,
        "roleRefinementCounts": refinement_counts,
        "missingRoleGroups": missing_groups,
        "missingRecommendedRoleGroups": missing_recommended,
        "preflight": preflight,
        "warnings": warnings,
        "errors": errors,
    }
