"""Blender runtime regression for transform and source-isolation safety.

Checks:
- rotated Family stretching does not introduce matrix shear;
- canonical rotation is preserved;
- repeated apply is idempotent;
- 90-degree axis mapping is correct;
- canonical source shear is detected by Preflight;
- multiple separated asset clusters are routed to review.

Run from repository root with Blender 5.2:

blender --background --factory-startup --python tests/blender_runtime/run_transform_safety.py
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_NAME = "bfc_transform_safety"


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


def clean_scene():
    if bpy.context.mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def root_local_matrix(root, obj):
    return root.matrix_world.inverted_safe() @ obj.matrix_world


def column(matrix3, index):
    return Vector((matrix3[0][index], matrix3[1][index], matrix3[2][index]))


def assert_no_shear(matrix, tolerance=1e-6):
    matrix3 = matrix.to_3x3()
    axes = [column(matrix3, index) for index in range(3)]
    for axis in axes:
        assert_true(axis.length > 1e-9, "Degenerate transform axis")
        axis.normalize()
    for left, right in ((0, 1), (0, 2), (1, 2)):
        dot = abs(float(axes[left].dot(axes[right])))
        assert_true(dot <= tolerance, f"Transform contains shear: normalized dot={dot}")


def matrix_close(left, right, tolerance=1e-6):
    return all(
        abs(float(left[row][col]) - float(right[row][col])) <= tolerance
        for row in range(4)
        for col in range(4)
    )


def test_rotated_stretch(addon):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.6, -0.15, 0.8))
    member = bpy.context.object
    member.name = "AngledMember"
    member.rotation_euler = (math.radians(11.0), math.radians(-17.0), math.radians(37.0))
    member.scale = (1.4, 0.55, 1.15)
    bpy.context.view_layer.update()

    root = addon.core.create_family(bpy.context, [member], name="Transform Safety")
    root.bfc_family_kind = "GENERIC"

    member.bfc_rule_x = "STRETCH"
    member.bfc_rule_y = "MOVE"
    member.bfc_rule_z = "FIXED"

    base = root_local_matrix(root, member).copy()
    base_rotation = base.to_quaternion()
    base_scale = base.to_scale()

    root["bfc_applying"] = True
    try:
        root.bfc_width = root.bfc_base_width * 1.8
        root.bfc_depth = root.bfc_base_depth * 1.25
    finally:
        root["bfc_applying"] = False
    addon.core.apply_family(root)
    bpy.context.view_layer.update()

    transformed = root_local_matrix(root, member).copy()
    assert_no_shear(transformed)

    transformed_rotation = transformed.to_quaternion()
    rotation_delta = base_rotation.rotation_difference(transformed_rotation).angle
    assert_true(rotation_delta <= 1e-5, f"Canonical rotation drifted by {rotation_delta} rad")

    transformed_scale = transformed.to_scale()
    changed_axes = sum(
        1 for index in range(3)
        if abs(abs(float(transformed_scale[index])) - abs(float(base_scale[index]))) > 1e-5
    )
    assert_true(changed_axes == 1, f"Expected exactly one local scale axis to change, got {changed_axes}")

    first_apply = transformed.copy()
    addon.core.apply_family(root)
    bpy.context.view_layer.update()
    second_apply = root_local_matrix(root, member)
    assert_true(matrix_close(first_apply, second_apply), "Repeated apply_family accumulated transform drift")

    rotation_90 = Matrix.Rotation(math.radians(90.0), 3, "Z")
    mapping = addon.core._best_local_to_family_axis_map(rotation_90)
    assert_true(mapping[0] == 1, f"Expected local X -> family Y, got {mapping}")
    assert_true(mapping[1] == 0, f"Expected local Y -> family X, got {mapping}")
    assert_true(mapping[2] == 2, f"Expected local Z -> family Z, got {mapping}")

    root["bfc_applying"] = True
    try:
        root.bfc_width = root.bfc_base_width
        root.bfc_depth = root.bfc_base_depth
        root.bfc_height = root.bfc_base_height
    finally:
        root["bfc_applying"] = False
    addon.core.apply_family(root)
    bpy.context.view_layer.update()
    restored = root_local_matrix(root, member)
    assert_true(matrix_close(base, restored), "Base dimensions did not restore canonical matrix exactly")


def test_preflight_shear(addon):
    clean_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    member = bpy.context.object
    member.name = "ShearedSource"

    shear = Matrix.Identity(4)
    shear[0][1] = 0.35
    member.matrix_world = shear
    bpy.context.view_layer.update()

    root = addon.core.create_family(bpy.context, [member], name="Shear Detection")
    root.bfc_family_kind = "GENERIC"
    preflight = addon.preflight.inspect_family(root)
    count = int(preflight.get("stats", {}).get("shearedTransformMembers", 0) or 0)
    assert_true(count == 1, f"Expected one sheared source member, got {count}")
    assert_true(preflight.get("reviewRecommended") is True, "Sheared source was not routed to review")


def test_spatial_multi_asset_review(addon):
    clean_scene()
    members = []
    for x in (-4.0, 4.0):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0.0, 0.5))
        members.append(bpy.context.object)
    members[0].name = "Asset_A"
    members[1].name = "Asset_B"
    bpy.context.view_layer.update()

    root = addon.core.create_family(bpy.context, members, name="Two Separate Assets")
    root.bfc_family_kind = "GENERIC"
    preflight = addon.preflight.inspect_family(root)
    stats = preflight.get("stats", {})
    assert_true(stats.get("spatialComponentCount") == 2, f"Expected two spatial clusters, got {stats}")
    assert_true(
        float(stats.get("largestSpatialComponentVolumeShare", 1.0)) < 0.75,
        f"Unexpected largest spatial share: {stats}",
    )
    assert_true(preflight.get("reviewRecommended") is True, "Multi-asset source was not routed to review")
    text = "\n".join(preflight.get("warnings", []))
    assert_true("separated spatial clusters" in text, "Spatial-cluster review warning missing")


def main():
    addon = load_addon()
    addon.register()
    try:
        clean_scene()
        test_rotated_stretch(addon)
        test_preflight_shear(addon)
        test_spatial_multi_asset_review(addon)
        print("TRANSFORM_SAFETY: PASS")
    finally:
        try:
            addon.unregister()
        finally:
            clean_scene()


if __name__ == "__main__":
    main()
