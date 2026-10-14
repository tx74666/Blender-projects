"""Bounded read-only fingerprints of original character assets for isolated QA."""
import hashlib
import copy
import importlib
import json
import struct


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def packed_digest(rows):
    h = hashlib.sha256()
    count = 0
    for row in rows:
        h.update(struct.pack('<' + 'd' * len(row), *row))
        count += 1
    return {'count': count, 'sha256': h.hexdigest()}


def identity(value):
    return [value.name, value.library.filepath if value.library else None] if value else None


def color(value):
    return {'palette': value.palette, 'normal': list(value.custom.normal),
            'select': list(value.custom.select), 'active': list(value.custom.active),
            'constraints': value.custom.show_colored_constraints}


def scalar(value):
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if hasattr(value, 'name') and hasattr(value, 'library'):
        return identity(value)
    try:
        return list(value)
    except TypeError:
        return identity(value) if hasattr(value, 'name') else type(value).__name__


def material_content(material):
    result = {'id': identity(material), 'diffuse': list(material.diffuse_color),
              'roughness': material.roughness, 'metallic': material.metallic,
              'use_nodes': material.use_nodes}
    tree = material.node_tree
    if tree:
        result['nodes'] = [{'name': node.name, 'type': node.bl_idname,
                            'image': identity(getattr(node, 'image', None)),
                            'node_tree': identity(getattr(node, 'node_tree', None)),
                            'inputs': [[socket.identifier, scalar(getattr(socket, 'default_value', None))]
                                       for socket in node.inputs]}
                           for node in tree.nodes]
        result['links'] = sorted([link.from_node.name, link.from_socket.identifier,
                                  link.to_node.name, link.to_socket.identifier] for link in tree.links)
    return result


def authenticated_forearm_outputs(obj, rig=None):
    """Authenticate exact saved ownership, never a Shape Key name prefix.

    Do not repair names, prepare/migrate calibration, or update runtime here.
    A missing/renamed/replaced cached key or unexpected calibration fails QA.
    """
    ft = importlib.import_module('character_designer.forearm_twist')
    if ft.RECORD_KEY not in obj:
        return {}, None
    if ft.PREVIEW_KEY in obj:
        raise AssertionError('Forearm Twist calibration preview is active: ' + obj.name)
    raw = obj[ft.RECORD_KEY]
    records = json.loads(raw)
    if not isinstance(records, dict) or not records or set(records) - {'L', 'R'}:
        raise AssertionError('Invalid exact Forearm Twist ownership record: ' + obj.name)
    armature = ft._check_mesh(obj)
    if rig is not None and armature is not rig:
        raise AssertionError('Forearm Twist record is bound to another Rig: ' + obj.name)
    keys = obj.data.shape_keys
    if keys is None:
        raise AssertionError('Forearm Twist output Key datablock is missing: ' + obj.name)
    inventory = ft.forearm_original_inventory.validate(armature)
    owned = {}
    for side, record in records.items():
        if (not isinstance(record, dict) or type(record.get('version')) is not int
                or record['version'] != 1 or record.get('armature') != armature.name
                or not isinstance(record.get('key'), str) or not record['key']
                or not isinstance(record.get('chain'), list) or len(record['chain']) != 3
                or any(name not in armature.data.bones for name in record['chain'])
                or not isinstance(record.get('rest'), list)
                or [row[0] for row in record['rest']] != record['chain']):
            raise AssertionError('Invalid recorded Forearm Twist owner/chain: ' + obj.name + '/' + side)
        key = keys.key_blocks.get(record['key'])
        cached = ft._KEY_REFERENCES.get((obj.as_pointer(), side))
        if (key is None or key.name != record['key'] or key.id_data != keys
                or key.relative_key != keys.reference_key or key.vertex_group
                or len(key.data) != len(obj.data.vertices)
                or (cached is not None and (cached.as_pointer() != key.as_pointer()
                                           or cached.id_data != keys))):
            raise AssertionError('Forearm Twist exact managed Key reference changed: ' + obj.name + '/' + side)
        if key.name in owned:
            raise AssertionError('Forearm Twist sides claim the same output Key: ' + obj.name)
        resolved_armature, resolved = ft._resolve_rig(obj, side, _inventory=inventory)
        expected_target = resolved['target'].name
        if (resolved_armature is not armature or list(resolved['chain']) != record['chain']
                or record.get('target') != expected_target):
            raise AssertionError('Forearm Twist derived target does not match official current mode: '
                                 + obj.name + '/' + side + ' recorded=' + str(record.get('target'))
                                 + ' expected=' + expected_target)
        owned[key.name] = {'side': side, 'key': key, 'record': record,
                           'key_index': next(i for i, item in enumerate(keys.key_blocks) if item == key),
                           'derived_target_proof': {'recorded_target': record['target'],
                                                    'expected_target': expected_target,
                                                    'official_resolver': 'forearm_twist._resolve_rig',
                                                    'matches_current_mode': True,
                                                    'original_source': bool(resolved.get('original_source')),
                                                    'native_source': bool(resolved.get('native_source')),
                                                    'fk_source': bool(resolved.get('fk_source'))}}
    # Probe evidence proves official Original leave changes only target. It is
    # a mode-derived cache set by _current_record, and must pass the resolver
    # proof above. Every other calibration/ownership field remains exact.
    protected_records = {side: {field: value for field, value in record.items() if field != 'target'}
                         for side, record in records.items()}
    protected = {'record_key': ft.RECORD_KEY, 'records': protected_records,
                 'bound_armature': identity(armature), 'key_datablock': identity(keys),
                 'managed_outputs': {name: {'side': row['side'], 'key_index': row['key_index'],
                                             'reference_key': keys.reference_key.name}
                                     for name, row in owned.items()}}
    return owned, protected


def mesh_content(obj, *, separate_generated=False, rig=None):
    mesh = obj.data
    group_names = {group.index: group.name for group in obj.vertex_groups}
    weights = hashlib.sha256()
    influence_count = 0
    for vertex in mesh.vertices:
        row = [vertex.index, [[group_names.get(g.group), float(g.weight)] for g in vertex.groups]]
        weights.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        weights.update(b'\n')
        influence_count += len(vertex.groups)
    result = {'object_id': identity(obj), 'data_id': identity(mesh),
              'vertices': packed_digest(tuple(v.co) for v in mesh.vertices),
              'edges': packed_digest(tuple(e.vertices) for e in mesh.edges),
              'loops': packed_digest([loop.vertex_index] for loop in mesh.loops),
              'polygons': packed_digest([p.loop_start, p.loop_total, p.material_index,
                                         float(p.use_smooth)] for p in mesh.polygons),
              'weights': {'sha256': weights.hexdigest(), 'influences': influence_count,
                          'groups': [g.name for g in obj.vertex_groups]},
              'materials': [identity(m) for m in mesh.materials],
              'material_slots': [[slot.link, identity(slot.material)] for slot in obj.material_slots],
              'shape_keys': []}
    owned, calibration = authenticated_forearm_outputs(obj, rig) if separate_generated else ({}, None)
    if calibration is not None:
        result['forearm_twist_calibration'] = calibration
    if mesh.shape_keys:
        result['shape_keys'] = [{'name': key.name, 'relative': key.relative_key.name,
                                 'vertex_group': key.vertex_group,
                                 'slider_min': key.slider_min, 'slider_max': key.slider_max,
                                 'geometry': ({'count': len(key.data), 'generated_output_owner':
                                               {'record_key': calibration['record_key'],
                                                'side': owned[key.name]['side'], 'key': key.name}}
                                              if key.name in owned else
                                              packed_digest(tuple(v.co) for v in key.data))}
                                for key in mesh.shape_keys.key_blocks]
    return result


def forearm_runtime_output_snapshot(scene, rig):
    """Record authenticated derived geometry and runtime status independently."""
    ft = importlib.import_module('character_designer.forearm_twist')
    outputs = {}
    for obj in scene.objects:
        if obj.type != 'MESH' or ft.RECORD_KEY not in obj:
            continue
        armature_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        if not any(m.object is rig for m in armature_mods):
            continue
        owned, calibration = authenticated_forearm_outputs(obj, rig)
        signatures = {}
        for name, entry in owned.items():
            recorded = entry['record']['rest']
            current = ft._rest_signature(rig, entry['record']['chain'])
            delta = max((abs(a - b) for first, second in zip(recorded, current)
                         for a, b in zip(first[1], second[1])), default=0.0)
            signatures[entry['side']] = {'exact_equal': recorded == current,
                                         'maximum_matrix_delta': delta,
                                         'record_sha256': digest(recorded),
                                         'current_sha256': digest(current)}
        outputs[obj.name] = {'calibration_sha256': digest(calibration),
                             'full_record_sha256': digest({entry['side']: entry['record']
                                                          for entry in owned.values()}),
                             'derived_target_proofs': {entry['side']: entry['derived_target_proof']
                                                       for entry in owned.values()},
                             'error': ft._ERRORS.get(obj.name),
                             'record_rest_signature_checks': signatures,
                             'keys': {name: {'side': entry['side'], 'value': entry['key'].value,
                                             'mute': entry['key'].mute,
                                             'geometry': packed_digest(tuple(v.co) for v in entry['key'].data)}
                                      for name, entry in owned.items()}}
    return {'rig': identity(rig), 'frame': scene.frame_current + scene.frame_subframe,
            'objects': outputs, 'errors': {name: row['error'] for name, row in outputs.items()
                                          if row['error'] is not None}}


def evaluate_forearm_runtime(scene, rig):
    """Publish the derived outputs at this pose, then require healthy runtime."""
    ft = importlib.import_module('character_designer.forearm_twist')
    if ft._BUSY:
        raise AssertionError('Forearm Twist remained deferred during motion validation.')
    ft.update_runtime(scene)
    result = forearm_runtime_output_snapshot(scene, rig)
    if rig.name in ft._ERRORS:
        result['errors'][rig.name] = ft._ERRORS[rig.name]
    if result['errors']:
        raise AssertionError('Forearm Twist runtime errors: ' + json.dumps(result, ensure_ascii=False))
    for obj_name, row in result['objects'].items():
        for side, check in row['record_rest_signature_checks'].items():
            if not check['exact_equal']:
                raise AssertionError(f'Forearm Twist Rest signature differs at {obj_name}/{side}: '
                                     f"{check['maximum_matrix_delta']:.9g}.")
        for key_name, output in row['keys'].items():
            record = authenticated_forearm_outputs(scene.objects[obj_name], rig)[0][key_name]['record']
            if output['value'] != 1.0 or output['mute'] != (not record.get('enabled', True)):
                raise AssertionError('Forearm Twist managed output state is stale: ' + obj_name + '/' + key_name)
    return result


def property_content(value):
    if hasattr(value, 'name') and hasattr(value, 'library'):
        return {'native_id': identity(value)}
    if hasattr(value, 'items'):
        return {key: property_content(item) for key, item in value.items()}
    if hasattr(value, 'to_list'):
        return [property_content(item) for item in value.to_list()]
    if isinstance(value, (list, tuple)):
        return [property_content(item) for item in value]
    return scalar(value)


def authenticated_display_state(rig):
    """Validate exact official display ownership; perform no synchronization.

    Native evidence retained_readopt_asset_transition.json proves the only
    preview differences are managed Body membership and these owned FK ring
    bindings. Colors, other bindings, display channels and geometry stay exact.
    Original mode suspends frame following; its full raw state is still saved
    and is required byte-exact by every Restore comparison.
    """
    groups = importlib.import_module('character_designer.bone_collections')
    fk = importlib.import_module('character_designer.limb_fk_visuals')
    limb = importlib.import_module('character_designer.limb_ik')
    modes = importlib.import_module('character_designer.limb_ik_fk')
    original = importlib.import_module('character_designer.body_original_mode')
    original_active = original.active(rig)
    record = fk.get_record(rig)
    layout = groups._managed_body_layout(rig)
    if record is None and layout is None:
        return {'original_active': original_active, 'fk_registry': None,
                'owned_widgets': {}, 'body': None}
    if original_active:
        original_inventory = importlib.import_module('character_designer.forearm_original_inventory')
        inventory = original_inventory.validate(rig)
    else:
        inventory = limb._validate_inventory(rig)
    record = fk.validate(rig, inventory)
    native = fk._native_display(rig, record)
    owned = {}
    for name, entry in (record or {}).get('bindings', {}).items():
        widget = importlib.import_module('bpy').data.objects.get(entry['object'])
        pb = rig.pose.bones[name]
        expected = None if name in native else widget
        if pb.custom_shape != expected:
            raise AssertionError('FK ring binding differs from exact native authorization: ' + name)
        mode = (None if original_active else
                modes.mode_for_rig(rig, inventory['rigs'][(entry['kind'], entry['side'])]))
        if not original_active and ((name in native) != (mode == 'FK')):
            raise AssertionError('FK ring native display does not follow official current limb mode: ' + name)
        owned[name] = {'widget': widget, 'entry': entry, 'mode': mode,
                       'temporarily_unbound': name in native}
    body = None
    if layout is not None:
        if original_active:
            collection, _backup, _saved = layout
            desired = None
        else:
            collection, _backup, _saved, desired = groups._managed_body_membership(rig, inventory, layout)
        if collection.get(groups.GROUP_KEY) != 'Body':
            raise AssertionError('Preview membership classification requires exact GROUP_KEY=Body ownership.')
        actual = set(collection.bones.keys())
        if desired is not None and actual != desired:
            raise AssertionError('Managed Body membership differs from official current mode policy: '
                                 + str(sorted(actual ^ desired)))
        body = {'name': collection.name, 'group_key': groups.GROUP_KEY,
                'owner': collection[groups.GROUP_KEY],
                'profile': property_content(rig.data.get(groups.PROFILE_KEY)),
                'automatic': property_content(rig.data.get(groups.AUTO_KEY)),
                'actual_members': sorted(actual), 'expected_members': sorted(desired) if desired is not None else None,
                'matches_current_mode': actual == desired if desired is not None else None,
                'original_frame_following_suspended': original_active,
                'official_resolver': 'bone_collections._managed_body_membership(...)[3]'}
    return {'original_active': original_active, 'fk_registry': record,
            'owned_widgets': owned, 'body': body}


def asset_payload(scene, rig, ua):
    """Exact fingerprint source fields, exposed for transition diagnosis."""
    bones = {}
    for bone in rig.data.bones:
        pb = rig.pose.bones[bone.name]
        bones[bone.name] = {'bone_color': color(bone.color), 'pose_color': color(pb.color),
            'collections': sorted(c.name for c in bone.collections),
            'widget': identity(pb.custom_shape), 'widget_transform': getattr(pb.custom_shape_transform, 'name', None),
            'widget_use_bone_size': pb.use_custom_shape_bone_size,
            'widget_scale': list(pb.custom_shape_scale_xyz),
            'widget_rotation': list(pb.custom_shape_rotation_euler),
            'widget_translation': list(pb.custom_shape_translation),
            'widget_wire_width': pb.custom_shape_wire_width}
    collections = [{'name': c.name, 'parent': c.parent.name if c.parent else None,
                    'bones': sorted(b.name for b in c.bones)} for c in rig.data.collections_all]
    skins = [obj for obj in scene.objects if obj.type == 'MESH' and
             (obj.parent is rig or any(m.type == 'ARMATURE' and m.object is rig for m in obj.modifiers))]
    widgets = sorted({pb.custom_shape for pb in rig.pose.bones if pb.custom_shape}, key=lambda o: o.name)
    meshes = {obj.name: mesh_content(obj, separate_generated=True, rig=rig) for obj in skins}
    widget_rows = {obj.name: {'mesh': mesh_content(obj) if obj.type == 'MESH' else None,
                             'matrix_basis': [list(row) for row in obj.matrix_basis]}
                   for obj in widgets}
    materials = {m.name: material_content(m) for obj in skins for m in obj.data.materials if m}
    return {'rest': ua._rest_state(rig.data), 'rig_raw_transform': {
            'location': list(rig.location), 'rotation_mode': rig.rotation_mode,
            'rotation_euler': list(rig.rotation_euler), 'rotation_quaternion': list(rig.rotation_quaternion),
            'scale': list(rig.scale)}, 'bone_colors_collections_widgets': bones,
            'collections': collections, 'skin_meshes': meshes, 'widgets': widget_rows,
            'materials': materials}


def protected_preview_payload(payload, display):
    """Classify only proved official display outputs after full authentication."""
    result = copy.deepcopy(payload)
    for name, row in display['owned_widgets'].items():
        result['bone_colors_collections_widgets'][name]['widget'] = identity(row['widget'])
    if display['body'] is not None:
        name = display['body']['name']
        owner = {key: display['body'][key] for key in ('name', 'group_key', 'owner', 'profile', 'automatic')}
        for bone in result['bone_colors_collections_widgets'].values():
            bone['collections'] = [collection for collection in bone['collections'] if collection != name]
        for collection in result['collections']:
            if collection['name'] == name:
                collection['bones'] = {'authenticated_mode_output': owner}
    return result


def asset_snapshot(scene, rig, ua):
    data = asset_payload(scene, rig, ua)
    display = authenticated_display_state(rig)
    all_widgets = dict(data['widgets'])
    # Preserve the original raw fingerprint rules. Independently fingerprint
    # every exactly authenticated ring asset even while its binding is None.
    for row in display['owned_widgets'].values():
        obj = row['widget']
        all_widgets[obj.name] = {'mesh': mesh_content(obj) if obj.type == 'MESH' else None,
                                'matrix_basis': [list(value) for value in obj.matrix_basis]}
    additional = {'all_widget_assets': all_widgets,
                  'collection_properties': {c.name: {key: property_content(c[key]) for key in c.keys()}
                                            for c in rig.data.collections_all},
                  'owned_fk_widget_registry': display['fk_registry']}
    protected = protected_preview_payload(data, display)
    protected['widgets'] = all_widgets
    protected.update({key: value for key, value in additional.items() if key != 'all_widget_assets'})
    bones = data['bone_colors_collections_widgets']
    collections = data['collections']
    meshes = data['skin_meshes']
    widgets = all_widgets
    materials = data['materials']
    return {'sha256': digest(data), 'component_sha256': {key: digest(value) for key, value in data.items()},
            'raw_additional_component_sha256': {key: digest(value) for key, value in additional.items()},
            'protected_preview_sha256': digest(protected),
            'protected_preview_component_sha256': {key: digest(value) for key, value in protected.items()},
            'runtime_derived_display': {
                'original_active': display['original_active'], 'body': display['body'],
                'fk_registry_sha256': digest(display['fk_registry']),
                'fk_bindings': {name: {'owned_widget': identity(row['widget']), 'mode': row['mode'],
                                       'temporarily_unbound': row['temporarily_unbound']}
                                for name, row in display['owned_widgets'].items()},
                'active_widget_objects': sorted({pb.custom_shape.name for pb in rig.pose.bones if pb.custom_shape}),
                'all_protected_widget_objects': sorted(widgets)},
            'runtime_generated_outputs': forearm_runtime_output_snapshot(scene, rig),
            'counts': {'bones': len(bones), 'collections': len(collections), 'skin_meshes': len(meshes),
                       'widgets': len(widgets), 'materials': len(materials)},
            'skin_mesh_summary': {name: {'vertices': row['vertices']['count'],
                                        'shape_keys': len(row['shape_keys']),
                                        'weight_influences': row['weights']['influences']}
                                  for name, row in meshes.items()}}


def changes(before, after):
    first, second = dict(before['component_sha256']), dict(after['component_sha256'])
    additional = 'raw_additional_component_sha256'
    if additional in before or additional in after:
        if additional not in before or additional not in after:
            raise AssertionError('Full raw asset comparison requires matching snapshot coverage.')
        first.update(before[additional])
        second.update(after[additional])
    return sorted(key for key in first.keys() | second.keys() if first.get(key) != second.get(key))


def protected_preview_changes(before, after):
    field = 'protected_preview_component_sha256'
    if field not in before or field not in after:
        raise AssertionError('Preview comparison requires freshly authenticated full protected snapshots.')
    return sorted(key for key in before[field].keys() | after[field].keys()
                  if before[field].get(key) != after[field].get(key))
