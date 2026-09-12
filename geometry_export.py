from pathlib import Path

import bpy

from . import core


def _object_exists(obj):
    try:
        return obj is not None and obj.name in bpy.data.objects
    except Exception:
        return False


def _hide_get(obj):
    try:
        return bool(obj.hide_get())
    except Exception:
        return False


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
            previous_visibility[obj] = {
                "hideViewport": bool(getattr(obj, "hide_viewport", False)),
                "hideRender": bool(getattr(obj, "hide_render", False)),
                "hideSet": _hide_get(obj),
            }
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
        # Selection restoration requires objects to be selectable first, so keep
        # exported members temporarily visible until selection/active state is
        # restored, then reinstate every viewport/render hide flag exactly.
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            pass

        for obj in previous_visibility:
            if not _object_exists(obj):
                continue
            try:
                obj.hide_set(False)
            except Exception:
                pass
            try:
                obj.hide_viewport = False
            except Exception:
                pass

        for obj in previous_selection:
            if _object_exists(obj):
                try:
                    obj.select_set(True)
                except Exception:
                    pass

        if _object_exists(previous_active):
            try:
                bpy.context.view_layer.objects.active = previous_active
            except Exception:
                pass

        for obj, state in previous_visibility.items():
            if not _object_exists(obj):
                continue
            try:
                obj.hide_render = bool(state["hideRender"])
            except Exception:
                pass
            try:
                obj.hide_viewport = bool(state["hideViewport"])
            except Exception:
                pass
            try:
                obj.hide_set(bool(state["hideSet"]))
            except Exception:
                pass

    return filepath


def export_glb_geometry(root, filepath):
    members = core.exportable_family_members(root)
    if not members:
        raise ValueError("Family has no exportable members")
    return export_glb_objects(members, filepath)
