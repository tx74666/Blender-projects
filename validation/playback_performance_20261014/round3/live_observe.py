"""Read the current artist runtime; no refresh, playback, save or scene writes."""
import bpy
import datetime
import hashlib
import json
import marshal
import os
from pathlib import Path
import sys

OUT = Path(r'D:\Blender\Projects\Character\X\validation\playback_performance_20261014\round3')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert not bpy.app.background
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'Not the original X artist'

def file_pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}

def callback_info(callback):
    return {'module': getattr(callback, '__module__', ''),
            'name': getattr(callback, '__qualname__', repr(callback)),
            'code_sha256': hashlib.sha256(marshal.dumps(callback.__code__)).hexdigest()
            if hasattr(callback, '__code__') else None}

modules = {name: module for name, module in tuple(sys.modules.items())
           if name == 'character_designer' or name.endswith('.character_designer')}
scene = bpy.context.scene
report = {
    'schema': 'x.playback-live-observation/1',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'pid': os.getpid(), 'blender': bpy.app.version_string,
    'file': file_pin(ARTIST), 'dirty': bool(bpy.data.is_dirty),
    'scene': scene.name, 'frame': scene.frame_current,
    'subframe': scene.frame_subframe, 'frame_start': scene.frame_start,
    'frame_end': scene.frame_end, 'sync_mode': scene.sync_mode,
    'playing': bool(bpy.context.screen.is_animation_playing),
    'mode': bpy.context.mode,
    'active_object': bpy.context.view_layer.objects.active.name
    if bpy.context.view_layer.objects.active else None,
    'addons': {name: {'version': list(getattr(module, 'bl_info', {}).get('version', ())),
                      'source': file_pin(module.__file__)}
               for name, module in modules.items()},
    'handlers': {kind: [callback_info(cb) for cb in getattr(bpy.app.handlers, kind)]
                 for kind in ('frame_change_pre', 'frame_change_post',
                              'depsgraph_update_pre', 'depsgraph_update_post')},
    'areas': [{'type': area.type, 'width': area.width, 'height': area.height,
               'shading': area.spaces.active.shading.type if area.type == 'VIEW_3D' else None,
               'overlays': area.spaces.active.overlay.show_overlays if area.type == 'VIEW_3D' else None}
              for area in bpy.context.screen.areas],
    'actions': {obj.name: obj.animation_data.action.name
                for obj in scene.objects if obj.animation_data and obj.animation_data.action},
    'rig_bone_counts': {obj.name: len(obj.data.bones)
                        for obj in scene.objects if obj.type == 'ARMATURE'},
    'mesh_modifiers': {obj.name: [{'name': modifier.name, 'type': modifier.type,
                                'viewport': modifier.show_viewport,
                                'render': modifier.show_render}
                               for modifier in obj.modifiers]
                       for obj in scene.objects if obj.type == 'MESH'},
    'scene_writes': False, 'refresh': False, 'save': False,
}
for root in modules:
    runtime = sys.modules.get(root + '.forearm_twist')
    if runtime is not None:
        report['forearm'] = {'errors': dict(runtime._ERRORS),
                             'busy': runtime._BUSY,
                             'calibrated_meshes': {obj.name: {
                                 side: {'enabled': record.get('enabled', True),
                                        'support_vertices': len(record['vertices'])}
                                 for side, record in runtime._records(obj).items()}
                                 for obj in scene.objects if obj.type == 'MESH'
                                 and runtime.RECORD_KEY in obj}}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'live_observation.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('X playback observation saved:', report['addons'], 'PID', report['pid'])
