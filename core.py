import json
import re
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

FAMILY_FLAG = "bfc_is_family"
MEMBER_FLAG = "bfc_is_member"
TEMPLATE_FLAG = "bfc_is_template"
GENERATED_FLAG = "bfc_is_generated"
GENERATOR_GROUP = "bfc_generator_group"
BASE_MATRIX = "bfc_base_matrix"
BASE_BBOX_MIN = "bfc_base_bbox_min"
BASE_BBOX_MAX = "bfc_base_bbox_max"
TYPES_JSON = "bfc_types_json"
CUSTOM_PARAMS_JSON = "bfc_custom_params_json"
SCHEMA_VERSION = 2

RULES = {"STRETCH", "MOVE", "FIXED"}
AXES = ("X", "Y", "Z")
SUPPORTED_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip()).strip("_")
    if not value:
        value = "parameter"
    if value[0].isdigit():
        value = f"p_{value}"
    return value.lower()


def matrix_to_list(matrix: Matrix):
    return [float(v) for row in matrix for v in row]


def list_to_matrix(values):
    if not values or len(values) != 16:
        return Matrix.Identity(4)
    return Matrix((values[0:4], values[4:8], values[8:12], values[12:16]))


def family_root(obj):
    current = obj
    while current:
        if bool(current.get(FAMILY_FLAG, False)):
            return current
        current = current.parent
    return None


def family_members(root, include_templates=True):
    if not root:
        return []
    members = [obj for obj in root.children_recursive if bool(obj.get(MEMBER_FLAG, False))]
    if include_templates:
        return members
    return [obj for obj in members if not bool(obj.get(TEMPLATE_FLAG, False))]


def exportable_family_members(root):
    return [
        obj
        for obj in family_members(root, include_templates=False)
        if not bool(obj.get("bfc_exclude_export", False))
    ]


def object_bbox_world(obj):
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return mins, maxs


def objects_bbox_world(objects):
    bounds = [object_bbox_world(obj) for obj in objects]
    if not bounds:
        raise ValueError("No supported geometry in selection")
    mins = Vector((min(v[0].x for v in bounds), min(v[0].y for v in bounds), min(v[0].z for v in bounds)))
    maxs = Vector((max(v[1].x for v in bounds), max(v[1].y for v in bounds), max(v[1].z for v in bounds)))
    return mins, maxs


def local_bbox(obj, root):
    root_inv = root.matrix_world.inverted_safe()
    corners = [root_inv @ (obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return mins, maxs


def infer_rule(span_ratio: float, center_ratio: float) -> str:
    if span_ratio >= 0.62:
        return "STRETCH"
    if span_ratio <= 0.38 and center_ratio >= 0.34:
        return "MOVE"
    return "FIXED"


def analyze_member(root, obj):
    family_dims = Vector((root.bfc_base_width, root.bfc_base_depth, root.bfc_base_height))
    mins, maxs = local_bbox(obj, root)
    span = maxs - mins
    center = (mins + maxs) * 0.5

    obj[BASE_MATRIX] = matrix_to_list(root.matrix_world.inverted_safe() @ obj.matrix_world)
    obj[BASE_BBOX_MIN] = [float(v) for v in mins]
    obj[BASE_BBOX_MAX] = [float(v) for v in maxs]
    obj[MEMBER_FLAG] = True

    for index, axis in enumerate(AXES):
        family_size = max(abs(family_dims[index]), 1e-9)
        span_ratio = abs(span[index]) / family_size
        half = family_size * 0.5
        center_ratio = abs(center[index]) / half if half > 1e-9 else 0.0
        setattr(obj, f"bfc_rule_{axis.lower()}", infer_rule(span_ratio, center_ratio))


def capture_family(root):
    root["bfc_applying"] = True
    try:
        for obj in family_members(root):
            analyze_member(root, obj)
    finally:
        root["bfc_applying"] = False


def create_family(context, objects, name="Family"):
    objects = [obj for obj in objects if obj.type in SUPPORTED_TYPES]
    if not objects:
        raise ValueError("Select at least one mesh/curve object")

    mins, maxs = objects_bbox_world(objects)
    center = (mins + maxs) * 0.5
    dims = maxs - mins

    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "CUBE"
    root.empty_display_size = max(max(dims), 0.25) * 0.55
    root.location = center
    context.collection.objects.link(root)

    root[FAMILY_FLAG] = True
    root[TYPES_JSON] = "{}"
    root[CUSTOM_PARAMS_JSON] = "{}"
    root.bfc_family_name = name
    root.bfc_category = "Generic Model"
    root.bfc_type_name = "Default"
    root.bfc_base_width = max(float(dims.x), 0.001)
    root.bfc_base_depth = max(float(dims.y), 0.001)
    root.bfc_base_height = max(float(dims.z), 0.001)
    root.bfc_width = root.bfc_base_width
    root.bfc_depth = root.bfc_base_depth
    root.bfc_height = root.bfc_base_height

    selected_set = set(objects)
    for obj in objects:
        obj[MEMBER_FLAG] = True

    for obj in objects:
        if obj.parent not in selected_set:
            world = obj.matrix_world.copy()
            obj.parent = root
            obj.matrix_world = world

    capture_family(root)
    save_type(root, "Default", overwrite=True)
    return root


def _axis_ratio(root, index):
    current = (root.bfc_width, root.bfc_depth, root.bfc_height)[index]
    base = (root.bfc_base_width, root.bfc_base_depth, root.bfc_base_height)[index]
    return max(float(current), 1e-6) / max(float(base), 1e-6)


def _family_axis_anchors(root):
    try:
        from .family_types import get_family_type

        spec = get_family_type(getattr(root, "bfc_family_kind", "GENERIC"))
        anchors = spec.get("axis_anchors", {})
        return [anchors.get(axis, "CENTER") for axis in AXES]
    except Exception:
        return ["CENTER", "CENTER", "CENTER"]


def _anchor_coordinate(base_size, anchor_mode):
    if anchor_mode == "MIN":
        return -float(base_size) * 0.5
    if anchor_mode == "MAX":
        return float(base_size) * 0.5
    return 0.0


def anchored_coordinate(value, base_size, ratio, anchor_mode="CENTER"):
    anchor = _anchor_coordinate(base_size, anchor_mode)
    return anchor + (float(value) - anchor) * float(ratio)


def apply_family(root):
    if not root or not bool(root.get(FAMILY_FLAG, False)):
        return

    ratios = [_axis_ratio(root, i) for i in range(3)]
    base_dims = [root.bfc_base_width, root.bfc_base_depth, root.bfc_base_height]
    anchors = _family_axis_anchors(root)

    root["bfc_applying"] = True
    try:
        for obj in family_members(root):
            base_matrix = list_to_matrix(obj.get(BASE_MATRIX))
            base_loc = base_matrix.to_translation()
            basis = base_matrix.copy()
            basis.translation = Vector((0.0, 0.0, 0.0))

            rules = [obj.bfc_rule_x, obj.bfc_rule_y, obj.bfc_rule_z]
            rules = [rule if rule in RULES else "FIXED" for rule in rules]

            new_loc = base_loc.copy()
            stretch = [1.0, 1.0, 1.0]
            for i, rule in enumerate(rules):
                if rule in {"MOVE", "STRETCH"}:
                    new_loc[i] = anchored_coordinate(
                        base_loc[i],
                        base_dims[i],
                        ratios[i],
                        anchors[i],
                    )
                if rule == "STRETCH":
                    stretch[i] = ratios[i]

            stretch_matrix = Matrix.Diagonal(Vector((stretch[0], stretch[1], stretch[2], 1.0)))
            new_matrix = stretch_matrix @ basis
            new_matrix.translation = new_loc
            obj.matrix_world = root.matrix_world @ new_matrix
    finally:
        root["bfc_applying"] = False


def read_types(root):
    try:
        data = json.loads(root.get(TYPES_JSON, "{}"))
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def write_types(root, data):
    root[TYPES_JSON] = json.dumps(data, ensure_ascii=False, sort_keys=True)


def save_type(root, name, overwrite=False):
    name = (name or "Default").strip()
    data = read_types(root)
    if name in data and not overwrite:
        raise ValueError(f"Type '{name}' already exists")
    data[name] = {
        "width": float(root.bfc_width),
        "depth": float(root.bfc_depth),
        "height": float(root.bfc_height),
    }
    write_types(root, data)
    root.bfc_type_name = name


def apply_type(root, name):
    data = read_types(root)
    if name not in data:
        raise ValueError(f"Type '{name}' not found")
    values = data[name]
    root.bfc_width = float(values["width"])
    root.bfc_depth = float(values["depth"])
    root.bfc_height = float(values["height"])
    root.bfc_type_name = name
    apply_family(root)


def delete_type(root, name):
    if name == "Default":
        raise ValueError("Default type cannot be removed")
    data = read_types(root)
    data.pop(name, None)
    write_types(root, data)
    if root.bfc_type_name == name:
        root.bfc_type_name = "Default"


def reset_family(root):
    root.bfc_width = root.bfc_base_width
    root.bfc_depth = root.bfc_base_depth
    root.bfc_height = root.bfc_base_height
    apply_family(root)


def add_custom_parameter(root, name, default_value=0.0):
    slug = slugify(name)
    prop_name = f"bfc_param_{slug}"
    root[prop_name] = float(default_value)
    root.id_properties_ui(prop_name).update(description=f"Family parameter: {name}")
    params = read_custom_parameters(root)
    params[slug] = {
        "name": name,
        "property": prop_name,
        "default": float(default_value),
        "bindings": params.get(slug, {}).get("bindings", []),
    }
    root[CUSTOM_PARAMS_JSON] = json.dumps(params, ensure_ascii=False, sort_keys=True)
    return slug, prop_name


def read_custom_parameters(root):
    try:
        data = json.loads(root.get(CUSTOM_PARAMS_JSON, "{}"))
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def bind_parameter(root, slug, target, data_path, index=-1, expression="p"):
    params = read_custom_parameters(root)
    if slug not in params:
        raise ValueError(f"Unknown parameter '{slug}'")
    prop_name = params[slug]["property"]

    fcurve = target.driver_add(data_path, index) if index >= 0 else target.driver_add(data_path)
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    driver.expression = expression or "p"
    variable = driver.variables.new()
    variable.name = "p"
    variable.type = "SINGLE_PROP"
    variable.targets[0].id = root
    variable.targets[0].data_path = f'["{prop_name}"]'

    params[slug].setdefault("bindings", []).append({
        "target": target.name,
        "dataPath": data_path,
        "index": int(index),
        "expression": expression or "p",
    })
    root[CUSTOM_PARAMS_JSON] = json.dumps(params, ensure_ascii=False, sort_keys=True)


def family_manifest(root):
    members = []
    for obj in exportable_family_members(root):
        members.append({
            "name": obj.name,
            "type": obj.type,
            "generated": bool(obj.get(GENERATED_FLAG, False)),
            "generatorGroup": obj.get(GENERATOR_GROUP, ""),
            "rules": {
                "x": obj.bfc_rule_x,
                "y": obj.bfc_rule_y,
                "z": obj.bfc_rule_z,
            },
        })
    templates = [
        {
            "name": obj.name,
            "role": getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN",
            "generatorGroup": obj.get(GENERATOR_GROUP, ""),
        }
        for obj in family_members(root)
        if bool(obj.get(TEMPLATE_FLAG, False))
    ]
    return {
        "schema": "axion.family",
        "schemaVersion": SCHEMA_VERSION,
        "name": root.bfc_family_name,
        "category": root.bfc_category,
        "activeType": root.bfc_type_name,
        "baseDimensions": {
            "width": root.bfc_base_width,
            "depth": root.bfc_base_depth,
            "height": root.bfc_base_height,
        },
        "dimensions": {
            "width": root.bfc_width,
            "depth": root.bfc_depth,
            "height": root.bfc_height,
        },
        "types": read_types(root),
        "customParameters": read_custom_parameters(root),
        "members": members,
        "templates": templates,
    }


def export_family(root, directory, export_glb=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    family_id = slugify(root.bfc_family_name)

    manifest_path = directory / f"{family_id}.family.json"
    manifest_path.write_text(
        json.dumps(family_manifest(root), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    glb_path = None
    if export_glb:
        glb_path = directory / f"{family_id}.glb"
        members = exportable_family_members(root)
        if not members:
            raise ValueError("Family has no exportable members")

        previous_selection = list(bpy.context.selected_objects)
        previous_active = bpy.context.view_layer.objects.active
        try:
            bpy.ops.object.select_all(action="DESELECT")
            for obj in members:
                obj.hide_set(False)
                obj.hide_render = False
                obj.select_set(True)
            bpy.context.view_layer.objects.active = members[0]
            bpy.ops.export_scene.gltf(
                filepath=str(glb_path),
                export_format="GLB",
                use_selection=True,
                export_apply=True,
                export_extras=True,
                export_animations=False,
                export_yup=True,
            )
        finally:
            bpy.ops.object.select_all(action="DESELECT")
            for obj in previous_selection:
                if obj and obj.name in bpy.data.objects:
                    obj.select_set(True)
            if previous_active and previous_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = previous_active

    return manifest_path, glb_path