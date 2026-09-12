SCHEMA_NAME = "axion.family"
SCHEMA_VERSION = 2


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _positive_number(value):
    return _number(value) and float(value) > 0.0


def _nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _nonnegative_number(value):
    return _number(value) and float(value) >= 0.0


def _numeric_vector(value, length):
    return (
        isinstance(value, list)
        and len(value) == length
        and all(_number(component) for component in value)
    )


def _relative_uri(value):
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    if normalized.startswith("/"):
        return False
    first = normalized.split("/", 1)[0]
    if ":" in first:
        return False
    parts = [part for part in normalized.split("/") if part]
    return bool(parts) and all(part not in {".", ".."} for part in parts)


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


def _validate_geometry_variants(data, errors):
    variants = data.get("geometryVariants")
    strategy = data.get("geometryStrategy")
    if variants is None and strategy is None:
        return
    if not isinstance(variants, dict) or not variants:
        errors.append("geometryVariants must be a non-empty object")
        return

    primary_names = []
    for type_name, variant in variants.items():
        path = f"geometryVariants.{type_name}"
        if not isinstance(type_name, str) or not type_name.strip():
            errors.append("geometryVariants contains an invalid type name")
            continue
        if not isinstance(variant, dict):
            errors.append(f"{path} must be an object")
            continue
        if not _relative_uri(variant.get("uri")):
            errors.append(f"{path}.uri must be a safe relative non-empty path")
        if variant.get("baked") is not True:
            errors.append(f"{path}.baked must be true")
        if bool(variant.get("primary")):
            primary_names.append(type_name)

    if len(primary_names) != 1:
        errors.append("geometryVariants must contain exactly one primary variant")
    else:
        active_type = data.get("activeType")
        if primary_names[0] != active_type:
            errors.append("primary geometry variant must match activeType")

    if not isinstance(strategy, dict):
        errors.append("geometryStrategy must be an object when geometryVariants are present")
        return
    if strategy.get("mode") not in {"BAKED_ACTIVE_TYPE", "BAKED_TYPE_VARIANTS"}:
        errors.append("geometryStrategy.mode is invalid")
    if strategy.get("activeType") != data.get("activeType"):
        errors.append("geometryStrategy.activeType must match activeType")
    if strategy.get("variantCount") != len(variants):
        errors.append("geometryStrategy.variantCount must match geometryVariants")


def _validate_thumbnail(thumbnail, errors):
    if thumbnail is None:
        return
    if not isinstance(thumbnail, dict):
        errors.append("thumbnail must be an object")
        return
    if not _relative_uri(thumbnail.get("uri")):
        errors.append("thumbnail.uri must be a safe relative non-empty path")
    if not isinstance(thumbnail.get("width"), int) or thumbnail.get("width", 0) <= 0:
        errors.append("thumbnail.width must be a positive integer")
    if not isinstance(thumbnail.get("height"), int) or thumbnail.get("height", 0) <= 0:
        errors.append("thumbnail.height must be a positive integer")
    if thumbnail.get("format") not in {"PNG", "JPEG", "WEBP"}:
        errors.append("thumbnail.format is invalid")


def _validate_runtime_cost(cost, errors):
    if cost is None:
        return
    if not isinstance(cost, dict):
        errors.append("runtimeCost must be an object")
        return

    measurement = cost.get("measurement")
    if measurement is not None and measurement != "EVALUATED_TRIANGULATED_GEOMETRY":
        errors.append("runtimeCost.measurement is invalid")
    texture_estimate = cost.get("textureMemoryEstimate")
    if texture_estimate is not None and texture_estimate != "UNCOMPRESSED_RGBA8":
        errors.append("runtimeCost.textureMemoryEstimate is invalid")

    for field in (
        "memberCount",
        "meshObjects",
        "nonMeshObjects",
        "vertices",
        "triangles",
        "materialSlots",
        "drawCallEstimate",
        "uniqueMaterials",
        "textureCount",
        "texturePixels",
        "maxTextureDimension",
        "estimatedTextureBytesRGBA",
    ):
        if field in cost and not _nonnegative_int(cost.get(field)):
            errors.append(f"runtimeCost.{field} must be a non-negative integer")

    if "estimatedTextureMemoryMiB" in cost and not _nonnegative_number(cost.get("estimatedTextureMemoryMiB")):
        errors.append("runtimeCost.estimatedTextureMemoryMiB must be a non-negative number")

    textures = cost.get("textures")
    if textures is not None:
        if not isinstance(textures, list):
            errors.append("runtimeCost.textures must be an array")
        else:
            for index, texture in enumerate(textures):
                path = f"runtimeCost.textures[{index}]"
                if not isinstance(texture, dict):
                    errors.append(f"{path} must be an object")
                    continue
                if not isinstance(texture.get("name"), str):
                    errors.append(f"{path}.name must be a string")
                for field in ("width", "height", "pixels", "estimatedBytesRGBA"):
                    if not _nonnegative_int(texture.get(field)):
                        errors.append(f"{path}.{field} must be a non-negative integer")

    members = cost.get("members")
    if members is not None:
        if not isinstance(members, list):
            errors.append("runtimeCost.members must be an array")
        else:
            for index, member in enumerate(members):
                path = f"runtimeCost.members[{index}]"
                if not isinstance(member, dict):
                    errors.append(f"{path} must be an object")
                    continue
                if not isinstance(member.get("name"), str):
                    errors.append(f"{path}.name must be a string")
                if not isinstance(member.get("role"), str):
                    errors.append(f"{path}.role must be a string")
                for field in ("vertices", "triangles", "materialSlots", "drawCallEstimate"):
                    if not _nonnegative_int(member.get(field)):
                        errors.append(f"{path}.{field} must be a non-negative integer")


def _validate_mobile_budget(mobile, errors):
    if mobile is None:
        return
    if not isinstance(mobile, dict):
        errors.append("mobileBudget must be an object")
        return
    if mobile.get("status") not in {"WITHIN_TARGET", "OVER_TARGET", "OVER_HARD_LIMIT"}:
        errors.append("mobileBudget.status is invalid")
    if "policyVersion" in mobile and not _nonnegative_int(mobile.get("policyVersion")):
        errors.append("mobileBudget.policyVersion must be a non-negative integer")

    for field in (
        "sourceTriangles",
        "sourceMaterialSlots",
        "sourceDrawCallEstimate",
        "sourceMaxTextureDimension",
    ):
        if field in mobile and not _nonnegative_int(mobile.get(field)):
            errors.append(f"mobileBudget.{field} must be a non-negative integer")
    if "sourceTextureMemoryMiB" in mobile and not _nonnegative_number(mobile.get("sourceTextureMemoryMiB")):
        errors.append("mobileBudget.sourceTextureMemoryMiB must be a non-negative number")

    for field in ("suggestedLod1Ratio", "suggestedLod2Ratio"):
        ratio = mobile.get(field)
        if ratio is not None and (not _number(ratio) or float(ratio) <= 0.0 or float(ratio) > 1.0):
            errors.append(f"mobileBudget.{field} must be in (0, 1]")

    budget = mobile.get("budget")
    if budget is not None:
        if not isinstance(budget, dict):
            errors.append("mobileBudget.budget must be an object")
        else:
            for field in (
                "lod0TargetTriangles",
                "lod0HardTriangles",
                "lod1TargetTriangles",
                "lod2TargetTriangles",
                "targetMaterialSlots",
                "targetDrawCalls",
                "targetTextureDimension",
                "hardTextureDimension",
                "targetTextureMemoryMiB",
            ):
                if not isinstance(budget.get(field), int) or budget.get(field, 0) <= 0:
                    errors.append(f"mobileBudget.budget.{field} must be a positive integer")
            target_dimension = budget.get("targetTextureDimension")
            hard_dimension = budget.get("hardTextureDimension")
            if (
                isinstance(target_dimension, int)
                and isinstance(hard_dimension, int)
                and hard_dimension < target_dimension
            ):
                errors.append("mobileBudget.budget.hardTextureDimension must be >= targetTextureDimension")

    warnings = mobile.get("warnings")
    if warnings is not None and (
        not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings)
    ):
        errors.append("mobileBudget.warnings must be an array of strings")


def _validate_geometry_lods(data, errors):
    lods = data.get("geometryLods")
    strategy = data.get("lodStrategy")
    if lods is None and strategy is None:
        return
    if not isinstance(lods, dict) or not lods:
        errors.append("geometryLods must be a non-empty object")
        return
    if "LOD0" not in lods:
        errors.append("geometryLods must contain LOD0")

    lod0_uri = None
    for level, record in lods.items():
        path = f"geometryLods.{level}"
        if level not in {"LOD0", "LOD1", "LOD2"}:
            errors.append(f"{path} is not a supported LOD level")
        if not isinstance(record, dict):
            errors.append(f"{path} must be an object")
            continue
        uri = record.get("uri")
        if not _relative_uri(uri):
            errors.append(f"{path}.uri must be a safe relative non-empty path")
        if level == "LOD0":
            lod0_uri = uri
            if record.get("generated") is not False:
                errors.append("geometryLods.LOD0.generated must be false")
        elif not isinstance(record.get("generated"), bool):
            errors.append(f"{path}.generated must be boolean")
        if not _nonnegative_int(record.get("triangles")):
            errors.append(f"{path}.triangles must be a non-negative integer")
        if "targetTriangles" in record and not _nonnegative_int(record.get("targetTriangles")):
            errors.append(f"{path}.targetTriangles must be a non-negative integer")
        if "meetsTarget" in record and not isinstance(record.get("meetsTarget"), bool):
            errors.append(f"{path}.meetsTarget must be boolean")

        alias = record.get("aliasOf")
        if alias is not None:
            if alias != "LOD0":
                errors.append(f"{path}.aliasOf must currently be LOD0")
            if record.get("generated") is not False:
                errors.append(f"{path} alias cannot be generated")
            if lod0_uri is not None and uri != lod0_uri:
                errors.append(f"{path} alias URI must match LOD0")

        skipped = record.get("protectedOrSkippedMembers")
        if skipped is not None and not isinstance(skipped, list):
            errors.append(f"{path}.protectedOrSkippedMembers must be an array")

    if not isinstance(strategy, dict):
        errors.append("lodStrategy must be an object when geometryLods are present")
        return
    if strategy.get("mode") != "NON_DESTRUCTIVE_DECIMATE":
        errors.append("lodStrategy.mode is invalid")
    if strategy.get("source") != "LOD0":
        errors.append("lodStrategy.source must be LOD0")
    if strategy.get("levelCount") != len(lods):
        errors.append("lodStrategy.levelCount must match geometryLods")
    protected = strategy.get("protectedRoles", [])
    if not isinstance(protected, list) or any(not isinstance(item, str) for item in protected):
        errors.append("lodStrategy.protectedRoles must be an array of strings")


def _validate_aabb(record, path, errors, require_minmax=True):
    if not isinstance(record, dict):
        errors.append(f"{path} must be an object")
        return
    if record.get("shape") != "AABB":
        errors.append(f"{path}.shape must be AABB")
    if require_minmax:
        if not _numeric_vector(record.get("min"), 3):
            errors.append(f"{path}.min must be a 3-number vector")
        if not _numeric_vector(record.get("max"), 3):
            errors.append(f"{path}.max must be a 3-number vector")
    if not _numeric_vector(record.get("center"), 3):
        errors.append(f"{path}.center must be a 3-number vector")
    size = record.get("size")
    if not _numeric_vector(size, 3) or any(float(value) <= 0.0 for value in (size or [])):
        errors.append(f"{path}.size must be a positive 3-number vector")


def _validate_runtime_proxy(proxy, types, errors):
    if not isinstance(proxy, dict):
        errors.append("runtimeProxy must be an object")
        return
    if proxy.get("coordinateSystem") != "RIGHT_HANDED_Z_UP":
        errors.append("runtimeProxy.coordinateSystem is invalid")

    _validate_aabb(proxy.get("selection"), "runtimeProxy.selection", errors)
    _validate_aabb(proxy.get("collision"), "runtimeProxy.collision", errors, require_minmax=False)

    footprint = proxy.get("planFootprint")
    if not isinstance(footprint, dict):
        errors.append("runtimeProxy.planFootprint must be an object")
    else:
        if footprint.get("shape") != "RECTANGLE":
            errors.append("runtimeProxy.planFootprint.shape must be RECTANGLE")
        if not _numeric_vector(footprint.get("min"), 2):
            errors.append("runtimeProxy.planFootprint.min must be a 2-number vector")
        if not _numeric_vector(footprint.get("max"), 2):
            errors.append("runtimeProxy.planFootprint.max must be a 2-number vector")
        if not _number(footprint.get("baseZ")):
            errors.append("runtimeProxy.planFootprint.baseZ must be numeric")

    type_bounds = proxy.get("typeBounds")
    if not isinstance(type_bounds, dict):
        errors.append("runtimeProxy.typeBounds must be an object")
        return
    for type_name, bounds in type_bounds.items():
        path = f"runtimeProxy.typeBounds.{type_name}"
        if isinstance(types, dict) and type_name not in types:
            errors.append(f"{path} does not match a saved Family Type")
        if not isinstance(bounds, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in ("min", "max", "center", "size"):
            if not _numeric_vector(bounds.get(field), 3):
                errors.append(f"{path}.{field} must be a 3-number vector")
        size = bounds.get("size")
        if _numeric_vector(size, 3) and any(float(value) <= 0.0 for value in size):
            errors.append(f"{path}.size must be positive")


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

    active_type = data.get("activeType")
    if not isinstance(active_type, str) or not active_type.strip():
        errors.append("activeType is required")

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
    types = data.get("types")
    _validate_types(types, errors)
    if isinstance(types, dict) and active_type not in types:
        errors.append("activeType must exist in types")
    _validate_members(data.get("members"), errors)
    _validate_materials(data.get("materials", []), errors)
    _validate_hosting(data.get("hosting"), errors)
    _validate_geometry_variants(data, errors)
    _validate_thumbnail(data.get("thumbnail"), errors)
    _validate_runtime_proxy(data.get("runtimeProxy"), types, errors)
    _validate_runtime_cost(data.get("runtimeCost"), errors)
    _validate_mobile_budget(data.get("mobileBudget"), errors)
    _validate_geometry_lods(data, errors)

    if not isinstance(data.get("semanticParameters", {}), dict):
        errors.append("semanticParameters must be an object")
    if not isinstance(data.get("quality"), dict):
        errors.append("quality must be an object")
    if not isinstance(data.get("generator"), dict):
        errors.append("generator must be an object")
    warnings = data.get("exportWarnings", [])
    if warnings is not None and (
        not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings)
    ):
        errors.append("exportWarnings must be an array of strings")

    return errors


def assert_valid_manifest(data):
    errors = validate_manifest(data)
    if errors:
        preview = "; ".join(errors[:8])
        if len(errors) > 8:
            preview += f"; +{len(errors) - 8} more"
        raise ValueError(f"Invalid Axion family schema v2: {preview}")
    return data
