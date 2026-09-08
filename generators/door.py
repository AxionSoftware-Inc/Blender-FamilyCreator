from .opening_base import apply_opening_parameters


def rebuild(root):
    result = apply_opening_parameters(
        root,
        panel_role="DOOR_LEAF",
        panel_thickness_parameter="panel_thickness",
    )
    if not result["changed"]:
        return {"changed": False, "message": "Door frame/panel parameters are Auto/zero or roles were not detected"}

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    result["message"] = f"Applied door semantic geometry to {result['affected']} member(s)"
    return result
