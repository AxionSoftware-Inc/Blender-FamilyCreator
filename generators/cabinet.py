from .casework_base import apply_casework_parameters


def rebuild(root):
    result = apply_casework_parameters(root)
    if not result["changed"]:
        return {"changed": False, "message": "Cabinet Panel Thickness is Auto/zero or panel roles were not detected"}
    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    result["message"] = f"Applied cabinet panel geometry to {result['affected']} member(s)"
    return result
