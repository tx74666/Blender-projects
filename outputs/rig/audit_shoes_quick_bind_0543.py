"""Inspect Shoes binding and recovery metadata without binding, restoring or saving."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).parent
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import quick_bind


def assignments_summary(groups, vertex_count=None):
    result = []
    touched = set()
    for group in groups:
        positive = [(i, w) for i, w in group['weights'] if w > 0]
        touched.update(i for i, _ in positive)
        if positive:
            result.append({'name': group['name'], 'positive_assignments': len(positive),
                           'min': min(w for _, w in positive), 'max': max(w for _, w in positive),
                           'sum': sum(w for _, w in positive)})
    return {'groups_with_positive_weights': result, 'weighted_vertices': len(touched),
            'unweighted_vertices': vertex_count - len(touched) if vertex_count is not None else None}


def inspect():
    target = bpy.data.objects.get('Shoes')
    if target is None or target.type != 'MESH':
        return {'error': 'Shoes mesh is missing'}
    mods = [m for m in target.modifiers if m.type == 'ARMATURE']
    rig = next((m.object for m in mods if m.object), None)
    deform = {b.name for b in rig.data.bones if b.use_deform} if rig else set()
    tracked = {g.index: {'name': g.name, 'weights': []} for g in target.vertex_groups if g.name in deform}
    for vertex in target.data.vertices:
        for assignment in vertex.groups:
            if assignment.group in tracked:
                tracked[assignment.group]['weights'].append((vertex.index, assignment.weight))
    record = None
    record_error = None
    try:
        record = quick_bind._read_backup(target)
    except Exception as exc:
        record_error = str(exc)
    current_signature = quick_bind._topology_signature(target)
    result = {'filepath': bpy.data.filepath, 'mesh': target.data.name, 'mesh_users': target.data.users,
              'vertex_count': len(target.data.vertices), 'edge_count': len(target.data.edges),
              'face_count': len(target.data.polygons), 'topology_signature': current_signature,
              'armature_modifiers': [{'name': m.name, 'target': m.object.name if m.object else None,
                 'persistent_uid': m.persistent_uid, 'show_viewport': m.show_viewport,
                 'show_render': m.show_render, 'use_vertex_groups': m.use_vertex_groups,
                 'use_bone_envelopes': m.use_bone_envelopes, 'vertex_group_mask': m.vertex_group}
                 for m in mods],
              'modifier_stack': [{'name': m.name, 'type': m.type, 'show_viewport': m.show_viewport}
                                 for m in target.modifiers],
              'actual_deform_weights': assignments_summary(tracked.values(), len(target.data.vertices)),
              'has_backup_key': quick_bind.BACKUP_KEY in target,
              'has_rig_key': quick_bind.RIG_KEY in target,
              'backup_rig': target.get(quick_bind.RIG_KEY).name if isinstance(target.get(quick_bind.RIG_KEY), bpy.types.ID) else None,
              'backup_structural_error': record_error}
    if record is not None:
        result['backup'] = {'version': record['version'], 'mode': record.get('mode'),
             'vertex_count': record['vertex_count'], 'edge_count': record.get('edge_count'),
             'face_count': record.get('face_count'), 'topology_signature': record['topology'],
             'topology_matches_current': record['topology'] == current_signature,
             'tracked_deform_group_count': len(record['names']),
             'tracked_group_names': record['names'], 'previous_group_count': len(record['groups']),
             'previous_group_names': [g['name'] for g in record['groups']],
             'previous_weights': assignments_summary(record['groups'], record['vertex_count']),
             'modifier': record['modifier'],
             'serialized_sha256': hashlib.sha256(target[quick_bind.BACKUP_KEY].encode()).hexdigest(),
             'stored_fields': sorted(record)}
        for label, call in (('topology_guard', lambda: quick_bind._check_backup_topology(target, record)),
                            ('modifier_guard', lambda: quick_bind._backup_modifier(target, record, allow_missing=True))):
            try:
                call()
                result[label] = 'PASS'
            except Exception as exc:
                result[label] = str(exc)
    return result


def main():
    inputs = [Path(bpy.data.filepath)]
    if '--' in sys.argv:
        inputs.extend(Path(x) for x in sys.argv[sys.argv.index('--') + 1:])
    reports = []
    for index, path in enumerate(inputs):
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        if index:
            bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
        entry = inspect()
        entry['input_sha256'] = before
        entry['input_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest() == before
        reports.append(entry)
    report = {'blender': bpy.app.version_string, 'scenes': reports,
              'notes': ['No binding, restoring, weight writes, or file saves were performed.',
                        'Version1 recovery metadata stores a vertex count and connectivity hash; separate saved edge/face counts are not recorded.',
                        'Restore visibility checks backup-property presence; red button styling is unconditional in current panel code.']}
    path = OUT / 'shoes_quick_bind_0543_audit.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf8')
    print('SHOES_QUICK_BIND_AUDIT', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
