from pathlib import Path

import bpy
from mathutils import Vector

from . import core


DEFAULT_THUMBNAIL_SIZE = 512


def _look_at(obj, target):
    direction = Vector(target) - obj.location
    if direction.length <= 1e-9:
        return
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _render_engines(scene):
    try:
        prop = scene.render.bl_rna.properties["engine"]
        return {item.identifier for item in prop.enum_items}
    except Exception:
        return set()


def _create_area_light(scene, name, location, target, energy, size):
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = float(energy)
    data.shape = "DISK"
    data.size = max(float(size), 0.1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = Vector(location)
    _look_at(obj, target)
    return obj, data


def _snapshot_render(scene):
    render = scene.render
    image = render.image_settings
    return {
        "camera": scene.camera,
        "world": scene.world,
        "engine": render.engine,
        "filepath": render.filepath,
        "resolution_x": render.resolution_x,
        "resolution_y": render.resolution_y,
        "resolution_percentage": render.resolution_percentage,
        "film_transparent": render.film_transparent,
        "file_format": image.file_format,
        "color_mode": image.color_mode,
        "color_depth": image.color_depth,
    }


def _restore_render(scene, state):
    render = scene.render
    image = render.image_settings
    scene.camera = state["camera"]
    scene.world = state["world"]
    try:
        render.engine = state["engine"]
    except Exception:
        pass
    render.filepath = state["filepath"]
    render.resolution_x = state["resolution_x"]
    render.resolution_y = state["resolution_y"]
    render.resolution_percentage = state["resolution_percentage"]
    render.film_transparent = state["film_transparent"]
    image.file_format = state["file_format"]
    try:
        image.color_mode = state["color_mode"]
    except Exception:
        pass
    try:
        image.color_depth = state["color_depth"]
    except Exception:
        pass


def render_family_thumbnail(root, filepath, size=DEFAULT_THUMBNAIL_SIZE):
    """Render a square transparent family preview without changing authoring state.

    This is intentionally an optional library-production feature. Callers should
    treat failures as warnings rather than family-export failures. A failed
    render is also responsible for deleting any partially written output file so
    package staging can never commit an unreferenced corrupt thumbnail.
    """
    scene = bpy.context.scene
    members = core.exportable_family_members(root)
    if not members:
        raise ValueError("Family has no exportable members for thumbnail")

    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    size = max(64, min(int(size), 2048))

    mins, maxs = core.objects_bbox_world(members)
    center = (mins + maxs) * 0.5
    dims = maxs - mins
    max_dim = max(float(dims.x), float(dims.y), float(dims.z), 0.05)
    framing = max(float(dims.length) * 1.05, max_dim * 1.35, 0.25)

    render_state = _snapshot_render(scene)
    visibility = {obj: bool(obj.hide_render) for obj in scene.objects}
    temp_objects = []
    temp_data = []
    temp_world = None

    try:
        exportable = set(members)
        for obj in scene.objects:
            obj.hide_render = obj not in exportable

        camera_data = bpy.data.cameras.new("__BFC_ThumbnailCamera")
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = framing
        camera_data.clip_start = 0.01
        camera_data.clip_end = max(max_dim * 20.0, 100.0)
        camera = bpy.data.objects.new("__BFC_ThumbnailCamera", camera_data)
        scene.collection.objects.link(camera)
        temp_objects.append(camera)
        temp_data.append(camera_data)

        view = Vector((1.45, -1.8, 1.15)).normalized()
        camera.location = center + view * max(max_dim * 3.0, 2.0)
        _look_at(camera, center)
        scene.camera = camera

        light_scale = max(max_dim, 0.5)
        key_obj, key_data = _create_area_light(
            scene,
            "__BFC_ThumbnailKey",
            center + Vector((1.8, -2.2, 2.8)) * light_scale,
            center,
            700.0 * light_scale * light_scale,
            max_dim * 1.8,
        )
        fill_obj, fill_data = _create_area_light(
            scene,
            "__BFC_ThumbnailFill",
            center + Vector((-2.0, -0.8, 1.5)) * light_scale,
            center,
            350.0 * light_scale * light_scale,
            max_dim * 2.2,
        )
        rim_obj, rim_data = _create_area_light(
            scene,
            "__BFC_ThumbnailRim",
            center + Vector((0.7, 2.4, 2.0)) * light_scale,
            center,
            450.0 * light_scale * light_scale,
            max_dim * 1.6,
        )
        temp_objects.extend((key_obj, fill_obj, rim_obj))
        temp_data.extend((key_data, fill_data, rim_data))

        temp_world = bpy.data.worlds.new("__BFC_ThumbnailWorld")
        temp_world.use_nodes = False
        temp_world.color = (0.05, 0.05, 0.05)
        scene.world = temp_world

        render = scene.render
        engines = _render_engines(scene)
        if "BLENDER_EEVEE" in engines:
            render.engine = "BLENDER_EEVEE"
        render.resolution_x = size
        render.resolution_y = size
        render.resolution_percentage = 100
        render.film_transparent = True
        render.filepath = str(filepath)
        render.image_settings.file_format = "PNG"
        try:
            render.image_settings.color_mode = "RGBA"
            render.image_settings.color_depth = "8"
        except Exception:
            pass

        bpy.ops.render.render(write_still=True)
        if not filepath.exists() or filepath.stat().st_size <= 0:
            raise RuntimeError("Blender did not create the thumbnail file")

        return {
            "uri": filepath.name,
            "width": size,
            "height": size,
            "format": "PNG",
            "transparent": True,
        }
    except Exception:
        try:
            filepath.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    finally:
        for obj, hidden in visibility.items():
            if obj and obj.name in bpy.data.objects:
                obj.hide_render = hidden

        _restore_render(scene, render_state)

        for obj in reversed(temp_objects):
            try:
                if obj and obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            except Exception:
                pass
        for data in temp_data:
            try:
                if isinstance(data, bpy.types.Camera) and data.name in bpy.data.cameras:
                    bpy.data.cameras.remove(data)
                elif isinstance(data, bpy.types.Light) and data.name in bpy.data.lights:
                    bpy.data.lights.remove(data)
            except Exception:
                pass
        if temp_world is not None:
            try:
                if temp_world.name in bpy.data.worlds:
                    bpy.data.worlds.remove(temp_world)
            except Exception:
                pass
