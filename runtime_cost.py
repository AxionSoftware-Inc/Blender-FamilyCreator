"""Blender runtime-cost measurement for exported family geometry."""

from __future__ import annotations

from . import core
from .mobile_budget import evaluate_mobile_budget


def _mesh_cost(obj, depsgraph):
    evaluated = None
    mesh = None
    temporary = False
    try:
        evaluated = obj.evaluated_get(depsgraph)
        data = getattr(evaluated, "data", None)
        if getattr(evaluated, "type", None) == "MESH" and data is not None:
            mesh = data
        else:
            try:
                mesh = evaluated.to_mesh()
                temporary = mesh is not None
            except Exception:
                mesh = None

        if mesh is None:
            return {"vertices": 0, "triangles": 0, "materialSlots": 0}

        try:
            mesh.calc_loop_triangles()
            triangles = len(mesh.loop_triangles)
        except Exception:
            polygons = getattr(mesh, "polygons", ())
            triangles = sum(max(len(poly.vertices) - 2, 1) for poly in polygons)

        vertices = len(getattr(mesh, "vertices", ()))
        material_slots = len(getattr(mesh, "materials", ()))
        return {
            "vertices": int(vertices),
            "triangles": int(triangles),
            "materialSlots": int(material_slots),
        }
    finally:
        if temporary and evaluated is not None:
            try:
                evaluated.to_mesh_clear()
            except Exception:
                pass


def family_runtime_cost(root):
    members = list(core.exportable_family_members(root))
    depsgraph = None
    try:
        import bpy

        depsgraph = bpy.context.evaluated_depsgraph_get()
    except Exception:
        depsgraph = None

    total_vertices = 0
    total_triangles = 0
    material_slots = 0
    mesh_objects = 0
    non_mesh_objects = 0
    members_cost = []

    for obj in members:
        if depsgraph is None:
            cost = {"vertices": 0, "triangles": 0, "materialSlots": 0}
        else:
            cost = _mesh_cost(obj, depsgraph)
        if cost["triangles"] or getattr(obj, "type", None) == "MESH":
            mesh_objects += 1
        else:
            non_mesh_objects += 1
        total_vertices += cost["vertices"]
        total_triangles += cost["triangles"]
        material_slots += cost["materialSlots"]
        members_cost.append({
            "name": str(getattr(obj, "name", "")),
            "role": str(getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"),
            **cost,
        })

    cost = {
        "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
        "memberCount": len(members),
        "meshObjects": mesh_objects,
        "nonMeshObjects": non_mesh_objects,
        "vertices": total_vertices,
        "triangles": total_triangles,
        "materialSlots": material_slots,
        "members": members_cost,
    }
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    return cost, evaluate_mobile_budget(cost, family_kind)
