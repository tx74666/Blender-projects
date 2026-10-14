"""Read current Forearm Twist state, then save a protected copy only."""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ARTIST = BASE.parent.parent / 'X.blend'
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
from character_designer import forearm_twist as twist, limb_ik, limb_ik_fk
ns = {'CAPTURE_OUTPUT_PATH': str(BASE/'rig_live_before.json')}
exec(compile((BASE.parent/'arm_pole_20261009'/'capture_live.py').read_text(encoding='utf-8'),
             'forearm_read_only_rig_capture', 'exec'), ns)
plain = ns['plain']
rig = bpy.data.objects['CoshaRig']
depsgraph = bpy.context.evaluated_depsgraph_get()
ev = rig.evaluated_get(depsgraph)
state = {'artist': str(ARTIST), 'runtime_version': plain(sys.modules['character_designer'].bl_info['version']),
         'frame': bpy.context.scene.frame_current, 'mode': bpy.context.mode,
         'active_object': bpy.context.object.name if bpy.context.object else None,
         'runtime': {n: plain(getattr(twist,n)) for n in ('_BUSY','_UI_BUSY','_RUNTIME_REGISTERED',
                      '_INITIALIZE_PENDING','_SCENE_CLEANUP_PENDING','_ERRORS')},
         'session': plain(twist._SESSION), 'meshes': {}, 'arms': {}, 'settings': {},
         'handlers': {name: [getattr(fn,'__module__','')+'.'+getattr(fn,'__name__',str(fn))
                     for fn in getattr(bpy.app.handlers,name)]
                     for name in ('depsgraph_update_post','frame_change_post','load_post','save_pre','save_post')}}
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    keys = obj.data.shape_keys
    state['meshes'][obj.name] = {
        'mesh': obj.data.name, 'vertices': len(obj.data.vertices), 'edges': len(obj.data.edges),
        'polygons': len(obj.data.polygons), 'properties': ns['props'](obj),
        'topology': twist._topology_digest(obj.data), 'show_only_shape_key': obj.show_only_shape_key,
        'modifiers': [{'name':m.name,'type':m.type,'object':getattr(getattr(m,'object',None),'name',None),
                       'viewport':m.show_viewport,'render':m.show_render,
                       'preserve_volume':getattr(m,'use_deform_preserve_volume',None)} for m in obj.modifiers],
        'keys': [] if not keys else [{'name':k.name,'value':k.value,'mute':k.mute,
                   'relative':k.relative_key.name,'vertex_group':k.vertex_group,'vertices':len(k.data)}
                   for k in keys.key_blocks],
        'calibration': twist._records(obj), 'preview': plain(obj.get(twist.PREVIEW_KEY))}
for side in 'LR':
    lower,hand = ('forearm.'+side,'hand.'+side)
    axis = rig.data.bones[lower].tail_local-rig.data.bones[lower].head_local
    mats = {n:ev.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted() for n in (lower,hand)}
    try: angle = math.degrees(twist.twist_angle(mats[lower],mats[hand],axis))
    except Exception as exc: angle = {'error':str(exc)}
    state['arms'][side] = {'angle_degrees':angle,'deformation':plain(mats),
                          'target_status':plain(twist.controller_status(rig,'CTRL_hand_IK.'+side))}
settings = bpy.context.window_manager.character_designer_forearm_twist
for prop in settings.bl_rna.properties:
    if prop.identifier != 'rna_type' and prop.type not in {'COLLECTION','POINTER'}:
        state['settings'][prop.identifier] = plain(getattr(settings,prop.identifier))
(BASE/'live_before.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
assert twist._SESSION is None, 'Captured only: active calibration preview must be preserved before a backup.'
backup = BASE/'X_before_forearm_twist_fix.blend'
assert not backup.exists(), 'Protection copy already exists; inspect instead of overwriting.'
before_artist = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
saved = bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)
assert saved == {'FINISHED'} and Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert hashlib.sha256(ARTIST.read_bytes()).hexdigest() == before_artist
(BASE/'backup_receipt.json').write_text(json.dumps({'artist':str(ARTIST),'artist_sha256':before_artist,
    'backup':str(backup),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),
    'native_result':sorted(saved)},ensure_ascii=False,indent=2),encoding='utf-8')
print('FOREARM_TWIST_CAPTURE_AND_BACKUP_OK')
