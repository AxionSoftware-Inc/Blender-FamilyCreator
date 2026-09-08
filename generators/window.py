from .opening_base import apply_opening_parameters


def rebuild(root):
    result = apply_opening_parameters(root)
    if not result["changed"]:
        return {"changed": False, "message": "Window Frame Width is Auto/zero or frame roles were not detected"}

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    result["message"] = f"Applied window frame geometry to {result['affected']} member(s)"
    return result
