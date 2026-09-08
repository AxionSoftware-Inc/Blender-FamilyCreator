import bpy
from mathutils import Matrix, Vector

from .. import core


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


def clear_generated(root, group=None):
    removed = 0
    for obj in list(core.family_members(root)):
        if not bool(obj.get(core.GENERATED_FLAG, False)):
            continue
        if group is not None and obj.get(core.GENERATOR_GROUP, "") != group:
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
        removed += 1
    return removed


def mark_templates(objects, group):
    for obj in objects:
        obj[core.TEMPLATE_FLAG] = True
        obj[core.GENERATOR_GROUP] = group
        obj["bfc_exclude_export"] = True
        obj.hide_render = True
        try:
            obj.hide_set(True)
        except Exception:
            pass


def unmark_templates(objects):
    for obj in objects:
        obj[core.TEMPLATE_FLAG] = False
        obj["bfc_exclude_export"] = False
        obj.hide_render = False
        try:
            obj.hide_set(False)
        except Exception:
            pass


def current_templates(root, group):
    return [
        obj
        for obj in core.family_members(root)
        if bool(obj.get(core.TEMPLATE_FLAG, False))
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

    mark_templates(sources, group)
    return sources


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


def duplicate_template(root, source, group, name, role=None):
    clone = source.copy()
    clone.data = source.data
    clone.name = name

    collection = root.users_collection[0] if root.users_collection else bpy.context.collection
    collection.objects.link(clone)

    clone.parent = root
    clone.matrix_world = source.matrix_world.copy()
    clone[core.MEMBER_FLAG] = True
    clone[core.TEMPLATE_FLAG] = False
    clone[core.GENERATED_FLAG] = True
    clone[core.GENERATOR_GROUP] = group
    clone["bfc_exclude_export"] = False
    clone.hide_render = False
    try:
        clone.hide_set(False)
    except Exception:
        pass

    if role is not None:
        clone.bfc_member_role = role

    rules = (source.bfc_rule_x, source.bfc_rule_y, source.bfc_rule_z)
    core.analyze_member(root, clone)
    clone.bfc_rule_x, clone.bfc_rule_y, clone.bfc_rule_z = rules
    if role is not None:
        clone.bfc_member_role = role
    return clone


def set_family_local_location(root, obj, axis, value):
    index = {"X": 0, "Y": 1, "Z": 2}[axis]
    local = root.matrix_world.inverted_safe() @ obj.matrix_world
    translation = local.to_translation()
    translation[index] = float(value)
    local.translation = translation
    obj.matrix_world = root.matrix_world @ local
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
    core.analyze_member(root, obj)


def evenly_spaced_centers(count, minimum, maximum):
    count = int(count)
    if count <= 0:
        return []
    if count == 1:
        return [(float(minimum) + float(maximum)) * 0.5]
    step = (float(maximum) - float(minimum)) / float(count - 1)
    return [float(minimum) + step * i for i in range(count)]
