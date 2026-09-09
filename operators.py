import bpy
from bpy.types import Operator

from .batch import batch_convert_directory
from .core import (
    add_custom_parameter,
    apply_family,
    bind_parameter,
    delete_type,
    family_root,
)
from .family_types.parameter_specs import property_name
from .family_types.stair import solve_parameters as solve_stair_parameters
from .generators import rebuild_family_geometry, supports_generation
from .prepare import auto_prepare_objects
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


def _set_dimensions_without_callbacks(root, width, depth, height):
    root["bfc_applying"] = True
    try:
        root.bfc_width = float(width)
        root.bfc_depth = float(depth)
        root.bfc_height = float(height)
    finally:
        root["bfc_applying"] = False


def _reset_dimensions_once(root, rebuild=True):
    _set_dimensions_without_callbacks(
        root,
        root.bfc_base_width,
        root.bfc_base_depth,
        root.bfc_base_height,
    )
    apply_family(root)
    if rebuild and supports_generation(root.bfc_family_kind):
        return rebuild_family_geometry(root)
    return None


class BFC_OT_prepare_selection(Operator):
    bl_idname = "bfc.prepare_selection"
    bl_label = "Prepare Selection"
    bl_description = "Conservatively split disconnected mesh islands before creating a family"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected = list(context.selected_objects)
        if not selected:
            self.report({"ERROR"}, "Select one or more asset objects")
            return {"CANCELLED"}

        try:
            result = auto_prepare_objects(
                context,
                selected,
                max_islands=context.scene.bfc_prepare_max_islands,
            )
        except Exception as exc:
            context.scene.bfc_prepare_last_result = f"Prepare failed: {exc}"
            self.report({"ERROR"}, context.scene.bfc_prepare_last_result)
            return {"CANCELLED"}

        bpy.ops.object.select_all(action="DESELECT")
        for obj in result["objects"]:
            if obj and obj.name in bpy.data.objects:
                obj.select_set(True)
        if result["objects"]:
            context.view_layer.objects.active = result["objects"][0]

        context.scene.bfc_prepare_last_result = (
            f"{result['split_objects']} object(s) split -> {result['output_objects']} prepared object(s)"
        )
        self.report({"INFO"}, context.scene.bfc_prepare_last_result)
        return {"FINISHED"}


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

        # Analyze from the immutable base envelope without running the class
        # generator three times through property update callbacks.
        _reset_dimensions_once(root, rebuild=False)
        capture_typed_family(root)
        _set_dimensions_without_callbacks(root, *current)
        apply_family(root)

        generator_result = None
        if supports_generation(root.bfc_family_kind):
            generator_result = rebuild_family_geometry(root)

        message = f"Rules regenerated using {root.bfc_family_kind} logic"
        if generator_result and generator_result.get("message"):
            message += f"; {generator_result['message']}"
        self.report({"INFO"}, message)
        return {"FINISHED"}


class BFC_OT_reset_family(Operator):
    bl_idname = "bfc.reset_family"
    bl_label = "Reset Dimensions"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            return {"CANCELLED"}
        result = _reset_dimensions_once(root, rebuild=True)
        if result and result.get("message"):
            self.report({"INFO"}, f"Base dimensions restored; {result['message']}")
        else:
            self.report({"INFO"}, "Base dimensions restored")
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


class BFC_OT_rebuild_procedural_geometry(Operator):
    bl_idname = "bfc.rebuild_procedural_geometry"
    bl_label = "Rebuild Procedural Geometry"
    bl_description = "Regenerate class-specific repeated geometry from semantic parameters"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        root = active_root(context)
        if not root:
            self.report({"ERROR"}, "Select a family or one of its members")
            return {"CANCELLED"}
        if not supports_generation(root.bfc_family_kind):
            self.report({"WARNING"}, f"No procedural generator yet for {root.bfc_family_kind}")
            return {"CANCELLED"}

        try:
            result = rebuild_family_geometry(root)
        except Exception as exc:
            self.report({"ERROR"}, f"Procedural rebuild failed: {exc}")
            return {"CANCELLED"}

        if result.get("changed"):
            self.report({"INFO"}, result.get("message", "Procedural geometry rebuilt"))
            return {"FINISHED"}

        self.report({"WARNING"}, result.get("message", "Nothing was generated"))
        return {"CANCELLED"}


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
        result = rebuild_family_geometry(root)
        if not result.get("changed"):
            self.report({"WARNING"}, result.get("message", "Parameters solved, geometry not rebuilt"))
            return {"FINISHED"}

        self.report(
            {"INFO"},
            f"Stair solved and rebuilt: {solved['step_count']} steps, "
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


class BFC_OT_batch_convert(Operator):
    bl_idname = "bfc.batch_convert"
    bl_label = "Build Family Library"
    bl_description = "Convert every supported model in the selected folder using one exact Family Class"

    def execute(self, context):
        scene = context.scene
        raw_input = scene.bfc_batch_input_directory.strip()
        raw_output = scene.bfc_batch_output_directory.strip()
        if not raw_input or not raw_output:
            self.report({"ERROR"}, "Choose both Asset Folder and Library Output")
            return {"CANCELLED"}

        input_directory = bpy.path.abspath(raw_input)
        output_directory = bpy.path.abspath(raw_output)
        try:
            report = batch_convert_directory(
                context,
                input_directory,
                output_directory,
                scene.bfc_batch_family_kind,
                recursive=scene.bfc_batch_recursive,
                export_glb=scene.bfc_batch_export_glb,
                continue_on_error=scene.bfc_batch_continue_on_error,
                auto_split_loose=scene.bfc_batch_auto_split_loose,
                max_loose_islands=scene.bfc_prepare_max_islands,
            )
        except Exception as exc:
            scene.bfc_batch_last_result = f"Batch failed: {exc}"
            self.report({"ERROR"}, scene.bfc_batch_last_result)
            return {"CANCELLED"}

        scene.bfc_batch_last_result = (
            f"{report['ready']} ready / {report['needs_review']} review / "
            f"{report['failed']} failed / {report['discovered']} discovered"
        )
        message_type = {"WARNING"} if report["failed"] or report["needs_review"] else {"INFO"}
        self.report(message_type, scene.bfc_batch_last_result)
        return {"FINISHED"}


CLASSES = (
    BFC_OT_prepare_selection,
    BFC_OT_create_family,
    BFC_OT_apply_family_class,
    BFC_OT_smart_analyze,
    BFC_OT_reset_family,
    BFC_OT_save_type,
    BFC_OT_apply_type,
    BFC_OT_delete_type,
    BFC_OT_rebuild_procedural_geometry,
    BFC_OT_solve_stair_parameters,
    BFC_OT_add_parameter,
    BFC_OT_bind_parameter,
    BFC_OT_export_family,
    BFC_OT_batch_convert,
)
