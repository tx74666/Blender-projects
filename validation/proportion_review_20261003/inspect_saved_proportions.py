"""Read saved X coordinates, bindings and reference pixels; never save a blend."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'Validation' / 'proportion_review_20261003'
SOURCE = ROOT / 'X.blend'
OUT.mkdir(parents=True, exist_ok=True)
before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
report = {'source': str(SOURCE), 'source_sha256': before,
          'blender_version': bpy.app.version_string, 'frame': bpy.context.scene.frame_current,
          'scope': 'saved Basis/Rest data only; current unsaved artist edits not read',
          'references': [], 'meshes': {}, 'bones': {}, 'dress_curves': [], 'saved': False}
for name in ('Front', 'Side', 'Coat'):
    obj = bpy.data.objects.get(name)
    if obj is None or not isinstance(obj.data, bpy.types.Image):
        continue
    im = obj.data
    entry = {'object': name, 'image': im.name, 'filepath': im.filepath,
             'size': list(im.size), 'matrix_world': [list(row) for row in obj.matrix_world],
             'empty_display_size': obj.empty_display_size, 'image_offset': list(obj.empty_image_offset)}
    if im.packed_file:
        payload = bytes(im.packed_file.data)
        suffix = '.png' if payload.startswith(b'\x89PNG') else '.jpg' if payload.startswith(b'\xff\xd8') else '.img'
        target = OUT / (name + '_reference' + suffix)
        target.write_bytes(payload)
        entry['extracted'] = str(target)
    else:
        entry['resolved'] = bpy.path.abspath(im.filepath)
    report['references'].append(entry)
for name in ('Cosha', 'Dress', 'Clothes', 'Stocking'):
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != 'MESH':
        continue
    mesh = obj.data
    coords = mesh.shape_keys.reference_key.data if mesh.shape_keys else mesh.vertices
    vertices = [list(obj.matrix_world @ v.co) for v in coords]
    groups = {vg.index: vg.name for vg in obj.vertex_groups}
    weights = [[(groups[g.group], g.weight) for g in v.groups if g.weight > 1e-7] for v in mesh.vertices]
    report['meshes'][name] = {'vertices': vertices, 'edges': [list(e.vertices) for e in mesh.edges],
                             'faces': [list(p.vertices) for p in mesh.polygons], 'weights': weights,
                             'bounds': [[min(v[k] for v in vertices), max(v[k] for v in vertices)] for k in range(3)],
                             'modifiers': [{'name': m.name, 'type': m.type,
                                            'object': getattr(m, 'object', None).name if getattr(m, 'object', None) else None}
                                           for m in obj.modifiers]}
rig = bpy.data.objects.get('CoshaRig')
for bone in rig.data.bones:
    if bone.name in ('Hips', 'thigh.L', 'thigh.R', 'shin.L', 'shin.R', 'foot.L', 'foot.R', 'Head', 'Neck', 'spine') or 'SK_Dress' in bone.name:
        pb = rig.pose.bones[bone.name]
        report['bones'][bone.name] = {'head': list(rig.matrix_world @ bone.head_local),
            'tail': list(rig.matrix_world @ bone.tail_local), 'parent': bone.parent.name if bone.parent else None,
            'deform': bone.use_deform, 'constraints': [
                {'name': c.name, 'type': c.type, 'target': getattr(c, 'target', None).name if getattr(c, 'target', None) else None,
                 'subtarget': getattr(c, 'subtarget', None), 'influence': c.influence,
                 'mix_mode': getattr(c, 'mix_mode', None), 'mute': c.mute} for c in pb.constraints]}
for obj in bpy.data.objects:
    if obj.type == 'CURVE' and 'Dress' in obj.name:
        report['dress_curves'].append({'name': obj.name, 'parent': obj.parent.name if obj.parent else None,
            'parent_type': obj.parent_type, 'parent_bone': obj.parent_bone,
            'modifiers': [{'name': m.name, 'type': m.type} for m in obj.modifiers]})
report['source_unchanged'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
assert report['source_unchanged']
(OUT / 'saved_structure.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
print('PROPORTION_READ', json.dumps({'references': report['references'],
    'mesh_counts': {n:len(v['vertices']) for n,v in report['meshes'].items()},
    'source_unchanged': report['source_unchanged']}, ensure_ascii=False), flush=True)
