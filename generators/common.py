import bpy
from mathutils import Matrix, Vector

from .. import core
from ..family_types.parameter_specs import property_name


TEMPLATE_ROOT_FLAG = "bfc_is_template_root"


def semantic_float(root, name, fallback=0.0):
    try:
        return float(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return float(fallback)


def semantic_int(root, name, fallback=0):
    try:
        return int(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return int(fallback)


def role_members(root, roles, include_generated=False, include_templates=True):
    roles = set(roles)
    result = []
    for obj in core.family_members(root, include_templates=include_templates):
        if getattr(obj, "bfc_member_role", "UNKNOWN") not in roles:
            continue
        if not include_generated and bool(obj.get(core.GENERATED_FLAG, False)):
            continue
        result.append(obj)
    return result


def _object_subtree(obj):
    return [obj] + list(obj.children_recursive)


def _top_level_candidates(objects):
    objects = list(dict.fromkeys(objects))
    candidate_set = set(objects)
    result = []
    for obj in objects:
        current = obj.parent
        has_candidate_parent = False
        while current is not None:
            if current in candidate_set:
                has_candidate_parent = True
                break
            current = current.parent
        if not has_candidate_parent:
            result.append(obj)
    return result


def clear_generated(root, group=None):
    generated = []
    for obj in list(root.children_recursive):
        if not bool(obj.get(core.GENERATED_FLAG, False)):
            continue
        if group is not None and obj.get(core.GENERATOR_GROUP, "") != group:
            continue
        generated.append(obj)

    generated.sort(key=lambda obj: len(obj.children_recursive))
    removed = 0
    for obj in generated:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def mark_templates(objects, group):
    roots = _top_level_candidates(objects)
    for template_root in roots:
        for obj in _object_subtree(template_root):
            obj[core.TEMPLATE_FLAG] = True
            obj[core.GENERATOR_GROUP] = group
            obj["bfc_exclude_export"] = True
            obj[TEMPLATE_ROOT_FLAG] = obj == template_root
            obj.hide_render = True
            try:
                obj.hide_set(True)
            except Exception:
                pass
    return roots


def unmark_templates(objects):
    roots = _top_level_candidates(objects)
    for template_root in roots:
        for obj in _object_subtree(template_root):
            if not bool(obj.get(core.TEMPLATE_FLAG, False)):
                continue
            obj[core.TEMPLATE_FLAG] = False
            obj["bfc_exclude_export"] = False
            obj[TEMPLATE_ROOT_FLAG] = False
            obj.hide_render = False
            try:
                obj.hide_set(False)
            except Exception:
                pass


def current_templates(root, group):
    return [
        obj
        for obj in root.children_recursive
        if bool(obj.get(core.TEMPLATE_FLAG, False))
        and bool(obj.get(TEMPLATE_ROOT_FLAG, False))
        and obj.get(core.GENERATOR_GROUP, "") == group
    ]


def prepare_template_group(root, roles, group):
    templates = current_templates(root, group)
    if templates:
        return templates

    sources = role_members(root, roles, include_generated=False, include_templates=True)
    sources = [obj for obj in sources if not bool(obj.get(core.TEMPLATE_FLAG, False))]
    if not sources:
        return []

    return mark_templates(sources, group)


def local_center(obj, root):
    mins, maxs = core.local_bbox(obj, root)
    return (mins + maxs) * 0.5


def local_span(obj, root):
    mins, maxs = core.local_bbox(obj, root)
    return maxs - mins


def choose_center_prototype(objects, root, axis=0):
    if not objects:
        return None
    return min(objects, key=lambda obj: abs(local_center(obj, root)[axis]))


def _link_clone(root, original, clone):
    collections = list(original.users_collection)
    if collections:
        for collection in collections:
            collection.objects.link(clone)
    else:
        collection = root.users_collection[0] if root.users_collection else bpy.context.collection
        collection.objects.link(clone)


def duplicate_template(root, source, group, name, role=None):
    """Clone a template root and its complete child subtree.

    Object data is linked, not deep-copied, so repeated cushions/shelves/treads
    stay memory-efficient while preserving child details and material slots.
    """
    originals = _object_subtree(source)
    clone_map = {}
    world_matrices = {obj: obj.matrix_world.copy() for obj in originals}

    for original in originals:
        clone = original.copy()
        clone_map[original] = clone
        _link_clone(root, original, clone)

        clone[core.TEMPLATE_FLAG] = False
        clone[TEMPLATE_ROOT_FLAG] = False
        clone[core.GENERATED_FLAG] = True
        clone[core.GENERATOR_GROUP] = group
        clone["bfc_exclude_export"] = False
        clone.hide_render = False
        try:
            clone.hide_set(False)
        except Exception:
            pass

    for original, clone in clone_map.items():
        if original == source:
            clone.parent = root
        elif original.parent in clone_map:
            clone.parent = clone_map[original.parent]
        else:
            clone.parent = clone_map[source]
        clone.matrix_world = world_matrices[original]

    root_clone = clone_map[source]
    root_clone.name = name
    for original, clone in clone_map.items():
        if original == source:
            continue
        clone.name = f"{name}_{original.name}"

    if role is not None:
        root_clone.bfc_member_role = role

    for original, clone in clone_map.items():
        if not bool(original.get(core.MEMBER_FLAG, False)):
            continue
        clone[core.MEMBER_FLAG] = True
        original_rules = (
            original.bfc_rule_x,
            original.bfc_rule_y,
            original.bfc_rule_z,
        )
        original_role = getattr(original, "bfc_member_role", "UNKNOWN") or "UNKNOWN"
        core.analyze_member(root, clone)
        clone.bfc_rule_x, clone.bfc_rule_y, clone.bfc_rule_z = original_rules
        clone.bfc_member_role = role if original == source and role is not None else original_role

    return root_clone


def set_family_local_location(root, obj, axis, value):
    index = {"X": 0, "Y": 1, "Z": 2}[axis]
    local = root.matrix_world.inverted_safe() @ obj.matrix_world
    translation = local.to_translation()
    translation[index] = float(value)
    local.translation = translation
    obj.matrix_world = root.matrix_world @ local
    if bool(obj.get(core.MEMBER_FLAG, False)):
        core.analyze_member(root, obj)


def resize_family_axis(root, obj, axis, target_span):
    index = {"X": 0, "Y": 1, "Z": 2}[axis]
    current = local_span(obj, root)[index]
    if abs(current) <= 1e-9:
        return
    ratio = float(target_span) / float(current)
    local = root.matrix_world.inverted_safe() @ obj.matrix_world
    loc = local.to_translation()
    basis = local.copy()
    basis.translation = Vector((0.0, 0.0, 0.0))
    stretch = [1.0, 1.0, 1.0]
    stretch[index] = ratio
    stretch_matrix = Matrix.Diagonal(Vector((stretch[0], stretch[1], stretch[2], 1.0)))
    result = stretch_matrix @ basis
    result.translation = loc
    obj.matrix_world = root.matrix_world @ result
    if bool(obj.get(core.MEMBER_FLAG, False)):
        core.analyze_member(root, obj)


def resize_family_axis_anchored(root, obj, axis, target_span, anchor="CENTER"):
    index = {"X": 0, "Y": 1, "Z": 2}[axis]
    mins_before, maxs_before = core.local_bbox(obj, root)
    if anchor == "MIN":
        anchor_before = float(mins_before[index])
    elif anchor == "MAX":
        anchor_before = float(maxs_before[index])
    else:
        anchor_before = float((mins_before[index] + maxs_before[index]) * 0.5)

    resize_family_axis(root, obj, axis, target_span)

    mins_after, maxs_after = core.local_bbox(obj, root)
    if anchor == "MIN":
        anchor_after = float(mins_after[index])
    elif anchor == "MAX":
        anchor_after = float(maxs_after[index])
    else:
        anchor_after = float((mins_after[index] + maxs_after[index]) * 0.5)

    center = local_center(obj, root)
    set_family_local_location(root, obj, axis, float(center[index]) + anchor_before - anchor_after)


def move_surface_to(root, obj, axis, surface, target):
    index = {"X": 0, "Y": 1, "Z": 2}[axis]
    mins, maxs = core.local_bbox(obj, root)
    current = float(mins[index]) if surface == "MIN" else float(maxs[index])
    center = local_center(obj, root)
    set_family_local_location(root, obj, axis, float(center[index]) + float(target) - current)


def evenly_spaced_centers(count, minimum, maximum):
    count = int(count)
    if count <= 0:
        return []
    if count == 1:
        return [(float(minimum) + float(maximum)) * 0.5]
    step = (float(maximum) - float(minimum)) / float(count - 1)
    return [float(minimum) + step * i for i in range(count)]
