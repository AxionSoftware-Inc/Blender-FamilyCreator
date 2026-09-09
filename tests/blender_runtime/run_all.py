"""Deterministic Blender 5.2 runtime validation for Axion Family Creator.

Run with Blender, not normal Python. The repository root is loaded as a
package under a valid temporary module name because the Git checkout name may
contain a hyphen.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "tests" / "blender_runtime" / "artifacts"
ADDON_NAME = "bfc_runtime_addon"


def load_addon():
    spec = importlib.util.spec_from_file_location(
        ADDON_NAME,
        REPO_ROOT / "__init__.py",
        submodule_search_locations=[str(REPO_ROOT)],
    )
    addon = importlib.util.module_from_spec(spec)
    sys.modules[ADDON_NAME] = addon
    spec.loader.exec_module(addon)
    return addon


addon = load_addon()


def clean_scene():
    if bpy.context.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.users == 0:
            bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    scene.camera = None
    scene.render.filepath = ""


def select_only(objects, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj and obj.name in bpy.data.objects:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = active or (objects[0] if objects else None)


def set_dimensions(root, width=None, depth=None, height=None):
    root["bfc_applying"] = True
    try:
        if width is not None:
            root.bfc_width = float(width)
        if depth is not None:
            root.bfc_depth = float(depth)
        if height is not None:
            root.bfc_height = float(height)
    finally:
        root["bfc_applying"] = False
    addon.core.apply_family(root)


def set_semantic(root, name, value):
    root[addon.family_types.parameter_specs.property_name(name)] = value


def cube(name, dimensions, location=(0.0, 0.0, 0.0), *, apply=True, material=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple(float(v) for v in dimensions)
    if apply:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material is not None:
        if not obj.data.materials:
            obj.data.materials.append(material)
    return obj


def new_material(name="RuntimeMaterial"):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (0.18, 0.42, 0.72, 1.0)
    return material


def make_asset(kind):
    """Create a deterministic source asset with semantic names."""
    objects = []
    if kind == "SOFA":
        objects += [
            cube("Seat_Left", (0.78, 0.72, 0.18), (-0.45, 0.0, 0.10)),
            cube("Seat_Right", (0.78, 0.72, 0.18), (0.45, 0.0, 0.10)),
            cube("Back", (1.95, 0.18, 0.62), (0.0, 0.28, 0.46)),
            cube("Arm_Left", (0.20, 0.80, 0.55), (-1.05, 0.0, 0.34)),
            cube("Arm_Right", (0.20, 0.80, 0.55), (1.05, 0.0, 0.34)),
        ]
        for x in (-0.82, 0.82):
            for y in (-0.26, 0.26):
                objects.append(cube(f"Leg_{'L' if x < 0 else 'R'}_{'F' if y < 0 else 'B'}", (0.10, 0.10, 0.25), (x, y, -0.125)))
    elif kind == "TABLE":
        objects.append(cube("Top", (1.80, 1.00, 0.08), (0.0, 0.0, 0.78)))
        for x in (-0.76, 0.76):
            for y in (-0.36, 0.36):
                objects.append(cube(f"Leg_{'L' if x < 0 else 'R'}_{'F' if y < 0 else 'B'}", (0.10, 0.10, 0.74), (x, y, 0.37)))
        objects += [
            cube("Apron_Front", (1.55, 0.08, 0.12), (0.0, -0.43, 0.68)),
            cube("Apron_Side", (0.08, 0.70, 0.12), (-0.83, 0.0, 0.68)),
        ]
    elif kind == "CHAIR":
        objects += [
            cube("Seat", (0.82, 0.82, 0.12), (0.0, 0.0, 0.52)),
            cube("Back", (0.82, 0.12, 0.72), (0.0, 0.36, 0.88)),
        ]
        for x in (-0.32, 0.32):
            for y in (-0.30, 0.30):
                objects.append(cube(f"Leg_{'L' if x < 0 else 'R'}_{'F' if y < 0 else 'B'}", (0.09, 0.09, 0.50), (x, y, 0.25)))
    elif kind == "BED":
        objects += [
            cube("Mattress", (2.0, 2.0, 0.25), (0.0, 0.0, 0.58)),
            cube("Base", (2.10, 2.10, 0.18), (0.0, 0.0, 0.36)),
            cube("Headboard", (2.10, 0.12, 1.10), (0.0, 0.96, 0.78)),
            cube("Footboard", (2.10, 0.10, 0.38), (0.0, -0.96, 0.55)),
        ]
    elif kind in {"CABINET", "WARDROBE", "SHELF", "KITCHEN_BASE", "KITCHEN_WALL"}:
        objects += [
            cube("Side_Left", (0.06, 0.62, 1.20), (-0.57, 0.0, 0.60)),
            cube("Side_Right", (0.06, 0.62, 1.20), (0.57, 0.0, 0.60)),
            cube("Top", (1.20, 0.62, 0.06), (0.0, 0.0, 1.17)),
            cube("Bottom", (1.20, 0.62, 0.06), (0.0, 0.0, 0.03)),
            cube("Back", (1.10, 0.04, 1.08), (0.0, 0.29, 0.60)),
            cube("Shelf", (1.08, 0.55, 0.05), (0.0, 0.0, 0.60)),
            cube("Door", (1.08, 0.04, 1.08), (0.0, -0.32, 0.60)),
            cube("Handle", (0.05, 0.05, 0.16), (0.35, -0.37, 0.60)),
        ]
    elif kind == "DOOR":
        objects += [
            cube("Left_Jamb", (0.12, 0.16, 2.10), (-0.54, 0.0, 1.05)),
            cube("Right_Jamb", (0.12, 0.16, 2.10), (0.54, 0.0, 1.05)),
            cube("Head", (1.20, 0.16, 0.12), (0.0, 0.0, 2.04)),
            cube("Door_Leaf", (1.04, 0.05, 1.94), (0.0, 0.0, 1.00)),
            cube("Handle", (0.05, 0.08, 0.16), (0.35, -0.10, 1.00)),
            cube("Hinge_Upper", (0.05, 0.05, 0.12), (-0.54, -0.10, 1.65)),
            cube("Hinge_Lower", (0.05, 0.05, 0.12), (-0.54, -0.10, 0.35)),
        ]
    elif kind == "WINDOW":
        objects += [
            cube("Frame_Left", (0.10, 0.12, 1.20), (-0.55, 0.0, 1.0)),
            cube("Frame_Right", (0.10, 0.12, 1.20), (0.55, 0.0, 1.0)),
            cube("Frame_Head", (1.20, 0.12, 0.10), (0.0, 0.0, 1.55)),
            cube("Sill", (1.20, 0.12, 0.10), (0.0, 0.0, 0.45)),
            cube("Sash", (0.98, 0.06, 1.08), (0.0, 0.0, 1.0)),
            cube("Glass", (0.84, 0.02, 0.96), (0.0, -0.04, 1.0)),
            cube("Mullion", (0.06, 0.04, 1.00), (0.0, -0.05, 1.0)),
        ]
    elif kind == "STAIR":
        objects += [
            cube("Tread_Template", (1.0, 0.28, 0.06), (0.0, -0.46, 0.03)),
            cube("Riser_Template", (1.0, 0.05, 0.20), (0.0, -0.30, 0.10)),
        ]
    elif kind == "SINK":
        objects += [
            cube("Basin", (1.0, 0.62, 0.20), (0.0, 0.0, 0.10)),
            cube("Drain", (0.10, 0.10, 0.05), (0.0, 0.0, 0.22)),
            cube("Faucet", (0.10, 0.10, 0.45), (0.30, 0.18, 0.33)),
        ]
    elif kind == "BATHTUB":
        objects += [
            cube("Tub", (1.80, 0.78, 0.40), (0.0, 0.0, 0.20)),
            cube("Rim", (1.80, 0.05, 0.05), (0.0, -0.36, 0.42)),
            cube("Drain", (0.10, 0.10, 0.05), (0.55, 0.20, 0.42)),
        ]
    elif kind == "TOILET":
        objects += [
            cube("Bowl", (0.70, 0.90, 0.58), (0.0, 0.0, 0.29)),
            cube("Tank", (0.70, 0.25, 0.78), (0.0, 0.35, 0.75)),
            cube("Seat", (0.64, 0.78, 0.06), (0.0, 0.0, 0.60)),
            cube("Connector", (0.12, 0.12, 0.10), (0.0, 0.46, 0.10)),
        ]
    else:
        objects = [cube("Generic_Part", (1.0, 1.0, 1.0))]
    return objects


def family_for(kind, name=None):
    objects = make_asset(kind)
    root = addon.typed.create_typed_family(
        bpy.context,
        objects,
        name or f"Runtime_{kind}",
        kind,
    )
    select_only([root], root)
    return root, objects


def local_span(obj, root):
    minimum, maximum = addon.core.local_bbox(obj, root)
    return maximum - minimum


def local_bounds(root):
    members = addon.core.exportable_family_members(root)
    minimum, maximum = addon.core.objects_bbox_world(members)
    root_inverse = root.matrix_world.inverted_safe()
    points = [root_inverse @ Vector((minimum.x, minimum.y, minimum.z)), root_inverse @ Vector((maximum.x, maximum.y, maximum.z))]
    return points[0], points[1]


def generated_members(root, group=None):
    return [
        obj for obj in root.children_recursive
        if bool(obj.get(addon.core.GENERATED_FLAG, False))
        and (group is None or obj.get(addon.core.GENERATOR_GROUP, "") == group)
    ]


def source_named(root, name):
    return next(obj for obj in addon.core.family_members(root) if obj.name == name)


def remove_objects(objects):
    for obj in list(objects):
        if obj and obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def assert_file(path):
    path = Path(path)
    assert path.exists() and path.stat().st_size > 0, f"expected non-empty file: {path}"


def run_test(results, name, function):
    try:
        function()
    except Exception as exc:
        results["failures"].append({"test": name, "error": str(exc), "traceback": traceback.format_exc()})
        print(f"[FAIL] {name}: {exc}")
    else:
        results["passed"].append(name)
        print(f"[PASS] {name}")


def test_registration():
    addon.unregister()
    addon.register()
    addon.unregister()
    addon.register()
    assert len(addon.CLASSES) == 15


def test_operator_execution():
    clean_scene()
    objects = make_asset("TABLE")
    select_only(objects, objects[0])
    bpy.context.scene.bfc_new_family_name = "Operator_Table"
    bpy.context.scene.bfc_new_family_kind = "TABLE"
    assert bpy.ops.bfc.create_family() == {"FINISHED"}
    root = bpy.context.view_layer.objects.active
    assert root and root.bfc_family_kind == "TABLE"
    bpy.context.scene.bfc_type_query = "OperatorType"
    assert bpy.ops.bfc.save_type() == {"FINISHED"}
    assert bpy.ops.bfc.apply_family_class() == {"FINISHED"}
    assert bpy.ops.bfc.rebuild_procedural_geometry() in ({"FINISHED"}, {"CANCELLED"})
    bpy.context.scene.bfc_export_directory = str(ARTIFACTS / "operator_export")
    bpy.context.scene.bfc_export_glb = False
    bpy.context.scene.bfc_export_baked_types = False
    bpy.context.scene.bfc_export_thumbnail = False
    assert bpy.ops.bfc.export_family() == {"FINISHED"}
    assert (ARTIFACTS / "operator_export" / "operator_table.family.json").exists()


def test_sofa():
    clean_scene()
    root, objects = family_for("SOFA")
    roles = {obj.name: obj.bfc_member_role for obj in addon.core.family_members(root)}
    assert roles["Seat_Left"] == "SEAT" and roles["Seat_Right"] == "SEAT"
    assert roles["Back"] == "BACK"
    assert roles["Arm_Left"] == "ARM_LEFT" and roles["Arm_Right"] == "ARM_RIGHT"
    assert sum(role == "LEG" for role in roles.values()) == 4

    base_width = float(root.bfc_base_width)
    set_semantic(root, "arm_width", 0.25)
    set_semantic(root, "seat_count", 3)
    set_semantic(root, "seat_height", 0.48)
    set_dimensions(root, width=base_width * 1.30)
    result = addon.generators.rebuild_family_geometry(root)
    assert result["changed"] and result["seatCount"] == 3
    first_count = len(generated_members(root, "SOFA_SEATS"))
    first_objects = len(bpy.data.objects)
    addon.generators.rebuild_family_geometry(root)
    assert len(generated_members(root, "SOFA_SEATS")) == first_count
    assert len(bpy.data.objects) == first_objects
    assert len(generated_members(root, "SOFA_SEATS")) == 3
    assert any(obj.hide_render for obj in addon.core.family_members(root) if obj.get(addon.core.TEMPLATE_FLAG))

    addon.typed.save_typed_type(root, "3-seat", overwrite=True)
    set_semantic(root, "seat_count", 2)
    set_dimensions(root, width=base_width)
    addon.generators.rebuild_family_geometry(root)
    addon.typed.save_typed_type(root, "2-seat", overwrite=True)
    addon.typed.apply_typed_type(root, "3-seat")
    source_matrix = source_named(root, "Seat_Left").matrix_world.copy()
    addon.typed.apply_typed_type(root, "2-seat")
    addon.typed.apply_typed_type(root, "3-seat")
    assert (source_named(root, "Seat_Left").matrix_world.translation - source_matrix.translation).length < 1e-5, "sofa type switching drifted"


def test_table_chair_bed():
    clean_scene()
    root, _ = family_for("TABLE")
    set_semantic(root, "top_thickness", 0.12)
    table_result = addon.generators.rebuild_family_geometry(root)
    top = source_named(root, "Top")
    assert abs(float(local_span(top, root).z) - 0.12) < 1e-4, f"table top span={local_span(top, root).z}, semantic={root.get('bfc_sem_top_thickness')}, result={table_result}"
    assert local_span(source_named(root, "Leg_L_F"), root).z > 0.5, f"table leg span={local_span(source_named(root, 'Leg_L_F'), root).z}"
    set_dimensions(root, height=root.bfc_base_height * 1.5)
    minimum, _ = local_bounds(root)
    table_member_debug = {obj.name: tuple(float(v) for v in addon.core.local_bbox(obj, root)[0]) + tuple(float(v) for v in addon.core.local_bbox(obj, root)[1]) for obj in addon.core.exportable_family_members(root)}
    assert abs(float(minimum.z) + float(root.bfc_base_height) * 0.5) < 1e-4, f"table minz={minimum.z}, expected={-root.bfc_base_height * 0.5}, height={root.bfc_height}, base={root.bfc_base_height}, rootloc={tuple(root.location)}, worldmin={tuple(addon.core.objects_bbox_world(addon.core.exportable_family_members(root))[0])}, members={table_member_debug}"
    addon.typed.save_typed_type(root, "Tall", overwrite=True)
    addon.typed.apply_typed_type(root, "Default")
    addon.typed.apply_typed_type(root, "Tall")
    addon.typed.apply_typed_type(root, "Default")

    clean_scene()
    root, _ = family_for("CHAIR")
    set_semantic(root, "seat_height", 0.60)
    addon.generators.rebuild_family_geometry(root)
    seat = source_named(root, "Seat")
    seat_min, seat_max = addon.core.local_bbox(seat, root)
    assert abs(float(seat_max.z) - (-float(root.bfc_height) * 0.5 + 0.60)) < 1e-4
    assert local_span(source_named(root, "Leg_L_F"), root).z > 0.2

    clean_scene()
    root, _ = family_for("BED")
    set_semantic(root, "mattress_height", 0.34)
    addon.generators.rebuild_family_geometry(root)
    assert abs(float(local_span(source_named(root, "Mattress"), root).z) - 0.34) < 1e-4


def test_casework():
    clean_scene()
    root, _ = family_for("SHELF")
    set_semantic(root, "panel_thickness", 0.08)
    set_semantic(root, "shelf_count", 3)
    result = addon.generators.rebuild_family_geometry(root)
    assert result["changed"] and result["shelfCount"] == 3
    shelves = generated_members(root, "SHELF_LEVELS")
    assert len(shelves) == 3
    assert abs(float(local_span(source_named(root, "Top"), root).z) - 0.08) < 1e-4, f"casework top span={local_span(source_named(root, 'Top'), root).z}, semantic={root.get('bfc_sem_panel_thickness')}, result={result}"
    assert all(obj.get(addon.core.TEMPLATE_FLAG, False) for obj in addon.core.family_members(root) if obj.name == "Shelf")
    exportable_names = {obj.name for obj in addon.core.exportable_family_members(root)}
    assert "Shelf" not in exportable_names

    clean_scene()
    root, _ = family_for("CABINET")
    set_semantic(root, "panel_thickness", 0.09)
    result = addon.generators.rebuild_family_geometry(root)
    assert result["changed"]
    assert abs(float(local_span(source_named(root, "Side_Left"), root).x) - 0.09) < 1e-4


def test_additional_registered_classes():
    for kind in ("WARDROBE", "KITCHEN_BASE", "KITCHEN_WALL"):
        clean_scene()
        root, _ = family_for(kind)
        set_semantic(root, "panel_thickness", 0.08)
        result = addon.generators.rebuild_family_geometry(root)
        assert root.bfc_family_kind == kind
        assert result["supported"]

    clean_scene()
    root, _ = family_for("GENERIC")
    assert root.bfc_family_kind == "GENERIC"
    assert addon.generators.rebuild_family_geometry(root)["supported"] is False


def test_door_window():
    clean_scene()
    root, _ = family_for("DOOR")
    roles = {obj.name: obj.bfc_member_role for obj in addon.core.family_members(root)}
    assert roles["Left_Jamb"] == "FRAME_LEFT"
    assert roles["Right_Jamb"] == "FRAME_RIGHT"
    assert roles["Head"] == "FRAME_HEAD"
    assert roles["Door_Leaf"] == "DOOR_LEAF"
    assert roles["Handle"] == "HANDLE" and roles["Hinge_Upper"] == "HINGE"
    set_semantic(root, "frame_width", 0.10)
    set_semantic(root, "panel_thickness", 0.06)
    set_dimensions(root, width=1.35, height=2.40)
    addon.generators.rebuild_family_geometry(root)
    assert abs(float(local_span(source_named(root, "Door_Leaf"), root).y) - 0.06) < 1e-4
    hosting = addon.hosting.hosting_metadata(root)
    assert hosting["hostType"] == "WALL" and hosting["opening"]["width"] == root.bfc_width
    assert hosting["planRepresentation"]["hingeSide"] == "LEFT"
    assert hosting["canFlipFacing"] and hosting["canFlipHand"]
    minimum, _ = local_bounds(root)
    door_member_debug = {obj.name: tuple(float(v) for v in addon.core.local_bbox(obj, root)[0]) + tuple(float(v) for v in addon.core.local_bbox(obj, root)[1]) for obj in addon.core.exportable_family_members(root)}
    assert abs(float(minimum.z) + float(root.bfc_base_height) * 0.5) < 1e-4, f"door minz={minimum.z}, expected={-root.bfc_base_height * 0.5}, height={root.bfc_height}, base={root.bfc_base_height}, rootloc={tuple(root.location)}, worldmin={tuple(addon.core.objects_bbox_world(addon.core.exportable_family_members(root))[0])}, members={door_member_debug}"

    clean_scene()
    root, _ = family_for("WINDOW")
    roles = {obj.name: obj.bfc_member_role for obj in addon.core.family_members(root)}
    assert roles["Glass"] == "GLASS" and roles["Mullion"] == "MULLION"
    set_semantic(root, "frame_width", 0.12)
    set_semantic(root, "sill_height", 0.90)
    set_dimensions(root, width=1.5, height=1.6)
    addon.generators.rebuild_family_geometry(root)
    hosting = addon.hosting.hosting_metadata(root)
    assert hosting["hostType"] == "WALL" and hosting["elevationFromLevel"] == 0.90
    assert hosting["planRepresentation"]["type"] == "WINDOW_OPENING"


def test_stair_and_plumbing():
    clean_scene()
    root, _ = family_for("STAIR")
    set_semantic(root, "step_count", 4)
    set_semantic(root, "tread_depth", 0.30)
    set_semantic(root, "riser_height", 0.20)
    set_semantic(root, "total_run", 1.20)
    set_semantic(root, "total_rise", 0.80)
    result = addon.generators.rebuild_family_geometry(root)
    assert result["changed"] and result["stepCount"] == 4
    assert len(generated_members(root, "STAIR_TREADS")) == 4
    assert len(generated_members(root, "STAIR_RISERS")) == 4
    y_positions = sorted(round(float((addon.core.local_bbox(obj, root)[0].y + addon.core.local_bbox(obj, root)[1].y) * 0.5), 5) for obj in generated_members(root, "STAIR_TREADS"))
    assert y_positions == sorted(set(y_positions))
    count_before = len(bpy.data.objects)
    addon.generators.rebuild_family_geometry(root)
    assert len(bpy.data.objects) == count_before
    select_only([root], root)
    assert bpy.ops.bfc.solve_stair_parameters() == {"FINISHED"}

    clean_scene()
    root, _ = family_for("SINK")
    original_basin = local_span(source_named(root, "Basin"), root).copy()
    set_semantic(root, "drain_diameter", 0.16)
    addon.generators.rebuild_family_geometry(root)
    assert abs(float(local_span(source_named(root, "Drain"), root).x) - 0.16) < 1e-4, f"drain span={local_span(source_named(root, 'Drain'), root).x}, semantic={root.get('bfc_sem_drain_diameter')}"
    assert (local_span(source_named(root, "Basin"), root) - original_basin).length < 1e-4

    clean_scene()
    root, _ = family_for("BATHTUB")
    set_semantic(root, "rim_thickness", 0.08)
    addon.generators.rebuild_family_geometry(root)
    rim_span = local_span(source_named(root, "Rim"), root)
    assert max(float(v) for v in rim_span) > 1.0 and max(float(v) for v in rim_span) >= 0.079 and min(float(v) for v in rim_span) < 0.081, f"rim span={tuple(rim_span)}"

    clean_scene()
    root, _ = family_for("TOILET")
    original_bowl = source_named(root, "Bowl").matrix_world.copy()
    set_semantic(root, "connector_height", 0.20)
    addon.generators.rebuild_family_geometry(root)
    assert (source_named(root, "Bowl").matrix_world.translation - original_bowl.translation).length < 1e-5
    connector_center = (addon.core.local_bbox(source_named(root, "Connector"), root)[0].z + addon.core.local_bbox(source_named(root, "Connector"), root)[1].z) * 0.5
    assert abs(float(connector_center) - (-float(root.bfc_height) * 0.5 + 0.20)) < 1e-4


def test_hierarchy_and_preflight():
    clean_scene()
    parent = bpy.data.objects.new("Asset_Parent", None)
    bpy.context.collection.objects.link(parent)
    parent.location = (2.0, -1.0, 0.5)
    nested = bpy.data.objects.new("Nested_Empty", None)
    bpy.context.collection.objects.link(nested)
    nested.parent = parent
    nested.location = (0.2, 0.3, 0.1)
    first = cube("Hierarchy_Part", (1.0, 0.5, 0.5))
    first.rotation_euler = (0.17, -0.11, 0.29)
    first.parent = nested
    second = cube("Hierarchy_Part_2", (0.3, 0.3, 0.3), (2.8, -0.7, 0.8))
    second.parent = parent
    for obj in (first, second):
        obj["before_world"] = [float(v) for row in obj.matrix_world for v in row]
    root = addon.typed.create_typed_family(bpy.context, [parent, nested, first, second], "Hierarchy", "TABLE")
    assert nested.parent == parent and first.parent == nested and second.parent == parent
    for obj in (first, second):
        before = addon.core.list_to_matrix(obj["before_world"])
        assert (obj.matrix_world.translation - before.translation).length < 1e-5
    assert parent.get("bfc_is_helper") and nested.get("bfc_is_helper")
    assert all(bool(obj.get("bfc_exclude_export", False)) for obj in (parent, nested))

    clean_scene()
    mirrored = cube("Mirrored_Source", (1.0, 0.5, 0.5), apply=False)
    mirrored.scale = (-1.0, 1.0, 1.0)
    scaled = cube("Scaled_Source", (0.5, 0.5, 0.5), apply=False)
    scaled.scale = (2.0, 1.0, 1.0)
    root = addon.typed.create_typed_family(bpy.context, [mirrored, scaled], "Risky", "TABLE")
    preflight = addon.preflight.inspect_family(root)
    assert preflight["stats"]["negativeDeterminantMembers"] >= 1
    assert preflight["stats"]["nonUniformScaleMembers"] >= 1
    assert preflight["reviewRecommended"]


def test_modifier_aware_analysis():
    clean_scene()
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Solidified_Panel"
    solidify = plane.modifiers.new("Solidify", "SOLIDIFY")
    solidify.thickness = 0.25
    minimum, maximum = addon.core.object_bbox_world(plane)
    assert float(maximum.z - minimum.z) >= 0.24
    array = plane.modifiers.new("Array", "ARRAY")
    array.count = 3
    array.relative_offset_displace = (2.0, 0.0, 0.0)
    minimum, maximum = addon.core.object_bbox_world(plane)
    assert float(maximum.x - minimum.x) >= 2.9
    bevel = plane.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.02
    assert addon.core.object_bbox_world(plane)[1].x > 2.0


def test_auto_prepare():
    clean_scene()
    material = new_material("LoosePartMaterial")
    first = cube("Loose_Source_A", (0.4, 0.4, 0.4), (-1.0, 0.0, 0.2), material=material)
    second = cube("Loose_Source_B", (0.4, 0.4, 0.4), (1.0, 0.0, 0.2), material=material)
    select_only([first, second], first)
    bpy.ops.object.join()
    joined = bpy.context.object
    assert addon.prepare.count_loose_islands(joined.data) == 2
    result = addon.prepare.auto_prepare_objects(bpy.context, [joined], max_islands=4)
    assert result["split_objects"] == 1 and result["output_objects"] == 2
    assert all(obj.data.materials for obj in result["objects"])

    clean_scene()
    one = cube("One_Island", (1, 1, 1))
    report = addon.prepare.auto_prepare_objects(bpy.context, [one], max_islands=4)["reports"][0]
    assert report["reason"] == "single_island"

    clean_scene()
    shape = cube("Shape_Key", (1, 1, 1))
    shape.shape_key_add(name="Basis")
    report = addon.prepare.auto_prepare_objects(bpy.context, [shape], max_islands=4)["reports"][0]
    assert report["reason"] == "shape_keys"

    clean_scene()
    armature_data = bpy.data.armatures.new("ArmatureData")
    armature = bpy.data.objects.new("Armature", armature_data)
    bpy.context.collection.objects.link(armature)
    armature_mod_mesh = cube("Armature_Mesh", (1, 1, 1))
    armature_mod_mesh.modifiers.new("Armature", "ARMATURE").object = armature
    report = addon.prepare.auto_prepare_objects(bpy.context, [armature_mod_mesh], max_islands=4)["reports"][0]
    assert report["reason"] == "armature"

    clean_scene()
    parts = [cube(f"Fragment_{i}", (0.2, 0.2, 0.2), (i * 0.5, 0, 0.1)) for i in range(3)]
    select_only(parts, parts[0])
    bpy.ops.object.join()
    report = addon.prepare.auto_prepare_objects(bpy.context, [bpy.context.object], max_islands=2)["reports"][0]
    assert report["reason"] == "too_many_islands"


def test_export_variants_thumbnail_and_roundtrip():
    clean_scene()
    root, _ = family_for("SOFA", "Variant_Sofa")
    base_width = float(root.bfc_base_width)
    set_semantic(root, "seat_count", 2)
    addon.generators.rebuild_family_geometry(root)
    addon.typed.save_typed_type(root, "2-seat", overwrite=True)
    set_semantic(root, "seat_count", 3)
    set_dimensions(root, width=base_width * 1.40)
    addon.generators.rebuild_family_geometry(root)
    addon.typed.save_typed_type(root, "3-seat", overwrite=True)
    set_semantic(root, "seat_count", 4)
    set_dimensions(root, width=base_width * 1.90)
    addon.generators.rebuild_family_geometry(root)
    addon.typed.save_typed_type(root, "4-seat", overwrite=True)
    addon.typed.apply_typed_type(root, "3-seat")
    original = addon.variants.snapshot_family_state(root)
    export_dir = ARTIFACTS / "variant_export"
    manifest_path, glb_path = addon.typed.export_typed_family(
        root,
        export_dir,
        export_glb=True,
        export_baked_types=True,
        export_thumbnail=True,
    )
    assert_file(glb_path)
    assert_file(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    addon.schema.assert_valid_manifest(data)
    assert data["geometryStrategy"]["variantCount"] == 4, f"variant count={data['geometryStrategy']['variantCount']} names={list(data['geometryVariants'])}"
    assert set(data["geometryVariants"]) == {"Default", "2-seat", "3-seat", "4-seat"} or set(data["geometryVariants"]) == set(addon.core.read_types(root))
    assert data["activeType"] == "3-seat"
    assert data.get("thumbnail", {}).get("width") == 512
    for variant in data["geometryVariants"].values():
        assert_file(export_dir / variant["uri"])
    restored = addon.variants.snapshot_family_state(root)
    assert restored["typeName"] == original["typeName"]
    assert abs(restored["width"] - original["width"]) < 1e-6
    assert restored["semanticParameters"] == original["semanticParameters"]
    assert restored["generatorRevision"] == original["generatorRevision"]

    thumb = export_dir / data["thumbnail"]["uri"]
    assert_file(thumb)
    image = bpy.data.images.load(str(thumb), check_existing=False)
    assert tuple(image.size) == (512, 512)
    assert max(image.pixels[3::4]) > 0.0
    bpy.data.images.remove(image)
    assert not any(obj.name.startswith("__BFC_Thumbnail") for obj in bpy.data.objects)
    assert not any(data.name.startswith("__BFC_Thumbnail") for data in bpy.data.cameras)
    assert not any(data.name.startswith("__BFC_Thumbnail") for data in bpy.data.lights)
    assert bpy.context.scene.camera is None

    variant_dimensions = {}
    for type_name, variant in data["geometryVariants"].items():
        before = set(bpy.data.objects)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.import_scene.gltf(filepath=str(export_dir / variant["uri"]))
        imported = [obj for obj in bpy.data.objects if obj not in before]
        assert imported
        assert all("Template" not in obj.name for obj in imported)
        minimum, maximum = addon.core.objects_bbox_world(imported)
        variant_dimensions[type_name] = tuple(round(float(v), 4) for v in (maximum - minimum))
        remove_objects(imported)
    assert len({dimensions[0] for dimensions in variant_dimensions.values()}) >= 3, variant_dimensions

    second_manifest, second_glb = addon.typed.export_typed_family(
        root,
        export_dir,
        export_glb=True,
        export_baked_types=True,
        export_thumbnail=True,
    )
    assert_file(second_manifest)
    assert_file(second_glb)
    second_data = json.loads(second_manifest.read_text(encoding="utf-8"))
    addon.schema.assert_valid_manifest(second_data)
    assert second_data["geometryStrategy"]["variantCount"] == data["geometryStrategy"]["variantCount"]


def _save_raw_asset(kind, path, glb=False):
    clean_scene()
    objects = make_asset(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    select_only(objects, objects[0])
    if glb:
        bpy.ops.export_scene.gltf(
            filepath=str(path),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_extras=True,
            export_animations=False,
            export_yup=True,
        )
    else:
        bpy.ops.wm.save_as_mainfile(filepath=str(path))


def test_batch_and_catalog(results):
    assets = ARTIFACTS / "test_assets"
    exact_input = ARTIFACTS / "exact_assets"
    output = ARTIFACTS / "batch_library"
    _save_raw_asset("SOFA", exact_input / "sofa_exact.blend")
    _save_raw_asset("SOFA", assets / "sofas" / "sofa_02.glb", glb=True)
    _save_raw_asset("TABLE", assets / "tables" / "table_01.blend")
    _save_raw_asset("DOOR", assets / "doors" / "door_01.blend")
    _save_raw_asset("WINDOW", assets / "windows" / "window_01.blend")
    _save_raw_asset("STAIR", assets / "stairs" / "stair_01.blend")
    _save_raw_asset("GENERIC", assets / "unknown_things" / "foo.blend")

    clean_scene()
    counts_before_exact = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images), len(bpy.data.cameras), len(bpy.data.lights))
    exact_report = addon.batch.batch_convert_directory(
        bpy.context,
        exact_input,
        output,
        "SOFA",
        recursive=True,
        export_glb=True,
        export_baked_types=True,
        export_thumbnail=True,
        continue_on_error=True,
        auto_split_loose=False,
    )
    counts_after_exact = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images), len(bpy.data.cameras), len(bpy.data.lights))
    assert exact_report["converted"] == 1 and exact_report["failed"] == 0
    assert exact_report["resolved_class_counts"] == {"SOFA": 1}

    clean_scene()
    auto_report = addon.batch.batch_convert_directory(
        bpy.context,
        assets,
        output,
        "AUTO_FOLDER",
        recursive=True,
        export_glb=True,
        export_baked_types=True,
        export_thumbnail=True,
        continue_on_error=True,
        auto_split_loose=True,
    )
    counts_after_auto = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images), len(bpy.data.cameras), len(bpy.data.lights))
    assert counts_after_exact[0] == 0 and counts_after_auto[0] == 0
    assert counts_after_auto[1:] == counts_before_exact[1:], f"owned datablocks grew across batch: before={counts_before_exact}, exact={counts_after_exact}, auto={counts_after_auto}"
    assert auto_report["discovered"] == 6
    assert auto_report["converted"] == 5 and auto_report["failed"] == 1
    assert auto_report["resolved_class_counts"] == {"DOOR": 1, "SOFA": 1, "STAIR": 1, "TABLE": 1, "WINDOW": 1}
    assert auto_report["library_family_count"] == 6
    assert auto_report["library_index_error"] is None
    duplicate_paths = [
        assets / "tables" / "same_name.blend",
        assets / "tables" / "vendor_a" / "same_name.blend",
    ]
    duplicate_keys = addon.batch._build_output_keys(duplicate_paths, assets)
    assert len(set(key.as_posix() for key in duplicate_keys.values())) == 2

    report_path = output / "batch-report.json"
    review_path = output / "review-queue.json"
    index_path = output / "library-index.json"
    for path in (report_path, review_path, index_path):
        assert_file(path)
    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert report_data["failed"] == 1
    assert index["familyCount"] == 6
    assert index["classCounts"] == {"DOOR": 1, "SOFA": 2, "STAIR": 1, "TABLE": 1, "WINDOW": 1}
    ids = [entry["familyId"] for entry in index["families"]]
    assert len(ids) == len(set(ids))
    for entry in index["families"]:
        assert not Path(entry["manifest"]).is_absolute()
        manifest_path = output / entry["manifest"]
        assert_file(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        addon.schema.assert_valid_manifest(manifest)
        if entry.get("thumbnail"):
            assert not Path(entry["thumbnail"]).is_absolute()
            assert_file(output / entry["thumbnail"])
        for uri in entry.get("geometryVariants", {}).values():
            assert not Path(uri).is_absolute()
            assert_file(output / uri)
    results["batch"] = {
        "exact": exact_report,
        "auto": auto_report,
        "index": index,
        "datablockCounts": {
            "before": counts_before_exact,
            "afterExact": counts_after_exact,
            "afterAuto": counts_after_auto,
        },
    }


def test_batch_cleanup_and_transactions():
    output = ARTIFACTS / "batch_library"
    before = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images), len(bpy.data.cameras), len(bpy.data.lights))
    before_camera_names = sorted(data.name for data in bpy.data.cameras)
    before_light_names = sorted(data.name for data in bpy.data.lights)
    clean_scene()
    after_scene = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images), len(bpy.data.cameras), len(bpy.data.lights))
    assert after_scene[0] == 0
    assert sorted(data.name for data in bpy.data.cameras) == before_camera_names
    assert sorted(data.name for data in bpy.data.lights) == before_light_names
    assert not any(data.name.startswith("__BFC_Thumbnail") for data in bpy.data.cameras)
    assert not any(data.name.startswith("__BFC_Thumbnail") for data in bpy.data.lights)
    assert output.exists()

    clean_scene()
    root, _ = family_for("TABLE", "Failure_Table")
    bad_dir = ARTIFACTS / "invalid_export\0"
    try:
        addon.typed.export_typed_family(root, bad_dir, export_glb=True, export_thumbnail=False)
    except Exception:
        pass
    else:
        raise AssertionError("invalid export directory unexpectedly succeeded")
    assert not bad_dir.parent.joinpath("invalid_export").exists()

    core_types = addon.core.read_types(root)
    core_types["Broken"] = {"width": 0.0}
    addon.core.write_types(root, core_types)
    try:
        addon.typed.apply_typed_type(root, "Broken")
    except (KeyError, TypeError, ValueError):
        pass
    else:
        raise AssertionError("invalid saved type unexpectedly applied")

    clean_scene()
    source = make_asset("GENERIC")
    missing_root = addon.typed.create_typed_family(bpy.context, source, "Missing_Door_Roles", "DOOR")
    quality = addon.quality.validate_family(missing_root)
    assert not quality["ready"] and quality["missingRoleGroups"]

    clean_scene()
    root, _ = family_for("TABLE", "Generator_Failure_Table")
    set_dimensions(root, width=root.bfc_base_width * 1.2)
    addon.typed.save_typed_type(root, "Wide", overwrite=True)
    failure_dir = ARTIFACTS / "generator_failure_export"
    sentinel = ARTIFACTS / "unrelated_sentinel.txt"
    sentinel.write_text("keep me", encoding="utf-8")
    original_rebuild = addon.variants.rebuild_family_geometry

    def fail_rebuild(_root):
        raise RuntimeError("intentional generator failure")

    addon.variants.rebuild_family_geometry = fail_rebuild
    try:
        try:
            addon.typed.export_typed_family(
                root,
                failure_dir,
                export_glb=True,
                export_baked_types=True,
                export_thumbnail=False,
            )
        except RuntimeError as exc:
            assert "intentional generator failure" in str(exc)
        else:
            raise AssertionError("intentional generator failure unexpectedly exported")
    finally:
        addon.variants.rebuild_family_geometry = original_rebuild
    assert not list(failure_dir.glob("*")) if failure_dir.exists() else True
    assert sentinel.read_text(encoding="utf-8") == "keep me"

    clean_scene()
    root, _ = family_for("TABLE", "Thumbnail_Failure_Table")
    thumbnail_failure_dir = ARTIFACTS / "thumbnail_failure_export"
    original_thumbnail = addon.typed.render_family_thumbnail

    def fail_thumbnail(*_args, **_kwargs):
        raise RuntimeError("intentional thumbnail failure")

    addon.typed.render_family_thumbnail = fail_thumbnail
    try:
        manifest, _ = addon.typed.export_typed_family(
            root,
            thumbnail_failure_dir,
            export_glb=False,
            export_thumbnail=True,
        )
    finally:
        addon.typed.render_family_thumbnail = original_thumbnail
    thumbnail_data = json.loads(manifest.read_text(encoding="utf-8"))
    addon.schema.assert_valid_manifest(thumbnail_data)
    assert "thumbnail" not in thumbnail_data
    assert any("intentional thumbnail failure" in warning for warning in thumbnail_data.get("exportWarnings", []))


def test_runtime_proxy_and_schema():
    clean_scene()
    root, _ = family_for("TABLE", "Proxy_Table")
    addon.typed.save_typed_type(root, "Wide", overwrite=True)
    set_dimensions(root, width=root.bfc_base_width * 1.5)
    addon.typed.save_typed_type(root, "Wide", overwrite=True)
    proxy = addon.runtime_proxy.runtime_proxy_metadata(root)
    assert proxy["selection"]["size"][0] > 0 and proxy["collision"]["size"][2] > 0
    for type_name, bounds in proxy["typeBounds"].items():
        assert type_name in addon.core.read_types(root)
        assert all(value > 0 for value in bounds["size"])
    assert proxy["planFootprint"]["baseZ"] == proxy["selection"]["min"][2]
    manifest = addon.typed.export_typed_family(root, ARTIFACTS / "schema_export", export_glb=False, export_thumbnail=False)[0]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    addon.schema.assert_valid_manifest(data)
    assert data["familyKind"] == "TABLE" and data["runtimeProxy"]["typeBounds"]


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    # The harness owns this exact artifact directory. It never purges Blender
    # global orphans and never touches repository files outside artifacts.
    for child in list(ARTIFACTS.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    addon.register()
    results = {
        "blenderVersion": bpy.app.version_string,
        "pythonVersion": sys.version.split()[0],
        "executable": bpy.app.binary_path,
        "renderEngines": [item.identifier for item in bpy.context.scene.render.bl_rna.properties["engine"].enum_items],
        "passed": [],
        "failures": [],
    }

    tests = [
        ("registration", test_registration),
        ("operator_execution", test_operator_execution),
        ("sofa", test_sofa),
        ("table_chair_bed", test_table_chair_bed),
        ("casework", test_casework),
        ("additional_registered_classes", test_additional_registered_classes),
        ("door_window", test_door_window),
        ("stair_and_plumbing", test_stair_and_plumbing),
        ("hierarchy_and_preflight", test_hierarchy_and_preflight),
        ("modifier_aware_analysis", test_modifier_aware_analysis),
        ("auto_prepare", test_auto_prepare),
        ("export_variants_thumbnail_roundtrip", test_export_variants_thumbnail_and_roundtrip),
        ("batch_and_catalog", lambda: test_batch_and_catalog(results)),
        ("batch_cleanup_and_transactions", test_batch_cleanup_and_transactions),
        ("runtime_proxy_and_schema", test_runtime_proxy_and_schema),
    ]
    only = os.environ.get("BFC_RUNTIME_ONLY", "").strip()
    if only:
        tests = [item for item in tests if item[0] in {value.strip() for value in only.split(",")}]
    for name, function in tests:
        run_test(results, name, function)

    results["ok"] = not results["failures"]
    result_path = ARTIFACTS / "runtime-results.json"
    result_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"ok": results["ok"], "passed": len(results["passed"]), "failed": len(results["failures"]), "result": str(result_path)}, indent=2))
    if results["failures"]:
        raise RuntimeError(f"Blender runtime validation failed: {len(results['failures'])} test(s)")


if __name__ == "__main__":
    main()
