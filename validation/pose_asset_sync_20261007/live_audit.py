"""Observe one actual Asset Browser application, then restore the hook."""
import json
from pathlib import Path

import bpy
from character_designer import control_pose_assets as poses

folder = Path(__file__).resolve().parent
target = folder / 'live_double_click.json'
if target.exists():
    raise RuntimeError('The click evidence already exists; inspect it before retrying.')
if hasattr(poses, '_pose_validation_apply'):
    raise RuntimeError('A previous validation hook is still active.')
poses._pose_validation_apply = poses.apply_channels

def make_observer(original, target):
    def observe(context, rig, values, *, metadata=None):
        auto_key = context.scene.tool_settings.use_keyframe_insert_auto
        result = {'rig': rig.name, 'metadata_present': metadata is not None,
                  'names': sorted(values), 'mode': context.mode, 'passed': False,
                  'verification_auto_key_suppressed': auto_key}
        try:
            # This same-pose GUI verification must preserve existing animation.
            context.scene.tool_settings.use_keyframe_insert_auto = False
            returned = original(context, rig, values, metadata=metadata)
            result.update(passed=True, result=returned)
            return returned
        except Exception as error:
            result.update(error=repr(error))
            raise
        finally:
            context.scene.tool_settings.use_keyframe_insert_auto = auto_key
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return observe

poses.apply_channels = make_observer(poses._pose_validation_apply, target)
print('POSE_CLICK_AUDIT_READY')
