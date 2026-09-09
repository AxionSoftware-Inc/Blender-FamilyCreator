from . import core


HELPER_TYPES = {"EMPTY", "ARMATURE"}
HELPER_FLAG = "bfc_is_helper"


def _family_source_objects(objects):
    allowed = set(core.SUPPORTED_TYPES) | HELPER_TYPES
    return [obj for obj in objects if obj is not None and obj.type in allowed]


def create_family_preserving_hierarchy(context, objects, name="Family"):
    """Create a family while retaining selected/imported Empty/Armature parents.

    Core semantic members remain geometry-only. Helpers are preserved solely as
    hierarchy/transform nodes and therefore do not enter role inference or GLB
    selection by themselves.
    """
    source_objects = _family_source_objects(objects)
    geometry = [obj for obj in source_objects if obj.type in core.SUPPORTED_TYPES]
    if not geometry:
        raise ValueError("Select at least one mesh/curve object")

    source_set = set(source_objects)
    original_parents = {obj: obj.parent for obj in source_objects}
    world_matrices = {obj: obj.matrix_world.copy() for obj in source_objects}

    root = core.create_family(context, geometry, name)

    # First place helper nodes into their original selected hierarchy (or under
    # the family root when the original parent was outside the converted asset).
    for obj in source_objects:
        if obj.type not in HELPER_TYPES:
            continue
        target_parent = original_parents[obj] if original_parents[obj] in source_set else root
        obj.parent = target_parent
        obj.matrix_world = world_matrices[obj]
        obj[HELPER_FLAG] = True
        obj[core.MEMBER_FLAG] = False
        obj["bfc_exclude_export"] = True

    # Then restore geometry parents. BASE_MATRIX is root-space world transform,
    # so reparenting with world transforms preserved does not invalidate capture.
    for obj in geometry:
        original_parent = original_parents.get(obj)
        if original_parent in source_set:
            obj.parent = original_parent
            obj.matrix_world = world_matrices[obj]

    return root
