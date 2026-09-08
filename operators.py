import bpy
from bpy.types import Operator

from .core import (
    add_custom_parameter,
    apply_family,
    bind_parameter,
    delete_type,
    family_root,
    reset_family,
)
from .family_types.parameter_specs import property_name
from .family_types.stair import solve_parameters as solve_stair_parameters
from .typed import (
    apply_family_kind,
    apply_semantic_parameter_values,
    apply_typed_type,
    capture_typed_family,
    create_typed_family,
    ensure_semantic_parameters,
    export_typed_family,
    save_typed_type,
)


def active_root(context):
    return family_root(context.active_object) if context.active_object else None


class BFC_OT_create_family(Operator):
    bl_idname = "bfc.create_family"
    bl_label = "Create Typed Family from Selection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            root = create_typed_family(
                context,
                list(context.selected_objects),
                context.scene.bfc_new_family_name,
                context.scene.bfc_new_family_kind,
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        bpy.ops.object.select_all(action="DESELECT")
        root.select_set(True)
        context.view_layer.objects.active = root
        self.report({"INFO"}, f"{root.bfc_family_kind} family '{root.bfc_family_name}' created")
        return {"FINISHED"}


class BFC_OT_apply_family_class(Operator):
    bl_idname = "bfc.apply_family_class"
    bl_label = "Apply Family Class Logic"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            self.report({"ERROR"}, "Select a family or one of its members")
            return {"CANCELLED"}
        spec = apply_family_kind(root, root.bfc_family_kind, recapture=True)
        self.report({"INFO"}, f"Applied {spec['label']} logic")
        return {"FINISHED"}


class BFC_OT_smart_analyze(Operator):
    bl_idname = "bfc.smart_analyze"
    bl_label = "Analyze by Family Class"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            self.report({"ERROR"}, "Select a Family Creator family or one of its members")
            return {"CANCELLED"}

        current = (root.bfc_width, root.bfc_depth, root.bfc_height)
        reset_family(root)
        capture_typed_family(root)
        root["bfc_applying"] = True
        try:
            root.bfc_width, root.bfc_depth, root.bfc_height = current
        finally:
            root["bfc_applying"] = False
        apply_family(root)
        self.report({"INFO"}, f"Rules regenerated using {root.bfc_family_kind} logic")
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
        save_typed_type(root, name, overwrite=True)
        self.report({"INFO"}, f"Type '{name}' saved with semantic parameters")
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
            apply_typed_type(root, context.scene.bfc_type_query.strip())
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


class BFC_OT_solve_stair_parameters(Operator):
    bl_idname = "bfc.solve_stair_parameters"
    bl_label = "Solve Stair Parameters"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root or root.bfc_family_kind != "STAIR":
            self.report({"ERROR"}, "Select a Stair family")
            return {"CANCELLED"}

        ensure_semantic_parameters(root, "STAIR")

        def value(name):
            return root.get(property_name(name), 0)

        step_count = int(value("step_count"))
        tread_depth = float(value("tread_depth"))
        riser_height = float(value("riser_height"))
        total_run = float(value("total_run"))
        total_rise = float(value("total_rise"))

        try:
            solved = solve_stair_parameters(
                step_count=step_count if step_count > 0 else None,
                tread_depth=tread_depth if tread_depth > 0 else None,
                riser_height=riser_height if step_count > 0 and riser_height > 0 else None,
                total_run=total_run if total_run > 0 else None,
                total_rise=total_rise if total_rise > 0 else None,
                target_riser_height=riser_height if riser_height > 0 else 0.175,
            )
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        apply_semantic_parameter_values(root, solved, "STAIR")
        self.report(
            {"INFO"},
            f"Stair solved: {solved['step_count']} steps, "
            f"run {solved['total_run']:.3f}, rise {solved['total_rise']:.3f}",
        )
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
            manifest, glb = export_typed_family(root, directory, context.scene.bfc_export_glb)
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {manifest.name}" + (f" + {glb.name}" if glb else ""))
        return {"FINISHED"}


CLASSES = (
    BFC_OT_create_family,
    BFC_OT_apply_family_class,
    BFC_OT_smart_analyze,
    BFC_OT_reset_family,
    BFC_OT_save_type,
    BFC_OT_apply_type,
    BFC_OT_delete_type,
    BFC_OT_solve_stair_parameters,
    BFC_OT_add_parameter,
    BFC_OT_bind_parameter,
    BFC_OT_export_family,
)
