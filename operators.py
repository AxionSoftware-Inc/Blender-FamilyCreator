import bpy
from bpy.types import Operator

from .core import (
    add_custom_parameter,
    analyze_member,
    apply_family,
    apply_type,
    bind_parameter,
    create_family,
    delete_type,
    export_family,
    family_root,
    reset_family,
    save_type,
)


def active_root(context):
    return family_root(context.active_object) if context.active_object else None


class BFC_OT_create_family(Operator):
    bl_idname = "bfc.create_family"
    bl_label = "Create Family from Selection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            root = create_family(context, list(context.selected_objects), context.scene.bfc_new_family_name)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        context.view_layer.objects.active = root
        self.report({"INFO"}, f"Family '{root.bfc_family_name}' created")
        return {"FINISHED"}


class BFC_OT_smart_analyze(Operator):
    bl_idname = "bfc.smart_analyze"
    bl_label = "Smart Analyze Members"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            self.report({"ERROR"}, "Select a Family Creator family or one of its members")
            return {"CANCELLED"}
        for obj in root.children_recursive:
            if obj.type in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
                analyze_member(root, obj)
        apply_family(root)
        self.report({"INFO"}, "Stretch / Move / Fixed rules regenerated")
        return {"FINISHED"}


class BFC_OT_reset_family(Operator):
    bl_idname = "bfc.reset_family"
    bl_label = "Reset Dimensions"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        reset_family(root)
        return {"FINISHED"}


class BFC_OT_save_type(Operator):
    bl_idname = "bfc.save_type"
    bl_label = "Save / Update Type"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        name = context.scene.bfc_type_query.strip() or "Default"
        save_type(root, name, overwrite=True)
        self.report({"INFO"}, f"Type '{name}' saved")
        return {"FINISHED"}


class BFC_OT_apply_type(Operator):
    bl_idname = "bfc.apply_type"
    bl_label = "Apply Type"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        try:
            apply_type(root, context.scene.bfc_type_query.strip())
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class BFC_OT_delete_type(Operator):
    bl_idname = "bfc.delete_type"
    bl_label = "Delete Type"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        try:
            delete_type(root, context.scene.bfc_type_query.strip())
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class BFC_OT_add_parameter(Operator):
    bl_idname = "bfc.add_parameter"
    bl_label = "Add Custom Parameter"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        slug, _ = add_custom_parameter(root, context.scene.bfc_param_name, context.scene.bfc_param_default)
        context.scene.bfc_bind_param = slug
        self.report({"INFO"}, f"Parameter '{slug}' added")
        return {"FINISHED"}


class BFC_OT_bind_parameter(Operator):
    bl_idname = "bfc.bind_parameter"
    bl_label = "Bind Parameter to Active Object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        target = context.active_object
        if not root or not target or target == root:
            self.report({"ERROR"}, "Select a family member as the active object")
            return {"CANCELLED"}
        try:
            bind_parameter(
                root,
                context.scene.bfc_bind_param.strip(),
                target,
                context.scene.bfc_bind_data_path.strip(),
                context.scene.bfc_bind_index,
                context.scene.bfc_bind_expression.strip() or "p",
            )
        except Exception as exc:
            self.report({"ERROR"}, f"Could not create driver: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, "Driver binding created")
        return {"FINISHED"}


class BFC_OT_export_family(Operator):
    bl_idname = "bfc.export_family"
    bl_label = "Export Family Package"

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        directory = bpy.path.abspath(context.scene.bfc_export_directory)
        if not directory:
            self.report({"ERROR"}, "Choose an export folder")
            return {"CANCELLED"}
        try:
            manifest, glb = export_family(root, directory, context.scene.bfc_export_glb)
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {manifest.name}" + (f" + {glb.name}" if glb else ""))
        return {"FINISHED"}


CLASSES = (
    BFC_OT_create_family,
    BFC_OT_smart_analyze,
    BFC_OT_reset_family,
    BFC_OT_save_type,
    BFC_OT_apply_type,
    BFC_OT_delete_type,
    BFC_OT_add_parameter,
    BFC_OT_bind_parameter,
    BFC_OT_export_family,
)
