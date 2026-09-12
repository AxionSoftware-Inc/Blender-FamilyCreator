import re

from . import core


POLYGON_REVIEW_THRESHOLD = 500_000
POLYGON_HEAVY_THRESHOLD = 1_500_000
SCALE_EPSILON = 1e-4
SHEAR_EPSILON = 1e-4


TYPICAL_MAX_DIMENSION = {
    "SOFA": 8.0,
    "TABLE": 12.0,
    "CHAIR": 4.0,
    "BED": 6.0,
    "CABINET": 8.0,
    "WARDROBE": 8.0,
    "SHELF": 10.0,
    "KITCHEN_BASE": 5.0,
    "KITCHEN_WALL": 5.0,
    "DOOR": 6.0,
    "WINDOW": 12.0,
    "STAIR": 50.0,
    "TOILET": 4.0,
    "SINK": 5.0,
    "BATHTUB": 6.0,
}


TYPICAL_MIN_DIMENSION = {
    "SOFA": 0.20,
    "TABLE": 0.10,
    "CHAIR": 0.10,
    "BED": 0.20,
    "CABINET": 0.10,
    "WARDROBE": 0.10,
    "SHELF": 0.10,
    "KITCHEN_BASE": 0.10,
    "KITCHEN_WALL": 0.10,
    "DOOR": 0.10,
    "WINDOW": 0.10,
    "STAIR": 0.10,
    "TOILET": 0.05,
    "SINK": 0.05,
    "BATHTUB": 0.10,
}


_GENERIC_OBJECT_NAME = re.compile(r"^(?:cube|object|mesh|plane|cylinder|sphere|cone|curve)(?:[._ -]?\d+)?$", re.IGNORECASE)


def _source_members(root):
    return [
        obj
        for obj in core.family_members(root)
        if not bool(obj.get(core.GENERATED_FLAG, False))
    ]


def _mesh_polygon_count(obj):
    data = getattr(obj, "data", None)
    polygons = getattr(data, "polygons", None)
    return len(polygons) if polygons is not None else 0


def _canonical_matrix(obj):
    values = obj.get(core.BASE_MATRIX)
    if values is not None:
        try:
            return core.list_to_matrix(list(values))
        except Exception:
            pass
    return obj.matrix_world.copy()


def _scale_flags(matrix):
    try:
        scale = tuple(abs(float(value)) for value in matrix.to_scale())
    except Exception:
        return False, False
    non_unit = any(abs(value - 1.0) > SCALE_EPSILON for value in scale)
    non_uniform = (max(scale) - min(scale)) > SCALE_EPSILON if scale else False
    return non_unit, non_uniform


def _shear_measure(matrix):
    """Return max normalized dot product between basis columns.

    Pure rotation + arbitrary local scale keeps the basis columns orthogonal.
    A non-zero normalized dot therefore signals canonical transform shear,
    independently of unapplied/non-uniform scale magnitude.
    """
    try:
        matrix3 = matrix.to_3x3()
        columns = []
        for index in range(3):
            column = (
                float(matrix3[0][index]),
                float(matrix3[1][index]),
                float(matrix3[2][index]),
            )
            length_sq = sum(value * value for value in column)
            if length_sq <= 1e-18:
                return 0.0
            inv_length = length_sq ** -0.5
            columns.append(tuple(value * inv_length for value in column))

        return max(
            abs(sum(columns[left][i] * columns[right][i] for i in range(3)))
            for left, right in ((0, 1), (0, 2), (1, 2))
        )
    except Exception:
        return 0.0


def _source_text(root):
    values = [
        str(getattr(root, "bfc_family_name", "") or ""),
        str(root.get("bfc_source_asset", "") or ""),
        str(root.get("bfc_source_key", "") or ""),
    ]
    return " ".join(values).lower().replace("_", "-")


def _mixed_scene_name_hint(root, family_kind):
    text = _source_text(root)
    if family_kind == "TABLE":
        return "table" in text and any(token in text for token in ("chair", "stool", "bench", "seating"))
    if family_kind == "BED":
        return "bed" in text and any(token in text for token in ("nightstand", "bedside-table", "bedside cabinet"))
    return False


def inspect_family(root):
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    members = _source_members(root)

    warnings = []
    severe = []
    stats = {
        "sourceMembers": len(members),
        "meshPolygons": 0,
        "nonUnitScaleMembers": 0,
        "nonUniformScaleMembers": 0,
        "shearedTransformMembers": 0,
        "maxShearDot": 0.0,
        "negativeDeterminantMembers": 0,
        "shapeKeyMembers": 0,
        "armatureMembers": 0,
        "genericNamedMembers": 0,
        "genericNameShare": 0.0,
        "mixedSceneNameHint": False,
    }

    for obj in members:
        stats["meshPolygons"] += _mesh_polygon_count(obj)
        if _GENERIC_OBJECT_NAME.match(str(getattr(obj, "name", "") or "").strip()):
            stats["genericNamedMembers"] += 1

        matrix = _canonical_matrix(obj)
        non_unit, non_uniform = _scale_flags(matrix)
        if non_unit:
            stats["nonUnitScaleMembers"] += 1
        if non_uniform:
            stats["nonUniformScaleMembers"] += 1

        shear = _shear_measure(matrix)
        stats["maxShearDot"] = max(float(stats["maxShearDot"]), float(shear))
        if shear > SHEAR_EPSILON:
            stats["shearedTransformMembers"] += 1

        try:
            if float(matrix.to_3x3().determinant()) < 0.0:
                stats["negativeDeterminantMembers"] += 1
        except Exception:
            pass

        data = getattr(obj, "data", None)
        if data is not None and getattr(data, "shape_keys", None) is not None:
            stats["shapeKeyMembers"] += 1
        if any(modifier.type == "ARMATURE" for modifier in getattr(obj, "modifiers", ())):
            stats["armatureMembers"] += 1

    if members:
        stats["genericNameShare"] = float(stats["genericNamedMembers"]) / float(len(members))

    if stats["meshPolygons"] > POLYGON_HEAVY_THRESHOLD:
        severe.append(f"Very heavy source geometry: {stats['meshPolygons']:,} polygons")
    elif stats["meshPolygons"] > POLYGON_REVIEW_THRESHOLD:
        warnings.append(f"Heavy source geometry: {stats['meshPolygons']:,} polygons")

    if stats["nonUniformScaleMembers"]:
        severe.append(f"{stats['nonUniformScaleMembers']} source member(s) have non-uniform scale")
    elif stats["nonUnitScaleMembers"]:
        warnings.append(f"{stats['nonUnitScaleMembers']} source member(s) have unapplied scale")

    if stats["shearedTransformMembers"]:
        severe.append(
            f"{stats['shearedTransformMembers']} source member(s) contain canonical transform shear"
        )
    if stats["negativeDeterminantMembers"]:
        severe.append(f"{stats['negativeDeterminantMembers']} source member(s) have mirrored/negative transforms")
    if stats["shapeKeyMembers"]:
        warnings.append(f"{stats['shapeKeyMembers']} source member(s) contain shape keys")
    if stats["armatureMembers"]:
        warnings.append(f"{stats['armatureMembers']} source member(s) use armature modifiers")

    stats["mixedSceneNameHint"] = _mixed_scene_name_hint(root, family_kind)
    if stats["mixedSceneNameHint"]:
        warnings.append(
            "Source name suggests a mixed/multi-item set; review family isolation before automatic acceptance"
        )

    dims = (
        abs(float(root.bfc_width)),
        abs(float(root.bfc_depth)),
        abs(float(root.bfc_height)),
    )
    max_dimension = max(dims) if dims else 0.0
    positive = [value for value in dims if value > 1e-9]
    min_dimension = min(positive) if positive else 0.0
    stats["dimensions"] = list(dims)

    typical_max = TYPICAL_MAX_DIMENSION.get(family_kind)
    typical_min = TYPICAL_MIN_DIMENSION.get(family_kind)
    if typical_max is not None and max_dimension > typical_max:
        severe.append(
            f"Family envelope {max_dimension:.3f} m is unusually large for {family_kind}; check source units"
        )
    if typical_min is not None and min_dimension and min_dimension < typical_min:
        warnings.append(
            f"Family envelope has a {min_dimension:.3f} m axis; check source units/orientation"
        )

    review_recommended = bool(severe or warnings)
    return {
        "familyKind": family_kind,
        "reviewRecommended": review_recommended,
        "stats": stats,
        "warnings": warnings,
        "severe": severe,
    }
