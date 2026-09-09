from . import (
    bathtub,
    bed,
    cabinet,
    chair,
    door,
    kitchen_base,
    kitchen_wall,
    shelf,
    sink,
    sofa,
    stair,
    table,
    toilet,
    wardrobe,
    window,
)


GENERATORS = {
    "SOFA": sofa,
    "TABLE": table,
    "CHAIR": chair,
    "BED": bed,
    "CABINET": cabinet,
    "WARDROBE": wardrobe,
    "SHELF": shelf,
    "KITCHEN_BASE": kitchen_base,
    "KITCHEN_WALL": kitchen_wall,
    "DOOR": door,
    "WINDOW": window,
    "STAIR": stair,
    "TOILET": toilet,
    "SINK": sink,
    "BATHTUB": bathtub,
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
