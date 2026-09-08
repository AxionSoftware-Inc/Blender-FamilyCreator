from . import core


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
}


def _source_members(root):
    return [
        obj
        for obj in core.family_members(root)
        if not bool(obj.get(core.GENERATED_FLAG, False))
    ]


def validate_family(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    members = _source_members(root)
    roles = [getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN" for obj in members]
    role_counts = {}
    for role in roles:
        role_counts[role] = role_counts.get(role, 0) + 1

    known = sum(count for role, count in role_counts.items() if role != "UNKNOWN")
    total = len(members)
    coverage = float(known) / float(total) if total else 0.0

    required_groups = REQUIRED_ROLE_GROUPS.get(family_kind, ())
    missing_groups = []
    for alternatives in required_groups:
        if not any(role_counts.get(role, 0) > 0 for role in alternatives):
            missing_groups.append(list(alternatives))

    warnings = []
    errors = []
    if total == 0:
        errors.append("Family has no source geometry members")
    if coverage < 0.65 and total > 0:
        warnings.append(f"Only {coverage:.0%} of source members have semantic roles")
    if missing_groups:
        for group in missing_groups:
            errors.append("Missing required role: " + " or ".join(group))

    requirement_score = 1.0 if not required_groups else (
        float(len(required_groups) - len(missing_groups)) / float(len(required_groups))
    )
    score = int(round((coverage * 60.0) + (requirement_score * 40.0)))
    ready = not errors

    return {
        "familyKind": family_kind,
        "ready": ready,
        "score": score,
        "sourceMembers": total,
        "roleCoverage": coverage,
        "roleCounts": role_counts,
        "missingRoleGroups": missing_groups,
        "warnings": warnings,
        "errors": errors,
    }
