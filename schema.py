SCHEMA_NAME = "axion.family"
SCHEMA_VERSION = 2


def _positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) > 0.0


def _validate_dimensions(data, path, errors):
    if not isinstance(data, dict):
        errors.append(f"{path} must be an object")
        return
    for key in ("width", "depth", "height"):
        if not _positive_number(data.get(key)):
            errors.append(f"{path}.{key} must be a positive number")


def _validate_types(types, errors):
    if not isinstance(types, dict):
        errors.append("types must be an object")
        return
    for name, values in types.items():
        if not isinstance(name, str) or not name.strip():
            errors.append("types contains an empty/non-string type name")
            continue
        _validate_dimensions(values, f"types.{name}", errors)
        semantic = values.get("semanticParameters", {}) if isinstance(values, dict) else {}
        if not isinstance(semantic, dict):
            errors.append(f"types.{name}.semanticParameters must be an object")


def _validate_members(members, errors):
    if not isinstance(members, list):
        errors.append("members must be an array")
        return
    names = set()
    for index, member in enumerate(members):
        path = f"members[{index}]"
        if not isinstance(member, dict):
            errors.append(f"{path} must be an object")
            continue
        name = member.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{path}.name is required")
        elif name in names:
            errors.append(f"duplicate member name: {name}")
        else:
            names.add(name)
        role = member.get("role")
        if not isinstance(role, str) or not role:
            errors.append(f"{path}.role is required")
        rules = member.get("rules")
        if not isinstance(rules, dict):
            errors.append(f"{path}.rules must be an object")
            continue
        for axis in ("x", "y", "z"):
            if rules.get(axis) not in {"STRETCH", "MOVE", "FIXED"}:
                errors.append(f"{path}.rules.{axis} is invalid")


def _validate_materials(materials, errors):
    if not isinstance(materials, list):
        errors.append("materials must be an array")
        return
    ids = set()
    for index, material in enumerate(materials):
        path = f"materials[{index}]"
        if not isinstance(material, dict):
            errors.append(f"{path} must be an object")
            continue
        material_id = material.get("id")
        if not isinstance(material_id, str) or not material_id:
            errors.append(f"{path}.id is required")
        elif material_id in ids:
            errors.append(f"duplicate material id: {material_id}")
        else:
            ids.add(material_id)
        if not isinstance(material.get("name"), str):
            errors.append(f"{path}.name is required")
        if not isinstance(material.get("usages", []), list):
            errors.append(f"{path}.usages must be an array")


def _validate_hosting(hosting, errors):
    if hosting is None:
        return
    if not isinstance(hosting, dict):
        errors.append("hosting must be an object")
        return
    if hosting.get("hostType") != "WALL":
        errors.append("hosting.hostType must currently be WALL")
    opening = hosting.get("opening")
    if not isinstance(opening, dict):
        errors.append("hosting.opening must be an object")
        return
    if opening.get("shape") != "RECTANGLE":
        errors.append("hosting.opening.shape must currently be RECTANGLE")
    for key in ("width", "height", "depth"):
        if not _positive_number(opening.get(key)):
            errors.append(f"hosting.opening.{key} must be positive")


def validate_manifest(data):
    errors = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    if data.get("schema") != SCHEMA_NAME:
        errors.append(f"schema must be {SCHEMA_NAME}")
    if data.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")

    family_id = data.get("familyId")
    if not isinstance(family_id, str) or not family_id.strip():
        errors.append("familyId is required")
    if not isinstance(data.get("familyKind"), str) or not data.get("familyKind"):
        errors.append("familyKind is required")
    if not isinstance(data.get("name"), str) or not data.get("name"):
        errors.append("name is required")

    units = data.get("units")
    if not isinstance(units, dict) or units.get("length") != "meter":
        errors.append("units.length must be meter")

    coordinates = data.get("coordinateSystems")
    if not isinstance(coordinates, dict):
        errors.append("coordinateSystems is required")
    else:
        if coordinates.get("family") != "RIGHT_HANDED_Z_UP":
            errors.append("coordinateSystems.family is invalid")
        if coordinates.get("geometry") != "GLTF_RIGHT_HANDED_Y_UP":
            errors.append("coordinateSystems.geometry is invalid")

    _validate_dimensions(data.get("baseDimensions"), "baseDimensions", errors)
    _validate_dimensions(data.get("dimensions"), "dimensions", errors)
    _validate_types(data.get("types"), errors)
    _validate_members(data.get("members"), errors)
    _validate_materials(data.get("materials", []), errors)
    _validate_hosting(data.get("hosting"), errors)

    if not isinstance(data.get("semanticParameters", {}), dict):
        errors.append("semanticParameters must be an object")
    if not isinstance(data.get("quality"), dict):
        errors.append("quality must be an object")
    if not isinstance(data.get("generator"), dict):
        errors.append("generator must be an object")

    return errors


def assert_valid_manifest(data):
    errors = validate_manifest(data)
    if errors:
        preview = "; ".join(errors[:8])
        if len(errors) > 8:
            preview += f"; +{len(errors) - 8} more"
        raise ValueError(f"Invalid Axion family schema v2: {preview}")
    return data
