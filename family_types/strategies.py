from . import (
    bathtub,
    bed,
    cabinet,
    chair,
    door,
    generic,
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


STRATEGIES = {
    "GENERIC": generic,
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


def infer_member_rule(type_id, axis, span_ratio, center_ratio, name=""):
    module = STRATEGIES.get(type_id, generic)
    return module.infer_rule(axis, span_ratio, center_ratio, name=name)


def infer_member_rules(type_id, spans, centers, name=""):
    rules = {}
    for axis, span_ratio, center_ratio in zip(("X", "Y", "Z"), spans, centers):
        rules[axis] = infer_member_rule(type_id, axis, span_ratio, center_ratio, name=name)
    return rules
