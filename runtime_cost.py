"""Blender runtime-cost measurement for exported family geometry."""

from __future__ import annotations

from . import core
from .mobile_budget import evaluate_mobile_budget


def _source_materials(obj):
    data = getattr(obj, "data", None)
    slots = getattr(data, "materials", None)
    if slots is None:
        return []
    return [material for material in slots if material is not None]


def _mesh_cost(obj, depsgraph):
    evaluated = None
    mesh = None
    evaluated_materials = []
    try:
        evaluated = obj.evaluated_get(depsgraph)
        try:
            mesh = evaluated.to_mesh()
        except Exception:
            mesh = None

        if mesh is None:
            return (
                {"vertices": 0, "triangles": 0, "materialSlots": 0, "drawCallEstimate": 0},
                _source_materials(obj),
            )

        try:
            mesh.calc_loop_triangles()
            triangles = len(mesh.loop_triangles)
        except Exception:
            polygons = getattr(mesh, "polygons", ())
            triangles = sum(max(len(poly.vertices) - 2, 1) for poly in polygons)

        vertices = len(getattr(mesh, "vertices", ()))
        material_slots = len(getattr(mesh, "materials", ()))
        evaluated_materials = [
            material for material in getattr(mesh, "materials", ()) if material is not None
        ]

        # Vendor files often keep many unused material slots. Counting all slots
        # as draw calls creates noisy mobile-budget warnings, so estimate the
        # number of actual submesh/material submissions from evaluated polygon
        # material indices instead. An unmaterialed mesh still costs one draw.
        used_material_indices = {
            int(getattr(poly, "material_index", 0) or 0)
            for poly in getattr(mesh, "polygons", ())
        }
        draw_calls = len(used_material_indices) if triangles > 0 else 0
        if triangles > 0 and draw_calls == 0:
            draw_calls = 1

        return (
            {
                "vertices": int(vertices),
                "triangles": int(triangles),
                "materialSlots": int(material_slots),
                "drawCallEstimate": int(draw_calls),
            },
            evaluated_materials,
        )
    finally:
        if mesh is not None and evaluated is not None:
            try:
                evaluated.to_mesh_clear()
            except Exception:
                pass


def _material_key(material):
    try:
        return int(material.as_pointer())
    except Exception:
        return id(material)


def _node_tree_key(tree):
    try:
        return int(tree.as_pointer())
    except Exception:
        return id(tree)


def _image_key(image):
    try:
        return int(image.as_pointer())
    except Exception:
        return id(image)


def _iter_node_tree_images(node_tree, visited=None):
    if node_tree is None:
        return
    visited = visited if visited is not None else set()
    key = _node_tree_key(node_tree)
    if key in visited:
        return
    visited.add(key)

    for node in getattr(node_tree, "nodes", ()):
        image = getattr(node, "image", None)
        if image is not None:
            yield image
        child_tree = getattr(node, "node_tree", None)
        if child_tree is not None:
            yield from _iter_node_tree_images(child_tree, visited)


def _material_and_texture_cost(material_candidates):
    materials = {}
    images = {}

    for material in material_candidates:
        if material is None:
            continue
        materials[_material_key(material)] = material

    for material in materials.values():
        node_tree = getattr(material, "node_tree", None)
        for image in _iter_node_tree_images(node_tree):
            images[_image_key(image)] = image

    texture_records = []
    total_pixels = 0
    total_rgba_bytes = 0
    max_dimension = 0
    for image in images.values():
        try:
            width = max(int(image.size[0]), 0)
            height = max(int(image.size[1]), 0)
        except Exception:
            width = 0
            height = 0
        pixels = width * height
        rgba_bytes = pixels * 4
        total_pixels += pixels
        total_rgba_bytes += rgba_bytes
        max_dimension = max(max_dimension, width, height)
        texture_records.append({
            "name": str(getattr(image, "name", "")),
            "width": width,
            "height": height,
            "pixels": pixels,
            "estimatedBytesRGBA": rgba_bytes,
        })

    texture_records.sort(key=lambda item: item["name"].lower())
    return {
        "uniqueMaterials": len(materials),
        "textureCount": len(images),
        "texturePixels": int(total_pixels),
        "maxTextureDimension": int(max_dimension),
        "estimatedTextureBytesRGBA": int(total_rgba_bytes),
        "estimatedTextureMemoryMiB": round(float(total_rgba_bytes) / (1024.0 * 1024.0), 3),
        "textures": texture_records,
    }


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
    draw_call_estimate = 0
    mesh_objects = 0
    non_mesh_objects = 0
    members_cost = []
    material_candidates = []

    for obj in members:
        if depsgraph is None:
            cost = {"vertices": 0, "triangles": 0, "materialSlots": 0, "drawCallEstimate": 0}
            evaluated_materials = _source_materials(obj)
        else:
            cost, evaluated_materials = _mesh_cost(obj, depsgraph)
        material_candidates.extend(evaluated_materials)

        if cost["triangles"] or getattr(obj, "type", None) == "MESH":
            mesh_objects += 1
        else:
            non_mesh_objects += 1
        total_vertices += cost["vertices"]
        total_triangles += cost["triangles"]
        material_slots += cost["materialSlots"]
        draw_call_estimate += cost["drawCallEstimate"]
        members_cost.append({
            "name": str(getattr(obj, "name", "")),
            "role": str(getattr(obj, "bfc_member_role", "UNKNOWN") or "UNKNOWN"),
            **cost,
        })

    resource_cost = _material_and_texture_cost(material_candidates)
    cost = {
        "measurement": "EVALUATED_TRIANGULATED_GEOMETRY",
        "textureMemoryEstimate": "UNCOMPRESSED_RGBA8",
        "memberCount": len(members),
        "meshObjects": mesh_objects,
        "nonMeshObjects": non_mesh_objects,
        "vertices": total_vertices,
        "triangles": total_triangles,
        "materialSlots": material_slots,
        "drawCallEstimate": draw_call_estimate,
        **resource_cost,
        "members": members_cost,
    }
    family_kind = getattr(root, "bfc_family_kind", "GENERIC")
    return cost, evaluate_mobile_budget(cost, family_kind)
