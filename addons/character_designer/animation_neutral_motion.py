"""Expose the project's editable Neutral Action beside the character's managed motions."""
from pathlib import Path
from types import SimpleNamespace

import bpy
from bpy.types import Operator

from . import animation_worklist_edit_scene as edit_scene


ROW = SimpleNamespace(name='Neutral', clip_key='local:neutral', work_item_id='local:neutral')
REST = 'character_designer_neutral_rest_v1'


def _template(rig):
    if not bpy.data.filepath:
        return None
    directory = Path(bpy.data.filepath).parent
    return directory / 'assets' / 'animations' / bpy.path.clean_name(rig.name) / 'Neutral.blend'


def available(scene):
    home = edit_scene.mapping_home(scene)
    rig = home.character_designer_setup.rig if home else None
    if not rig:
        return False
    if edit_scene.mapping_record(home, ROW) is not None:
        return True
    path = _template(rig)
    return bool(path and path.is_file())


def _load(rig):
    from .animation_controller_mapping import _digest
    from .control_pose_assets import native_rest
    path = _template(rig)
    if not path or not path.is_file():
        raise ValueError('The Neutral Action template is missing from this character project.')
    with bpy.data.libraries.load(str(path), link=False) as (source, loaded):
        if ROW.name not in source.actions:
            raise ValueError('The project template is missing its Neutral Action.')
        loaded.actions = [ROW.name]
    action, = loaded.actions
    try:
        if (not action or action.asset_data or len(action.slots) != 1
                or action.slots[0].target_id_type != 'OBJECT'
                or action.get(REST) != _digest(native_rest(rig))):
            raise ValueError('The Neutral Action template does not match this character rig.')
        return action
    except Exception:
        if action:
            bpy.data.actions.remove(action)
        raise


class CHARACTERDESIGNER_OT_open_neutral_motion(Operator):
    bl_idname = 'character_designer.open_neutral_motion'
    bl_label = 'Open Neutral'
    bl_description = 'Edit the character’s local Neutral Action'
    bl_options = {'UNDO'}

    def execute(self, context):
        from . import animation_controller_edit as edit, animation_pose_test as pose_test
        from . import animation_preview_session as preview, body_original_mode
        from .animation_worklist import _idle
        home = edit_scene.mapping_home(context.scene)
        if not home or not context.window:
            return {'CANCELLED'}
        created = None
        action = None
        try:
            rig = edit._target(home, home.character_designer_setup.rig)
            _idle(context)
            if preview.SESSION in rig:
                raise ValueError('Apply or discard the key reduction preview before switching motions.')
            if pose_test.active(rig) or rig.data.pose_position == 'REST':
                raise ValueError('Return to Animation before opening Neutral.')
            if body_original_mode.SESSION in rig:
                raise ValueError('Return to Controls before opening Neutral.')
            if edit.pending(home):
                raise ValueError('Finish preparing the character motion before opening Neutral.')
            record = edit._record(home, ROW, create=False)
            if record is None:
                action = _load(rig)
                created = record = edit._record(home, ROW)
                record.controller_action = action
                record.controller_slot = action.slots[0].handle
                record.state = 'READY'
            if not record.controller_action:
                raise ValueError('The local Neutral Action is missing from its saved motion.')
            result = edit._activate(context, home, record)
            settings = home.character_designer_animation_worklist
            settings.catalog_index = -1
            settings.selected_motion_clip = ''
            if result['state'] == 'CONTROLLER_RECOVERY':
                self.report({'WARNING'}, result['message'])
        except (ValueError, TypeError, RuntimeError, OSError) as exc:
            if action and not (rig.animation_data and rig.animation_data.action == action):
                if created is not None:
                    records = home.character_designer_controller_motions
                    records.remove(next(i for i, entry in enumerate(records) if entry == created))
                bpy.data.actions.remove(action)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


def draw(layout, context):
    from . import animation_worklist_categories as categories
    if (not available(context.scene)
            or categories.category_for(context.scene, ROW) != categories.current_category(context.scene)):
        return False
    home = edit_scene.mapping_home(context.scene)
    record = edit_scene.mapping_record(home, ROW)
    ad = home.character_designer_setup.rig.animation_data
    selected = bool(ad and record and ad.action and ad.action == record.controller_action
                    and ad.action_slot_handle == record.controller_slot)
    edit, status, manage = edit_scene.motion_row(layout)
    edit.enabled = context.mode in {'OBJECT', 'POSE'}
    edit.operator('character_designer.open_neutral_motion', text=ROW.name, icon='ACTION',
                  emboss=False, depress=selected)
    status.label(text='Ready', icon='CHECKMARK')
    categories.draw_move(manage, context, ROW)
    return True
