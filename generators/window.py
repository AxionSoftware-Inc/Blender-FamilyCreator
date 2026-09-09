from .common import role_members, semantic_float
from .opening_base import apply_opening_parameters


_FRAME_ROLES = {"FRAME_LEFT", "FRAME_RIGHT", "FRAME_HEAD", "FRAME_SILL", "MULLION"}


def rebuild(root):
    frame_members = role_members(root, _FRAME_ROLES, include_generated=True)
    if not frame_members:
        return {
            "changed": False,
            "reasonCode": "NO_SEPARATE_FRAME",
            "message": "No separate frame members; baked source geometry kept",
        }

    frame_width = semantic_float(root, "frame_width", 0.0)
    if frame_width <= 0.0:
        return {
            "changed": False,
            "reasonCode": "PARAMETER_AUTO",
            "message": "Window Frame Width is Auto/zero; source frame geometry kept",
        }

    result = apply_opening_parameters(root)
    if not result["changed"]:
        return {
            "changed": False,
            "reasonCode": "NO_EFFECT",
            "message": "Window frame parameters produced no geometry change",
        }

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    result["message"] = f"Applied window frame geometry to {result['affected']} member(s)"
    return result
