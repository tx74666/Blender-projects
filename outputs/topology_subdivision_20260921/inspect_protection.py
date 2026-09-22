"""Read-only live source-ring diagnostics. Run in Blender; keeps the current area.

No operator, reload, update_from_editmode, timer, mode switch, or RNA assignment
is used. The only write is live_protection.json beside this script.
"""
import hashlib
import json
import traceback
from pathlib import Path

import bpy
import bmesh

import character_designer
from character_designer import finger_ring_slide as slide, finger_workflow as work
from character_designer.mesh_mirror import INTERNAL_ATTRIBUTES, _value


OUTPUT = Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_protection.json')
C = bpy.context


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=repr).encode('utf8')).hexdigest()


def attr_value(attribute, index):
    field, value = _value(attribute.data[index])
    return {'field': field, 'value': value}


def numeric_delta(a, b):
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return {'b_minus_a': b-a, 'max_abs': abs(b-a)}
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        if all(isinstance(v, (float, int)) for v in list(a)+list(b)):
            delta = [y-x for x, y in zip(a, b)]
            return {'b_minus_a': delta, 'max_abs': max(map(abs, delta), default=0)}
    return None


def identity_diff(current, confirmed, path='$'):
    """Show every differing leaf; full identity objects are also saved below."""
    result = []
    if isinstance(current, dict) and isinstance(confirmed, dict):
        for key in sorted(current.keys() | confirmed.keys()):
            child = path+'.'+str(key)
            if key not in current:
                result.append({'path': child, 'current_missing': True, 'confirmed': confirmed[key]})
            elif key not in confirmed:
                result.append({'path': child, 'confirmed_missing': True, 'current': current[key]})
            else:
                result.extend(identity_diff(current[key], confirmed[key], child))
    elif isinstance(current, list) and isinstance(confirmed, list):
        if len(current) != len(confirmed):
            result.append({'path': path+'.length', 'current': len(current), 'confirmed': len(confirmed)})
        for index in range(max(len(current), len(confirmed))):
            child = path+'['+str(index)+']'
            if index >= len(current):
                result.append({'path': child, 'current_missing': True, 'confirmed': confirmed[index]})
            elif index >= len(confirmed):
                result.append({'path': child, 'confirmed_missing': True, 'current': current[index]})
            else:
                result.extend(identity_diff(current[index], confirmed[index], child))
    elif current != confirmed:
        result.append({'path': path, 'current': current, 'confirmed': confirmed,
                       'delta': numeric_delta(confirmed, current)})
    return result


def unchanged_guard(obj, source):
    """Read evidence directly; deliberately avoid validators that synchronize RNA."""
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        deform = bm.verts.layers.deform.active
        geometry = ([tuple(v.co) for v in bm.verts],
                    [tuple(v.index for v in edge.verts) for edge in bm.edges],
                    [tuple(v.index for v in face.verts) for face in bm.faces],
                    [sorted(v[deform].items()) for v in bm.verts] if deform else [],
                    [[element.select for element in sequence] for sequence in (bm.verts, bm.edges, bm.faces)])
    else:
        geometry = ([tuple(v.co) for v in obj.data.vertices],
                    [tuple(edge.vertices) for edge in obj.data.edges],
                    [tuple(face.vertices) for face in obj.data.polygons],
                    [[(group.group, group.weight) for group in v.groups] for v in obj.data.vertices])
    shapes = obj.data.shape_keys
    shape_data = [(key.name, key.value, key.mute, [tuple(p.co) for p in key.data])
                  for key in shapes.key_blocks] if shapes else []
    workflow = obj.character_designer_finger_workflow
    bank = obj.character_designer_finger_bank
    metadata = (workflow.source.as_pointer() if workflow.source else None,
                workflow.signature, workflow.results, workflow.bodies, workflow.status,
                workflow.preview_enabled, workflow.get('topology', ''),
                [(pair.name, pair.recipe, pair.labels, pair.applied, work.parameters(pair)) for pair in workflow.pairs],
                bank.active, bank.survey, bank.status, bank.needs_recheck,
                [(slot.name, slot.guide.record, slot.guide.bend_record, slot.guide.revision,
                  slot.guide.flip_bend, slot.guide.confirmed, slot.error, slot.bones) for slot in bank.slots])
    rigs = [(rig.name, rig.mode, tuple(tuple(row) for row in rig.matrix_world),
             [(bone.name, bone.parent.name if bone.parent else None,
               tuple(bone.head), tuple(bone.tail), bone.roll) for bone in rig.data.edit_bones]
             if rig.mode == 'EDIT' else
             [(bone.name, bone.parent.name if bone.parent else None,
               tuple(bone.head_local), tuple(bone.tail_local), tuple(tuple(row) for row in bone.matrix_local))
              for bone in rig.data.bones]) for rig in bpy.data.objects if rig.type == 'ARMATURE']
    source_data = None if source is None else (
        source.as_pointer(), [tuple(v.co) for v in source.vertices],
        [(attr.name, attr.domain, attr.data_type, [_value(item) for item in attr.data]) for attr in source.attributes])
    return {'area_type': C.area.type if C.area else None, 'mode': C.mode,
            'active': C.view_layer.objects.active.name if C.view_layer.objects.active else None,
            'mesh_pointer': obj.data.as_pointer(), 'mesh': digest(geometry), 'shape_keys': digest(shape_data),
            'source': digest(source_data), 'rigs': digest(rigs), 'metadata': digest(metadata)}


def ring_reasons(source, recipe, face_map, edge_map):
    rows = recipe['rings']
    positions = recipe['positions']
    protected = set(slide.protected_rows(source, rows))
    descriptions = []
    for index, row in enumerate(rows):
        item = {'row': index, 't': positions[index], 'vertices': row,
                'coordinates': [tuple(source.vertices[vi].co) for vi in row],
                'protected': index in protected, 'boundary': index in (0, len(rows)-1), 'reasons': []}
        descriptions.append(item)
        if item['boundary']: continue
        for column in range(len(row)):
            following = (column+1) % len(row)
            edge = edge_map[frozenset((row[column], row[following]))]
            location = {'column': column, 'edge': edge.index, 'edge_vertices': list(edge.vertices)}
            flags = {name: getattr(edge, name, False) for name in ('use_seam', 'use_edge_sharp', 'use_freestyle_mark')}
            if any(flags.values()):
                item['reasons'].append(dict(location, reason='CIRCUMFERENTIAL_EDGE_FLAG', values=flags))
            a = face_map[frozenset((rows[index-1][column], rows[index-1][following], row[column], row[following]))]
            b = face_map[frozenset((row[column], row[following], rows[index+1][column], rows[index+1][following]))]
            sides = dict(location, root_face=a.index, tip_face=b.index)
            if (a.material_index, a.use_smooth) != (b.material_index, b.use_smooth):
                item['reasons'].append(dict(sides, reason='FACE_MATERIAL_OR_SMOOTH_BOUNDARY',
                    root={'material_index': a.material_index, 'use_smooth': a.use_smooth},
                    tip={'material_index': b.material_index, 'use_smooth': b.use_smooth}))
            for attribute in source.attributes:
                name = attribute.name
                if name in INTERNAL_ATTRIBUTES or name.startswith(('.select', '.hide')): continue
                attr = {'attribute': name, 'domain': attribute.domain, 'type': attribute.data_type}
                if attribute.domain == 'FACE' and name != 'custom_normal':
                    av, bv = attr_value(attribute, a.index), attr_value(attribute, b.index)
                    if av != bv:
                        item['reasons'].append(dict(sides, **attr, reason='FACE_ATTRIBUTE_DISCONTINUITY',
                                                   root=av, tip=bv, delta=numeric_delta(av['value'], bv['value'])))
                if attribute.domain == 'CORNER' and name != 'custom_normal':
                    for vi in (row[column], row[following]):
                        ia = next(li for li in a.loop_indices if source.loops[li].vertex_index == vi)
                        ib = next(li for li in b.loop_indices if source.loops[li].vertex_index == vi)
                        av, bv = attr_value(attribute, ia), attr_value(attribute, ib)
                        if av != bv:
                            item['reasons'].append(dict(sides, **attr, reason='CORNER_ATTRIBUTE_DISCONTINUITY',
                                vertex=vi, root_loop=ia, tip_loop=ib, root=av, tip=bv,
                                delta=numeric_delta(av['value'], bv['value'])))
                if attribute.domain == 'EDGE':
                    value = attr_value(attribute, edge.index)
                    # Match protected_rows' exact predicate, including vector
                    # values, so the report exposes any over-broad zero test.
                    if value['value'] != 0 and value['value'] is not False:
                        item['reasons'].append(dict(location, **attr, reason='NONZERO_EDGE_ATTRIBUTE', sample=value))
        item['reason_count'] = len(item['reasons'])
    return {'saved_protected_rows': recipe.get('protected_rows'),
            'computed_protected_rows': sorted(protected), 'rows': descriptions}


report = {'version': character_designer.bl_info['version'], 'module': character_designer.__file__,
          'workflow_module': work.__file__, 'slide_module': slide.__file__,
          'read_only': True, 'objects': []}
guards = []
try:
    selected = bpy.data.objects.get('Cosha')
    objects = [selected] if selected is not None else [
        obj for obj in bpy.data.objects if obj.type == 'MESH' and
        getattr(obj, 'character_designer_finger_workflow', None) and obj.character_designer_finger_workflow.source]
    for obj in objects:
        state = obj.character_designer_finger_workflow
        source = state.source
        guard = unchanged_guard(obj, source)
        guards.append((obj, source, guard))
        entry = {'object': obj.name, 'source': source.name if source else None,
                 'source_pointer': source.as_pointer() if source else None,
                 'bank_active': obj.character_designer_finger_bank.active,
                 'before': guard, 'pairs': {}}
        report['objects'].append(entry)
        if source is None:
            entry['error'] = 'No immutable workflow source is available.'
            continue
        entry['source_attributes'] = [{'name': attr.name, 'domain': attr.domain, 'type': attr.data_type,
            'ignored_by_protection': attr.name in INTERNAL_ATTRIBUTES or attr.name.startswith(('.select', '.hide')) or attr.name == 'custom_normal'}
            for attr in source.attributes]
        entry['source_materials'] = [material.name if material else None for material in source.materials]
        faces = {frozenset(polygon.vertices): polygon for polygon in source.polygons}
        edges = {frozenset(edge.vertices): edge for edge in source.edges}
        saved = json.loads(state.results or '{}')
        for pair in state.pairs:
            current = {'applied': pair.applied, 'phase': work.committed_phase(pair, state),
                       'support_ready': work.support_ready(pair, state),
                       'current_center_parameters': work._center_parameters(pair),
                       'joints': work.parameters(pair), 'recipes': {}}
            entry['pairs'][pair.name] = current
            try:
                for key, recipe in json.loads(pair.recipe or '{}').items():
                    identity = work._center_identity(recipe)
                    result = saved.get(key, {})
                    confirmation = result.get('center_confirmation', {})
                    details = {'current_center_identity': identity, 'saved_center_confirmation': confirmation,
                        'identity_equal': identity == confirmation.get('identity'),
                        'identity_differences': identity_diff(identity, confirmation.get('identity')),
                        'parameters_equal': current['current_center_parameters'] == confirmation.get('parameters'),
                        'saved_center_rows': result.get('center_rows'), 'saved_phase': result.get('phase'),
                        'saved_subdivision_dirty': result.get('subdivision_dirty'), 'saved_layout_schema': result.get('layout_schema')}
                    current['recipes'][key] = details
                    try: details['protection'] = ring_reasons(source, recipe, faces, edges)
                    except Exception: details['protection_error'] = traceback.format_exc()
            except Exception: current['error'] = traceback.format_exc()
except Exception:
    report['error'] = traceback.format_exc()
finally:
    for obj, source, before in guards:
        entry = next(value for value in report['objects'] if value['object'] == obj.name)
        try:
            entry['after'] = unchanged_guard(obj, source)
            entry['unchanged'] = before == entry['after']
        except Exception: entry['guard_error'] = traceback.format_exc()
    report['all_unchanged'] = bool(report['objects']) and all(value.get('unchanged') for value in report['objects'])
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print('READ_ONLY_PROTECTION_REPORT', str(OUTPUT), 'unchanged=', report['all_unchanged'])
