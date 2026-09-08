import bpy
from bpy.types import Panel

from .core import family_root, read_custom_parameters, read_types
from .family_types import get_family_type


def _pretty_parameter(name):
    return (name or "").replace("_", " ").title()


class BFC_PT_main(Panel):
    bl_label = "Family Creator"
    bl_idname = "BFC_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Family"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        active = context.active_object
        root = family_root(active) if active else None

        if not root:
            box = layout.box()
            box.label(text="Create a typed BIM family", icon="OUTLINER_OB_GROUP_INSTANCE")
            box.prop(scene, "bfc_new_family_name")
            box.prop(scene, "bfc_new_family_kind")
            spec = get_family_type(scene.bfc_new_family_kind)
            box.label(text=spec["description"])
            box.label(text="Parameters: " + ", ".join(spec["parameters"][:5]))
            box.operator("bfc.create_family", icon="ADD")
            box.label(text="Select all parts of one asset first.")
            return

        header = layout.box()
        header.prop(root, "bfc_family_name")
        header.prop(root, "bfc_family_kind")
        spec = get_family_type(root.bfc_family_kind)
        header.label(text=f"Group: {spec['group']}  |  Category: {spec['category']}")
        header.label(text=f"Logic: {spec['logic_module'].split('.')[-1]}.py")
        header.label(text=spec["description"])
        header.operator("bfc.apply_family_class", icon="FILE_REFRESH")
        header.label(text="Change class, then Apply Family Class Logic.")

        editable = set(spec.get("editable_axes", ()))
        axis_parameters = spec.get("axis_parameters", {})
        dims = layout.box()
        dims.label(text="Class Dimensions", icon="ARROW_LEFTRIGHT")
        row = dims.row()
        row.enabled = "X" in editable
        row.prop(root, "bfc_width", text=_pretty_parameter(axis_parameters.get("X", "width")))
        row = dims.row()
        row.enabled = "Y" in editable
        row.prop(root, "bfc_depth", text=_pretty_parameter(axis_parameters.get("Y", "depth")))
        row = dims.row()
        row.enabled = "Z" in editable
        row.prop(root, "bfc_height", text=_pretty_parameter(axis_parameters.get("Z", "height")))
        dims.label(text="Enabled axes: " + (", ".join(sorted(editable)) if editable else "fixed proportions"))
        row = dims.row(align=True)
        row.operator("bfc.reset_family", icon="LOOP_BACK")
        row.operator("bfc.smart_analyze", icon="MODIFIER")

        params_info = layout.box()
        params_info.label(text="Semantic Class Parameters", icon="PROPERTIES")
        params_info.label(text="Contract for class-specific geometry modules:")
        for parameter in spec.get("parameters", ()):
            params_info.label(text=_pretty_parameter(parameter))

        types_box = layout.box()
        types_box.label(text="Size / Variant Types", icon="PRESET")
        types_box.prop(scene, "bfc_type_query")
        row = types_box.row(align=True)
        row.operator("bfc.save_type", icon="FILE_TICK")
        row.operator("bfc.apply_type", icon="CHECKMARK")
        row.operator("bfc.delete_type", icon="TRASH")
        type_names = list(read_types(root).keys())
        if type_names:
            types_box.label(text="Saved: " + ", ".join(type_names[:5]) + ("…" if len(type_names) > 5 else ""))

        if active and active != root and bool(active.get("bfc_is_member", False)):
            rules = layout.box()
            rules.label(text=f"Member Rules — {active.name}", icon="OBJECT_DATA")
            row = rules.row(align=True)
            row.prop(active, "bfc_rule_x", text="X")
            row.prop(active, "bfc_rule_y", text="Y")
            row.prop(active, "bfc_rule_z", text="Z")
            rules.label(text="Auto rules come from the selected family class.")
            rules.label(text="Manual overrides remain possible per object.")

        params = layout.box()
        params.label(text="Advanced Custom Parameters", icon="DRIVER")
        row = params.row(align=True)
        row.prop(scene, "bfc_param_name", text="Name")
        row.prop(scene, "bfc_param_default", text="Default")
        params.operator("bfc.add_parameter", icon="ADD")
        custom = read_custom_parameters(root)
        for slug, meta in list(custom.items())[:6]:
            prop_name = meta.get("property")
            if prop_name in root:
                params.prop(root, f'["{prop_name}"]', text=meta.get("name", slug))

        bind = layout.box()
        bind.label(text="Advanced Driver Binding", icon="LINKED")
        bind.prop(scene, "bfc_bind_param")
        bind.prop(scene, "bfc_bind_data_path")
        row = bind.row(align=True)
        row.prop(scene, "bfc_bind_index")
        row.prop(scene, "bfc_bind_expression")
        bind.operator("bfc.bind_parameter", icon="DRIVER")
        bind.label(text="Active object must be a family member.")

        export_box = layout.box()
        export_box.label(text="Mobile BIM Export", icon="EXPORT")
        export_box.prop(scene, "bfc_export_directory")
        export_box.prop(scene, "bfc_export_glb")
        export_box.operator("bfc.export_family", icon="EXPORT")


CLASSES = (BFC_PT_main,)
