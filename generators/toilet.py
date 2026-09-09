from .common import role_members, semantic_float, set_family_local_location


def rebuild(root):
    connector_height = semantic_float(root, "connector_height", 0.0)
    connectors = role_members(root, {"CONNECTOR"}, include_generated=False)
    if connector_height <= 0.0:
        return {"changed": False, "message": "Toilet connector height is Auto/zero"}
    if not connectors:
        return {"changed": False, "message": "Toilet generator needs a member classified as CONNECTOR"}

    bottom = -float(root.bfc_height) * 0.5
    target_z = bottom + connector_height
    for obj in connectors:
        set_family_local_location(root, obj, "Z", target_z)
        obj.bfc_rule_x = "FIXED"
        obj.bfc_rule_y = "FIXED"
        obj.bfc_rule_z = "FIXED"

    root["bfc_generator_revision"] = int(root.get("bfc_generator_revision", 0)) + 1
    return {
        "changed": True,
        "affected": len(connectors),
        "connectorHeight": connector_height,
        "message": f"Placed {len(connectors)} toilet connector member(s) at {connector_height:.3f} m",
    }
