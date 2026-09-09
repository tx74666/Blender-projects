"""Small Hair-page workflow for strand discovery and native bone control."""

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

from .hair_bones_topology import HairTopologyError, select_strands, selected_strands
from .hair_bones_rig import HairBonesRigError, build_hair_bones
from .ui_constants import SIDEBAR_CATEGORY, UI_PAGE_HAIR, active_ui_page


def _settings(context):
    return getattr(context.window_manager, "character_designer_hair_bones", None)


def _mesh_edit(context):
    obj = context.active_object
    return obj is not None and obj.type == "MESH" and context.mode == "EDIT_MESH"


def _report(operator, context, message, *, error=False):
    settings = _settings(context)
    if settings:
        settings.last_message = message
    operator.report({"ERROR" if error else "INFO"}, message)


class CharacterDesignerHairBonesState(PropertyGroup):
    bone_count: IntProperty(
        name="Bones per Strand",
        description="Number of connected bones used to bend each selected hair strand",
        default=4,
        min=1,
        max=12,
    )
    last_message: StringProperty(options={"SKIP_SAVE"})


class CHARACTERDESIGNER_OT_select_hair_strands(Operator):
    bl_idname = "character_designer.select_hair_strands"
    bl_label = "Select Hair Strands"
    bl_description = (
        "Find long hair strips up to their root junctions. Selected vertices limit "
        "the search; deselect all to search the visible mesh"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _mesh_edit(context)

    def execute(self, context):
        try:
            _obj, plans = select_strands(context)
        except (HairTopologyError, RuntimeError) as exc:
            _report(self, context, str(exc), error=True)
            return {"CANCELLED"}
        count = len(plans)
        _report(self, context, f"Selected {count} hair strand{'s' if count != 1 else ''}. Check the selection, then Generate Hair Bones.")
        return {"FINISHED"}


class CHARACTERDESIGNER_OT_generate_hair_bones(Operator):
    bl_idname = "character_designer.generate_hair_bones"
    bl_label = "Generate Hair Bones"
    bl_description = (
        "Create and bind a connected bone chain for each selected hair strand, "
        "then select the controls in Pose Mode"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _mesh_edit(context) and _settings(context) is not None

    def execute(self, context):
        try:
            obj, plans = selected_strands(context)
            result = build_hair_bones(
                context, obj, plans, bone_count=_settings(context).bone_count,
            )
        except (HairTopologyError, HairBonesRigError, RuntimeError) as exc:
            _report(self, context, str(exc), error=True)
            return {"CANCELLED"}
        count = len(result["chains"])
        action = "Created" if result["created"] else "Selected"
        _report(self, context, f"{action} {count} hair chain{'s' if count != 1 else ''}. Rotate the selected bones in Pose Mode.")
        return {"FINISHED"}


class CHARACTERDESIGNER_PT_hair_bones(Panel):
    bl_label = "Hair Bones"
    bl_idname = "CHARACTERDESIGNER_PT_hair_bones"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SIDEBAR_CATEGORY

    @classmethod
    def poll(cls, context):
        return active_ui_page(context) == UI_PAGE_HAIR

    def draw(self, context):
        layout = self.layout
        settings = _settings(context)
        if settings is None:
            return
        layout.prop(settings, "bone_count")
        layout.operator("character_designer.select_hair_strands", icon="RESTRICT_SELECT_OFF")
        layout.operator("character_designer.generate_hair_bones", icon="BONE_DATA")
        if _mesh_edit(context):
            layout.label(text="Select a tip to limit the search.", icon="INFO")
            layout.label(text="Deselect all to find visible strands.")
        elif context.mode == "POSE":
            layout.label(text="Rotate hair bones in Pose Mode.", icon="INFO")
            layout.label(text="Mesh Edit Mode to add more strands.")
        else:
            layout.label(text="Select hair in Mesh Edit Mode.", icon="INFO")


HAIR_BONES_CLASSES = (
    CharacterDesignerHairBonesState,
    CHARACTERDESIGNER_OT_select_hair_strands,
    CHARACTERDESIGNER_OT_generate_hair_bones,
    CHARACTERDESIGNER_PT_hair_bones,
)
