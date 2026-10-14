"""Exercise saved X in an isolated process; never save the artist file."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

import bpy

HERE = Path(__file__).resolve().parent
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
sys.path.insert(0, str(HERE / 'approved_release_0775' / 'addons'))
import character_designer
from character_designer import skirt_rig, skirt_wiggle as motion, skirt_wiggle_ui as ui
from character_designer import body_original_mode, hair_wiggle_adapter


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def author_proof():
    values = []
    for mesh in bpy.data.meshes:
        values.append((mesh.name, tuple(tuple(v.co) for v in mesh.vertices),
            tuple(tuple(p.vertices) for p in mesh.polygons),
            tuple(tuple((g.group, g.weight) for g in v.groups) for v in mesh.vertices),
            tuple((key.name, tuple(tuple(point.co) for point in key.data))
                  for key in mesh.shape_keys.key_blocks) if mesh.shape_keys else None))
    rest = [(obj.name, tuple((b.name, tuple(tuple(row) for row in b.matrix_local),
                             b.parent.name if b.parent else None, b.use_deform)
                            for b in obj.data.bones))
            for obj in bpy.data.objects if obj.type == 'ARMATURE']
    return digest_value((values, rest, hair_wiggle_adapter._animation_proof()))


def digest_value(value):
    return hashlib.sha256(repr(value).encode('utf-8')).hexdigest()


def visual(source, rig, record):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    try:
        vertices = [tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    names = [name for chain in record['chains'] for name in chain['def']]
    armature = rig.evaluated_get(graph)
    return vertices, {name: tuple(tuple(row) for row in armature.pose.bones[name].matrix) for name in names}


def error(first, second):
    before, matrices = first
    after, other = second
    assert len(before) == len(after)
    return max([abs(a-b) for one, two in zip(before, after) for a, b in zip(one, two)]
        + [abs(a-b) for name in matrices for one, two in zip(matrices[name], other[name])
           for a, b in zip(one, two)], default=0)


report = {'artist': str(ARTIST), 'artist_sha_before': digest(ARTIST), 'passed': False,
          'blender': bpy.app.version_string, 'source_version': character_designer.bl_info['version'],
          'scene_saved': False, 'checks': []}
try:
    backend_path = Path(bpy.utils.user_resource('SCRIPTS')) / 'addons' / 'wiggle_2.py'
    spec = importlib.util.spec_from_file_location('wiggle_2', backend_path)
    backend = importlib.util.module_from_spec(spec)
    sys.modules['wiggle_2'] = backend
    spec.loader.exec_module(backend)
    backend.register()
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False)
    sources = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
               and skirt_rig.RECORD_KEY in obj]
    assert sources, 'No configured Dress in saved X'
    for source in sources:
        record = skirt_rig.read_record(source)
        rig = source[skirt_rig.RIG_KEY]
        main = ui._display_owner(source)
        if body_original_mode.active(main):
            body_original_mode.leave(bpy.context, main)
        ui._show_layer(bpy.context, source, 'CONTROLS')
        proof = author_proof()
        before = visual(source, rig, record)
        motion.set_mode(bpy.context, source, 'AUTOMATIC')
        start_error = error(before, visual(source, rig, record))
        assert start_error < 5e-5, start_error
        frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_set(frame + 1)
        bpy.context.scene.frame_set(frame + 2)
        bpy.context.scene.frame_set(frame + 3)
        assert motion.status(bpy.context, source)['running']
        swung = visual(source, rig, record)
        motion.set_mode(bpy.context, source, 'MANUAL')
        stop_error = error(swung, visual(source, rig, record))
        assert stop_error < 5e-5, stop_error
        assert author_proof() == proof, 'Author mesh/weights/keys/Rest/Actions changed'
        controls, deform, mechanism = skirt_rig._bone_collection_layout(record)
        assert all(not rig.data.bones[name].hide for name in controls)
        assert all(rig.data.bones[name].hide for name in deform | mechanism)
        report['checks'].append({'source': source.name, 'rig': rig.name,
            'phys_bones': sum(len(chain['phys']) for chain in record['chains']),
            'automatic_pose_error': start_error, 'manual_pose_error': stop_error,
            'simulated_motion_delta': error(before, swung), 'author_data_unchanged': True})
    report['passed'] = True
except Exception as exc:
    report['error'] = str(exc)
    report['traceback'] = traceback.format_exc()
finally:
    motion.suspend(bpy.context, reason='Isolated model validation completed.')
    report['artist_sha_after'] = digest(ARTIST)
    assert report['artist_sha_after'] == report['artist_sha_before'], 'Artist file changed externally'
    (HERE / 'saved_x_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SAVED_X_WIGGLE_VALIDATION', json.dumps(report, ensure_ascii=False))
if not report['passed']:
    raise RuntimeError(report.get('error', 'Saved X validation failed'))
