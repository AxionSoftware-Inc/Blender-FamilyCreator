import bpy
from bpy.types import Panel

from .core import (
    GENERATED_FLAG,
    TEMPLATE_FLAG,
    family_members,
    family_root,
    read_custom_parameters,
    read_types,
)
from .family_types import get_family_type
from .family_types.parameter_specs import get_parameter_specs, property_name
from .generators import supports_generation
from .hosting import hosting_metadata
from .quality import validate_family
from .typed import ensure_semantic_parameters


def _pretty_parameter(name):
    return (name or "").replace("_", " ").title()


def _draw_prepare(layout, scene):
    box = layout.box()
    box.label(text="Auto Prepare", icon="MESH_DATA")
    box.label(text="Split manageable disconnected mesh islands before semantic analysis.")
    row = box.row(align=True)
    row.prop(scene, "bfc_prepare_max_islands")
    row.operator("bfc.prepare_selection", icon="MOD_EXPLODE")
    box.label(text="Shape-key, armature and very fragmented meshes are left untouched.")
    if scene.bfc_prepare_last_result:
        box.label(text=scene.bfc_prepare_last_result, icon="INFO")


def _draw_batch_factory(layout, scene):
    batch = layout.box()
    batch.label(text="Batch Family Factory", icon="FILE_FOLDER")
    batch.label(text="Convert a whole model folder using one exact Family Class.")
    batch.prop(scene, "bfc_batch_input_directory")
    batch.prop(scene, "bfc_batch_output_directory")
    batch.prop(scene, "bfc_batch_family_kind")

    spec = get_family_type(scene.bfc_batch_family_kind)
    batch.label(text=spec["description"])

    row = batch.row(align=True)
    row.prop(scene, "bfc_batch_recursive")
    row.prop(scene, "bfc_batch_export_glb")
    batch.prop(scene, "bfc_batch_auto_split_loose")
    if scene.bfc_batch_auto_split_loose:
        batch.prop(scene, "bfc_prepare_max_islands")
    batch.prop(scene, "bfc_batch_continue_on_error")
    batch.operator("bfc.batch_convert", icon="EXPORT")
    batch.label(text="Supports .blend, .fbx, .glb, .gltf and .obj")
    if scene.bfc_batch_last_result:
        batch.label(text=scene.bfc_batch_last_result, icon="INFO")


def _draw_quality(layout, root):
    quality = validate_family(root)
    box = layout.box()

    if quality.get("automaticReady"):
        icon = "CHECKMARK"
        status = "Automatic library ready"
    elif quality.get("ready"):
        icon = "INFO"
        status = "Semantically valid — review recommended"
    else:
        icon = "ERROR"
        status = "Not ready — semantic fixes required"

    box.label(text=f"Family Quality — {quality['score']}/100", icon=icon)
    box.label(text=status)
    box.label(text=f"Semantic role coverage: {quality['roleCoverage']:.0%}")

    preflight = quality.get("preflight", {})
    stats = preflight.get("stats", {})
    polygons = int(stats.get("meshPolygons", 0) or 0)
    if polygons:
        box.label(text=f"Source mesh polygons: {polygons:,}")

    for warning in quality.get("warnings", ()):
        box.label(text=warning, icon="INFO")
    for error in quality.get("errors", ()):
        box.label(text=error, icon="ERROR")


def _draw_hosting(layout, root):
    data = hosting_metadata(root)
    if data is None:
        return

    box = layout.box()
    box.label(text="BIM Hosting / Placement", icon="HOME")
    box.label(text=f"Host: {data['hostType']}  |  Cut: {data['opening']['shape']}")
    box.label(text=f"Insertion: {data['insertionPoint']}")
    box.label(text="Facing: +Y  |  Up: +Z")
    opening = data["opening"]
    box.label(
        text=(
            f"Opening: {opening['width']:.3f} × {opening['height']:.3f} × "
            f"{opening['depth']:.3f} m"
        )
    )
    if root.bfc_family_kind == "WINDOW":
        box.label(text=f"Sill elevation: {data['elevationFromLevel']:.3f} m")

    plan = data.get("planRepresentation")
    if plan and root.bfc_family_kind == "DOOR":
        box.label(text=f"Plan swing hinge: {plan.get('hingeSide', 'UNKNOWN')}")

    flags = []
    if data.get("canFlipFacing"):
        flags.append("Facing flip")
    if data.get("canFlipHand"):
        flags.append("Hand flip")
    if flags:
        box.label(text="Runtime: " + ", ".join(flags))


def _draw_generator(layout, root):
    box = layout.box()
    box.label(text="Procedural Geometry", icon="MOD_ARRAY")
    supported = supports_generation(root.bfc_family_kind)
    if not supported:
        box.label(text="No class-specific generator yet; semantic scaling only.")
        return

    members = family_members(root)
    template_count = sum(1 for obj in members if bool(obj.get(TEMPLATE_FLAG, False)))
    generated_count = sum(1 for obj in members if bool(obj.get(GENERATED_FLAG, False)))
    revision = int(root.get("bfc_generator_revision", 0))

    box.label(text=f"Generator: {root.bfc_family_kind}  |  Revision: {revision}")
    box.label(text=f"Templates: {template_count}  |  Generated: {generated_count}")
    box.operator("bfc.rebuild_procedural_geometry", icon="FILE_REFRESH")
    last_error = root.get("bfc_generator_last_error", "")
    if last_error:
        box.label(text=f"Last rebuild warning: {last_error}", icon="ERROR")
    else:
        box.label(text="Dimensions rebuild supported class geometry automatically.")
    box.label(text="Applying a saved Type rebuilds supported classes automatically.")


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
            box.label(text="Select all parts of one asset first.")
            _draw_prepare(layout, scene)
            box.operator("bfc.create_family", icon="ADD")
            _draw_batch_factory(layout, scene)
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

        _draw_quality(layout, root)
        _draw_hosting(layout, root)

        editable = set(spec.get("editable_axes", ()))
        axis_parameters = spec.get("axis_parameters", {})
        axis_anchors = spec.get("axis_anchors", {})
        dims = layout.box()
        dims.label(text="Class Dimensions", icon="ARROW_LEFTRIGHT")
        row = dims.row()
        row.enabled = "X" in editable
        row.prop(root, "bfc_width", text=_pretty_parameter(axis_parameters.get("X", "width")))
        row.label(text=f"Anchor: {axis_anchors.get('X', 'CENTER')}")
        row = dims.row()
        row.enabled = "Y" in editable
        row.prop(root, "bfc_depth", text=_pretty_parameter(axis_parameters.get("Y", "depth")))
        row.label(text=f"Anchor: {axis_anchors.get('Y', 'CENTER')}")
        row = dims.row()
        row.enabled = "Z" in editable
        row.prop(root, "bfc_height", text=_pretty_parameter(axis_parameters.get("Z", "height")))
        row.label(text=f"Anchor: {axis_anchors.get('Z', 'CENTER')}")
        dims.label(text="Enabled axes: " + (", ".join(sorted(editable)) if editable else "fixed proportions"))
        row = dims.row(align=True)
        row.operator("bfc.reset_family", icon="LOOP_BACK")
        row.operator("bfc.smart_analyze", icon="MODIFIER")

        params_info = layout.box()
        params_info.label(text="Semantic Class Parameters", icon="PROPERTIES")
        ensure_semantic_parameters(root, root.bfc_family_kind)
        parameter_specs = get_parameter_specs(root.bfc_family_kind)
        if parameter_specs:
            for parameter, parameter_spec in parameter_specs.items():
                prop = property_name(parameter)
                row = params_info.row()
                row.prop(root, f'["{prop}"]', text=_pretty_parameter(parameter))
                if parameter_spec.get("type") == "LENGTH":
                    row.label(text="length")
                elif parameter_spec.get("type") == "INT":
                    row.label(text="count")
        else:
            params_info.label(text="No extra semantic parameters for this class.")

        if root.bfc_family_kind == "STAIR":
            params_info.operator("bfc.solve_stair_parameters", icon="MOD_ARRAY")
            params_info.label(text="0 step/riser/tread values are treated as Auto.")

        _draw_generator(layout, root)

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
            rules.label(text=f"Member — {active.name}", icon="OBJECT_DATA")
            rules.prop(active, "bfc_member_role", text="Semantic Role")
            row = rules.row(align=True)
            row.prop(active, "bfc_rule_x", text="X")
            row.prop(active, "bfc_rule_y", text="Y")
            row.prop(active, "bfc_rule_z", text="Z")
            if bool(active.get(TEMPLATE_FLAG, False)):
                rules.label(text="Generator template (excluded from export)")
            elif bool(active.get(GENERATED_FLAG, False)):
                rules.label(text="Generated instance")
            rules.label(text="Analyze assigns role + rules from the family class.")
            rules.label(text="Role/rules can be corrected manually when needed.")

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

        _draw_batch_factory(layout, scene)


CLASSES = (BFC_PT_main,)
