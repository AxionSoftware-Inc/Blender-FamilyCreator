from ..family_types.parameter_specs import property_name
from ..family_types.stair import solve_parameters
from .common import (
    choose_center_prototype,
    clear_generated,
    duplicate_template,
    local_span,
    prepare_template_group,
    resize_family_axis,
    set_family_local_location,
)


TREAD_GROUP = "STAIR_TREADS"
RISER_GROUP = "STAIR_RISERS"


def _float(root, name, fallback=0.0):
    try:
        return float(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return float(fallback)


def _int(root, name, fallback=0):
    try:
        return int(root.get(property_name(name), fallback))
    except (TypeError, ValueError):
        return int(fallback)


def _solve_from_root(root):
    step_count = _int(root, "step_count", 0)
    tread_depth = _float(root, "tread_depth", 0.0)
    riser_height = _float(root, "riser_height", 0.0)
    total_run = _float(root, "total_run", 0.0)
    total_rise = _float(root, "total_rise", 0.0)

    return solve_parameters(
        step_count=step_count if step_count > 0 else None,
        tread_depth=tread_depth if tread_depth > 0 else None,
        riser_height=riser_height if step_count > 0 and riser_height > 0 else None,
        total_run=total_run if total_run > 0 else None,
        total_rise=total_rise if total_rise > 0 else None,
        target_riser_height=riser_height if riser_height > 0 else 0.175,
    )


def _write_solved(root, solved):
    for name, value in solved.items():
        root[property_name(name)] = int(value) if name == "step_count" else float(value)

    # Stair run/rise are semantic dimensions generated procedurally rather than
    # ordinary scaling axes. Keep the exported overall envelope honest.
    root["bfc_applying"] = True
    try:
        root.bfc_depth = float(solved["total_run"])
        root.bfc_height = float(solved["total_rise"])
    finally:
        root["bfc_applying"] = False


def rebuild(root):
    clear_generated(root, TREAD_GROUP)
    clear_generated(root, RISER_GROUP)

    try:
        solved = _solve_from_root(root)
    except ValueError as exc:
        return {"changed": False, "message": str(exc)}

    tread_templates = prepare_template_group(root, {"TREAD"}, TREAD_GROUP)
    riser_templates = prepare_template_group(root, {"RISER"}, RISER_GROUP)
    if not tread_templates:
        return {
            "changed": False,
            "message": "STAIR generator needs at least one member classified as TREAD",
        }

    _write_solved(root, solved)

    tread_proto = choose_center_prototype(tread_templates, root, axis=1)
    riser_proto = choose_center_prototype(riser_templates, root, axis=1) if riser_templates else None

    count = int(solved["step_count"])
    tread_depth = float(solved["tread_depth"])
    riser_height = float(solved["riser_height"])
    total_run = float(solved["total_run"])
    total_rise = float(solved["total_rise"])
    start_y = -total_run * 0.5
    start_z = -total_rise * 0.5
    tread_thickness = max(float(local_span(tread_proto, root).z), 0.001)

    generated = []
    for index in range(count):
        tread = duplicate_template(
            root,
            tread_proto,
            TREAD_GROUP,
            f"{root.bfc_family_name}_Tread_{index + 1:02d}",
            role="TREAD",
        )
        resize_family_axis(root, tread, "X", float(root.bfc_width))
        resize_family_axis(root, tread, "Y", tread_depth)
        set_family_local_location(root, tread, "Y", start_y + tread_depth * (index + 0.5))
        set_family_local_location(
            root,
            tread,
            "Z",
            start_z + riser_height * (index + 1) - tread_thickness * 0.5,
        )
        tread.bfc_rule_x = "STRETCH"
        tread.bfc_rule_y = "FIXED"
        tread.bfc_rule_z = "FIXED"
        generated.append(tread)

        if riser_proto is not None:
            riser = duplicate_template(
                root,
                riser_proto,
                RISER_GROUP,
                f"{root.bfc_family_name}_Riser_{index + 1:02d}",
                role="RISER",
            )
            resize_family_axis(root, riser, "X", float(root.bfc_width))
            resize_family_axis(root, riser, "Z", riser_height)
            set_family_local_location(root, riser, "Y", start_y + tread_depth * (index + 1))
            set_family_local_location(root, riser, "Z", start_z + riser_height * (index + 0.5))
            riser.bfc_rule_x = "STRETCH"
            riser.bfc_rule_y = "FIXED"
            riser.bfc_rule_z = "FIXED"
            generated.append(riser)

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    message = f"Generated {count} stair steps"
    if riser_proto is None:
        message += " (no RISER template found; treads only)"

    return {
        "changed": True,
        "generated": len(generated),
        "stepCount": count,
        "parameters": solved,
        "message": message,
    }
