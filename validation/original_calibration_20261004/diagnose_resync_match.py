"""Isolated diagnostic of ordinary IK match precision; never saves a scene."""
import json
import math
import sys
import traceback
from pathlib import Path
import bpy
from mathutils import Vector

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
import probe_current as probe
import character_designer
from character_designer import body_original_mode as original, body_rest_resync as resync
from character_designer import control_pose_assets as poses, forearm_twist as forearm, limb_ik_fk as match, limb_ik

facts = {'diagnostic_only': True, 'artist_opened': False, 'scene_saved': False}
ordinary_match = poses._match
verify = resync.verify

def ordinary(*args, **kwargs):
    kwargs.pop('precise_limbs', None)
    return ordinary_match(*args, **kwargs)

def inspect(context, rig, plan):
    inventory = limb_ik._validate_inventory(rig)
    facts['limbs'] = []
    for key in sorted(plan['keys']):
        entry = inventory['rigs'][key]
        wanted = {name: plan['desired'][name] for name in entry['chain']}
        start, joint, end = [wanted[name].translation for name in entry['chain']]
        axis = (end - start).normalized()
        radial = limb_ik._project_perpendicular(joint-start, axis).length
        length = (joint-start).length + (end-joint).length
        skin = {}
        for name in entry['chain']:
            now = rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted()
            old = plan['skin'][name]
            skin[name] = max(abs(a-b) for row, other in zip(now, old) for a,b in zip(row,other))
        facts['limbs'].append({'key': list(key), 'pose_errors': list(match._pose_errors(rig, wanted)),
            'matrix_errors': {name: poses._difference(wanted[name], rig.pose.bones[name].matrix) for name in wanted},
            'skin_errors': skin, 'bend_ratio': radial / length, 'mode': match.mode_for_rig(rig, entry),
            'pole_matrix': probe.matrix(rig.pose.bones[entry['pole'].name].matrix),
            'desired': {name: probe.matrix(matrix) for name,matrix in wanted.items()}})
    return verify(context, rig, plan)

try:
    assert bpy.app.background
    facts['input_before'] = probe.fingerprint(FOLDER / 'X_live_input.blend')
    bpy.ops.wm.open_mainfile(filepath=str(FOLDER / 'X_live_input.blend'), load_ui=False, use_scripts=False)
    forearm._BUSY = True
    character_designer.register()
    rig = bpy.data.objects['CoshaRig']
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.context.view_layer.update()
    forearm._BUSY = False
    poses._match, resync.verify = ordinary, inspect
    original.leave(bpy.context, rig)
    facts['outcome'] = 'ordinary_match_passed'
except Exception as exc:
    facts.update({'outcome': 'refused', 'error': str(exc), 'traceback': traceback.format_exc()})
finally:
    poses._match, resync.verify = ordinary_match, verify
    facts['input_after'] = probe.fingerprint(FOLDER / 'X_live_input.blend')
    facts['input_unchanged'] = facts.get('input_before') == facts['input_after']
    (FOLDER / 'ordinary_match_diagnostic.json').write_text(json.dumps(facts, indent=2), encoding='utf-8')
    print('ORDINARY_MATCH_DIAGNOSTIC', facts['outcome'], facts.get('error'), flush=True)
