from .casework_base import apply_casework_parameters


def rebuild(root):
    result = apply_casework_parameters(root, include_toe_kick=True)
    if not result["changed"]:
        return {"changed": False, "message": "Kitchen Base semantic panel/toe-kick parameters are Auto/zero or roles were not detected"}
    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    result["message"] = f"Applied kitchen-base geometry to {result['affected']} member(s)"
    return result
