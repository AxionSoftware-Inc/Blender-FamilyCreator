import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty

from .core import FAMILY_FLAG, apply_family, family_root


def _dimension_update(self, context):
    if bool(self.get(FAMILY_FLAG, False)) and not bool(self.get("bfc_applying", False)):
        apply_family(self)


def _rule_update(self, context):
    root = family_root(self)
    if root:
        apply_family(root)


def register_properties():
    bpy.types.Object.bfc_family_name = StringProperty(name="Family Name", default="Family")
    bpy.types.Object.bfc_category = StringProperty(name="Category", default="Generic Model")
    bpy.types.Object.bfc_type_name = StringProperty(name="Type Name", default="Default")

    bpy.types.Object.bfc_width = FloatProperty(name="Width", subtype="DISTANCE", min=0.001, default=1.0, update=_dimension_update)
    bpy.types.Object.bfc_depth = FloatProperty(name="Depth", subtype="DISTANCE", min=0.001, default=1.0, update=_dimension_update)
    bpy.types.Object.bfc_height = FloatProperty(name="Height", subtype="DISTANCE", min=0.001, default=1.0, update=_dimension_update)
    bpy.types.Object.bfc_base_width = FloatProperty(name="Base Width", subtype="DISTANCE", min=0.001, default=1.0)
    bpy.types.Object.bfc_base_depth = FloatProperty(name="Base Depth", subtype="DISTANCE", min=0.001, default=1.0)
    bpy.types.Object.bfc_base_height = FloatProperty(name="Base Height", subtype="DISTANCE", min=0.001, default=1.0)

    rule_items = [
        ("STRETCH", "Stretch", "Scale this member on this family axis"),
        ("MOVE", "Move", "Keep size but move proportionally on this family axis"),
        ("FIXED", "Fixed", "Do not react to this family axis"),
    ]
    bpy.types.Object.bfc_rule_x = EnumProperty(name="X Rule", items=rule_items, default="FIXED", update=_rule_update)
    bpy.types.Object.bfc_rule_y = EnumProperty(name="Y Rule", items=rule_items, default="FIXED", update=_rule_update)
    bpy.types.Object.bfc_rule_z = EnumProperty(name="Z Rule", items=rule_items, default="FIXED", update=_rule_update)

    bpy.types.Scene.bfc_new_family_name = StringProperty(name="New Family", default="New Family")
    bpy.types.Scene.bfc_type_query = StringProperty(name="Type", default="Default")
    bpy.types.Scene.bfc_param_name = StringProperty(name="Parameter", default="Clearance")
    bpy.types.Scene.bfc_param_default = FloatProperty(name="Default", default=0.0)
    bpy.types.Scene.bfc_bind_param = StringProperty(name="Parameter Key", default="clearance")
    bpy.types.Scene.bfc_bind_data_path = StringProperty(name="RNA Data Path", default="scale")
    bpy.types.Scene.bfc_bind_index = IntProperty(name="Index", default=-1, min=-1, max=32)
    bpy.types.Scene.bfc_bind_expression = StringProperty(name="Expression", default="p")
    bpy.types.Scene.bfc_export_directory = StringProperty(name="Export Folder", subtype="DIR_PATH")
    bpy.types.Scene.bfc_export_glb = BoolProperty(name="Export GLB", default=True)


def unregister_properties():
    names = [
        "bfc_family_name", "bfc_category", "bfc_type_name",
        "bfc_width", "bfc_depth", "bfc_height",
        "bfc_base_width", "bfc_base_depth", "bfc_base_height",
        "bfc_rule_x", "bfc_rule_y", "bfc_rule_z",
    ]
    for name in names:
        if hasattr(bpy.types.Object, name):
            delattr(bpy.types.Object, name)

    scene_names = [
        "bfc_new_family_name", "bfc_type_query", "bfc_param_name", "bfc_param_default",
        "bfc_bind_param", "bfc_bind_data_path", "bfc_bind_index", "bfc_bind_expression",
        "bfc_export_directory", "bfc_export_glb",
    ]
    for name in scene_names:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
