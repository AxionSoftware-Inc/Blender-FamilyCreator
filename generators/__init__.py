from . import shelf, sofa, stair


GENERATORS = {
    "SOFA": sofa,
    "SHELF": shelf,
    "STAIR": stair,
}


def generator_for(family_kind):
    return GENERATORS.get(family_kind)


def supports_generation(family_kind):
    return family_kind in GENERATORS


def rebuild_family_geometry(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    generator = generator_for(family_kind)
    if generator is None:
        return {
            "familyKind": family_kind,
            "supported": False,
            "changed": False,
            "message": f"No procedural generator yet for {family_kind}",
        }
    result = generator.rebuild(root)
    result.setdefault("familyKind", family_kind)
    result.setdefault("supported", True)
    return result
