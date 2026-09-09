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


def family_module(type_id):
    return STRATEGIES.get(type_id, generic)


def classify_member_role(type_id, spans, signed_centers, name=""):
    module = family_module(type_id)
    classifier = getattr(module, "classify_role", None)
    if classifier is None:
        return "UNKNOWN"
    return classifier(spans, signed_centers, name=name)


def refine_member_roles(type_id, members, family_dims):
    """Optionally refine per-member roles using the whole family context.

    First-pass classifiers intentionally remain cheap and local. Real vendor
    assets sometimes need family-level comparison (for example selecting the
    upper broad slab as a BED mattress, or filling missing WINDOW frame edges
    from otherwise ambiguous Cube.xxx parts). Class modules may implement
    ``refine_roles(members, family_dims)`` and return a list with the same
    length. Invalid/partial refinements are ignored rather than corrupting the
    first-pass result.
    """
    module = family_module(type_id)
    refinement = getattr(module, "refine_roles", None)
    if refinement is None:
        return members
    values = refinement(members, family_dims)
    if not isinstance(values, list) or len(values) != len(members):
        return members
    return values


def infer_semantic_parameters(type_id, members, family_dims):
    module = family_module(type_id)
    inference = getattr(module, "infer_semantic_parameters", None)
    if inference is None:
        return {}
    values = inference(members, family_dims)
    return values if isinstance(values, dict) else {}


def infer_member_rule(type_id, axis, span_ratio, center_ratio, name="", role=None):
    module = family_module(type_id)
    if role is not None:
        try:
            return module.infer_rule(axis, span_ratio, center_ratio, name=name, role=role)
        except TypeError:
            pass
    return module.infer_rule(axis, span_ratio, center_ratio, name=name)


def infer_member_rules(type_id, spans, centers, name="", role=None):
    rules = {}
    for axis, span_ratio, center_ratio in zip(("X", "Y", "Z"), spans, centers):
        rules[axis] = infer_member_rule(
            type_id,
            axis,
            span_ratio,
            center_ratio,
            name=name,
            role=role,
        )
    return rules
