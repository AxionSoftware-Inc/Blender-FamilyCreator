from . import core


def _float_value(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _vector_value(value, length=4):
    try:
        values = [float(component) for component in value]
    except Exception:
        values = []
    if len(values) >= length:
        return values[:length]
    return None


def _principled_node(material):
    if material is None or not getattr(material, "use_nodes", False):
        return None
    node_tree = getattr(material, "node_tree", None)
    nodes = getattr(node_tree, "nodes", None)
    if nodes is None:
        return None
    for node in nodes:
        if getattr(node, "type", "") == "BSDF_PRINCIPLED":
            return node
    return None


def _input_default(node, name):
    if node is None:
        return None
    try:
        socket = node.inputs.get(name)
    except Exception:
        socket = None
    if socket is None:
        return None
    return getattr(socket, "default_value", None)


def material_pbr_metadata(material):
    if material is None:
        return {}

    node = _principled_node(material)
    base_color = _vector_value(_input_default(node, "Base Color"), 4)
    metallic = _input_default(node, "Metallic")
    roughness = _input_default(node, "Roughness")
    alpha = _input_default(node, "Alpha")

    if base_color is None:
        base_color = _vector_value(getattr(material, "diffuse_color", None), 4)

    data = {}
    if base_color is not None:
        data["baseColorFactor"] = base_color
    if metallic is not None:
        data["metallicFactor"] = _float_value(metallic)
    if roughness is not None:
        data["roughnessFactor"] = _float_value(roughness, 0.5)
    if alpha is not None:
        data["alphaFactor"] = _float_value(alpha, 1.0)
    elif base_color is not None:
        data["alphaFactor"] = float(base_color[3])

    blend_method = getattr(material, "surface_render_method", None)
    if blend_method is None:
        blend_method = getattr(material, "blend_method", None)
    if blend_method:
        data["blendMode"] = str(blend_method)
    return data


def _assign_unique_ids(records):
    used = set()
    for record in sorted(records, key=lambda item: item["name"].lower()):
        base = core.slugify(record["name"])
        candidate = base
        index = 2
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate)
        record["id"] = candidate
    return records


def family_material_metadata(root):
    materials = {}

    for obj in core.exportable_family_members(root):
        data = getattr(obj, "data", None)
        slots = getattr(data, "materials", None)
        if slots is None:
            continue

        for slot_index, material in enumerate(slots):
            if material is None:
                continue
            key = material.name_full if hasattr(material, "name_full") else material.name
            if key not in materials:
                materials[key] = {
                    "name": str(key),
                    "pbr": material_pbr_metadata(material),
                    "usages": [],
                }
            usage = {
                "member": obj.name,
                "slot": int(slot_index),
            }
            if usage not in materials[key]["usages"]:
                materials[key]["usages"].append(usage)

    result = _assign_unique_ids(list(materials.values()))
    result.sort(key=lambda item: item["id"])
    return result
