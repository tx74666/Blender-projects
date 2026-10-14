"""One bounded read-only original-window diagnostic; no state assignments."""
import json
import os
from pathlib import Path
import sys


def ref(value):
    if value is None:
        return None
    try:
        return {'name': getattr(value, 'name', None),
                'pointer': int(value.as_pointer()), 'type': type(value).__name__}
    except Exception as error:
        return {'error': str(error), 'type': type(value).__name__}


def compare(left, right):
    a, b = ref(left), ref(right)
    return {'left': a, 'right': b, 'python_is': left is right,
            'python_equal': left == right,
            'native_pointer_equal': bool(a and b and 'pointer' in a and
                'pointer' in b and a['pointer'] == b['pointer'])}


def current(bpy):
    ctx = bpy.context
    return {'window': ref(ctx.window), 'scene': ref(ctx.scene),
            'view_layer': ref(ctx.view_layer), 'mode': ctx.mode,
            'frame': ctx.scene.frame_current if ctx.scene else None,
            'frame_subframe': ctx.scene.frame_subframe if ctx.scene else None,
            'active_object': ref(ctx.view_layer.objects.active) if ctx.view_layer else None,
            'selected_objects': sorted((ref(o) for o in ctx.selected_objects), key=lambda o: o['name']),
            'filepath': bpy.data.filepath, 'dirty': bool(bpy.data.is_dirty)}


def run(output_path):
    import bpy
    path = Path(output_path).resolve()
    allowed = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012').resolve()
    assert path.is_relative_to(allowed) and not path.exists()
    assert os.getpid() == 27676
    assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
    before = current(bpy)
    ctx = bpy.context
    windows = []
    for window in ctx.window_manager.windows:
        scene, layer = window.scene, window.view_layer
        rig = scene.objects.get('CoshaRig')
        setup = getattr(getattr(scene, 'character_designer_setup', None), 'rig', None)
        worklist = getattr(getattr(scene, 'character_designer_animation_worklist', None), 'rig', None)
        member = layer.objects.get('CoshaRig')
        windows.append({'window': ref(window), 'scene': ref(scene), 'view_layer': ref(layer),
            'rig': ref(rig), 'rig_type': getattr(rig, 'type', None),
            'rig_library': ref(rig.library) if rig else None,
            'rig_data': ref(rig.data) if rig else None,
            'rig_data_library': ref(rig.data.library) if rig else None,
            'setup_rig': ref(setup), 'worklist_rig': ref(worklist),
            'checks': {'context_scene_vs_window_scene': compare(ctx.scene, scene),
                'context_view_layer_vs_window_view_layer': compare(ctx.view_layer, layer),
                'view_layer_member_vs_rig': compare(member, rig),
                'setup_rig_vs_rig': compare(setup, rig),
                'worklist_rig_vs_rig': compare(worklist, rig)}})
    original_windows = [w for w in ctx.window_manager.windows if w.scene.name == 'Scene']
    assert len(original_windows) == 1
    original_window = original_windows[0]
    # Match the failed helper's window-only override. No Window.scene or
    # view-layer assignment, operator, selection or evaluation occurs.
    with bpy.context.temp_override(window=original_window):
        scoped = bpy.context
        scoped_rig = scoped.scene.objects.get('CoshaRig')
        setup_rig = getattr(getattr(scoped.scene, 'character_designer_setup', None), 'rig', None)
        worklist_rig = getattr(getattr(scoped.scene, 'character_designer_animation_worklist', None), 'rig', None)
        overridden = {'context': current(bpy), 'window': ref(original_window),
            'rig': ref(scoped_rig), 'rig_type': getattr(scoped_rig, 'type', None),
            'rig_local': scoped_rig is not None and scoped_rig.library is None,
            'rig_data_local': scoped_rig is not None and scoped_rig.data.library is None,
            'checks': {
                'context_scene_vs_window_scene': compare(scoped.scene, original_window.scene),
                'context_view_layer_vs_window_view_layer': compare(scoped.view_layer, original_window.view_layer),
                'view_layer_member_vs_rig': compare(scoped.view_layer.objects.get('CoshaRig'), scoped_rig),
                'setup_rig_vs_rig': compare(setup_rig, scoped_rig),
                'worklist_rig_vs_rig': compare(worklist_rig, scoped_rig)}}
    scene = bpy.data.scenes.get('Scene')
    named = scene.objects.get('CoshaRig') if scene else None
    module = sys.modules.get('character_designer')
    after = current(bpy)
    report = {'schema': 'x.validation.original-context-identity-readonly/1',
        'completed': True, 'read_only': True, 'pid': os.getpid(),
        'before': before, 'windows': windows, 'named_scene': ref(scene),
        'named_scene_rig': ref(named), 'all_armatures': [ref(o) for o in bpy.data.objects if o.type == 'ARMATURE'],
        'loaded_CD': {'file': getattr(module, '__file__', None),
            'version': list(module.bl_info['version']) if module else None},
        'original_window_override': overridden,
        'after': after, 'current_context_unchanged': before == after,
        'state_assignments': 0, 'context_overrides': 1, 'scene_switches': 0,
        'frame_evaluations': 0, 'save_calls': 0, 'candidate_imports': 0,
        'limits': ['A single window-only temporary context override reproduces the failed guard; actual Window Scene and ViewLayer are never assigned.',
            'No original adoption, bone/weight/constraint editing, refresh, save or worker operation.']}
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')
    print('ORIGINAL_CONTEXT_READONLY ' + json.dumps(report, ensure_ascii=True, allow_nan=False))
