from pathlib import Path

import bpy

from . import core


def export_glb_objects(objects, filepath):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    members = [obj for obj in objects if obj is not None]
    if not members:
        raise ValueError("No exportable objects")

    previous_selection = list(bpy.context.selected_objects)
    previous_active = bpy.context.view_layer.objects.active
    previous_visibility = {}

    try:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in members:
            previous_visibility[obj] = (
                bool(getattr(obj, "hide_viewport", False)),
                bool(getattr(obj, "hide_render", False)),
            )
            try:
                obj.hide_set(False)
            except Exception:
                pass
            obj.hide_viewport = False
            obj.hide_render = False
            obj.select_set(True)

        bpy.context.view_layer.objects.active = members[0]
        bpy.ops.export_scene.gltf(
            filepath=str(filepath),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_extras=True,
            export_animations=False,
            export_yup=True,
        )
    finally:
        bpy.ops.object.select_all(action="DESELECT")
        for obj, (hide_viewport, hide_render) in previous_visibility.items():
            if obj and obj.name in bpy.data.objects:
                obj.hide_viewport = hide_viewport
                obj.hide_render = hide_render
        for obj in previous_selection:
            if obj and obj.name in bpy.data.objects:
                try:
                    obj.select_set(True)
                except Exception:
                    pass
        if previous_active and previous_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = previous_active

    return filepath


def export_glb_geometry(root, filepath):
    members = core.exportable_family_members(root)
    if not members:
        raise ValueError("Family has no exportable members")
    return export_glb_objects(members, filepath)
