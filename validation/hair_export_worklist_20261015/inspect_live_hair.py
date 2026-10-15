"""Prepare-only live Hair diagnosis; call run(config) in the verified artist GUI.

Required config: expected_pid (int), artist (absolute .blend path),
candidate_root (this directory's release_07743/character_designer), and report
(a new .json in this directory). Importing this helper does not run diagnosis.
No registration, reload, operators, evaluation, frame change, or save is used.
"""
import ast
import hashlib
import importlib
import importlib.machinery
import json
import marshal
import os
from pathlib import Path
import sys
import time
import types


SCHEMA = 'x.validation.hair-export-live-diagnosis/1'
RECORD = 'character_designer_hair_bones_v1'
PROFILE = 'character_designer_hair_motion_v1'
RIG = 'character_designer_hair_bones_armature'
SESSION = 'character_designer_worklist_main_session_v1'
REFS = 'character_designer_worklist_main_refs_v1'


class Refusal(ValueError):
    pass


def _identity(value):
    if value is None:
        return None
    pointer = getattr(value, 'as_pointer', None)
    result = {'type': type(value).__name__,
              'pointer': int(pointer()) if pointer else id(value)}
    for name in ('name_full', 'name'):
        if hasattr(value, name):
            result[name] = getattr(value, name)
    library = getattr(value, 'library', None)
    if library is not None:
        result['library'] = library.filepath
    return result


def _plain(value):
    # Float hex preserves signed zero and exact native float components.
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, float):
        return {'$float': float(value).hex()}
    if isinstance(value, bytes):
        return {'$bytes': value.hex()}
    mathutils = sys.modules.get('mathutils')
    if mathutils is not None:
        # These native types may implement only the sequence protocol. Do not
        # require __iter__, and do not generalize indexing to arbitrary RNA.
        for name in ('Vector', 'Euler', 'Matrix', 'Quaternion', 'Color'):
            cls = getattr(mathutils, name, None)
            if cls is None or not isinstance(value, cls):
                continue
            if name == 'Matrix':
                rows = tuple(tuple(value[row][column] for column in range(len(value[row])))
                             for row in range(len(value)))
                return {'$mathutils': name, 'dimensions': [len(rows), len(rows[0]) if rows else 0],
                        'rows': _plain(rows)}
            result = {'$mathutils': name,
                      'values': _plain(tuple(value[index] for index in range(len(value))))}
            if name == 'Euler':
                result['order'] = value.order
            return result
    if hasattr(value, 'as_pointer'):
        return {'$native': _identity(value)}
    if hasattr(value, 'items'):
        return {str(key): _plain(item) for key, item in sorted(value.items(), key=lambda row: str(row[0]))}
    to_list = getattr(value, 'to_list', None)
    if callable(to_list):
        return _plain(to_list())
    if hasattr(value, '__iter__'):
        return [_plain(item) for item in value]
    raise TypeError('Unsupported protected-state value: ' + type(value).__name__)


def _digest(value):
    raw = json.dumps(_plain(value), ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _rows(values):
    digest, count = hashlib.sha256(), 0
    for value in values:
        encoded = json.dumps(_plain(value), ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        digest.update(len(encoded).to_bytes(8, 'little'))
        digest.update(encoded)
        count += 1
    return {'count': count, 'sha256': digest.hexdigest()}


def _props(owner):
    try:
        return dict(owner.items())
    except TypeError:
        # Some RNA structs (for example KeyBlocks) cannot hold ID properties.
        return {'$custom_properties_unsupported': type(owner).__name__}


def _fields(owner, names):
    return {name: getattr(owner, name) for name in names if hasattr(owner, name)}


def _matrix(value):
    return [list(row) for row in value]


def _handlers(bpy):
    result = {}
    for name in dir(bpy.app.handlers):
        value = getattr(bpy.app.handlers, name)
        if isinstance(value, list):
            result[name] = {'list_identity': id(value), 'callbacks': [
                {'identity': id(callback), 'module': getattr(callback, '__module__', None),
                 'qualname': getattr(callback, '__qualname__', type(callback).__name__)}
                for callback in value]}
    return result


def _id_inventory(bpy):
    result = {}
    for prop in bpy.data.bl_rna.properties:
        if prop.type != 'COLLECTION':
            continue
        values = getattr(bpy.data, prop.identifier)
        result[prop.identifier] = _rows(
            (_identity(value), _fields(value, ('users', 'use_fake_user', 'is_embedded_data')))
            for value in sorted(values, key=lambda item: item.as_pointer()))
    return result


def _context(bpy):
    context = bpy.context
    result = {'filepath': bpy.data.filepath, 'dirty': bool(bpy.data.is_dirty),
              'mode': context.mode,
              'current': {name: _identity(getattr(context, name, None)) for name in
                          ('scene', 'view_layer', 'workspace', 'window', 'screen',
                           'area', 'region', 'object', 'active_object', 'active_bone',
                           'active_pose_bone')},
              'selected': sorted((_identity(value) for value in context.selected_objects),
                                 key=lambda item: item['pointer']),
              'object_modes': [(value.as_pointer(), value.mode) for value in bpy.data.objects],
              'scenes': [], 'windows': []}
    for scene in bpy.data.scenes:
        result['scenes'].append({'scene': _identity(scene),
            'frame': scene.frame_current, 'subframe': scene.frame_subframe,
            'layers': [{'layer': _identity(layer), 'active': _identity(layer.objects.active),
                        'selected': [obj.as_pointer() for obj in layer.objects
                                     if obj.select_get(view_layer=layer)]}
                       for layer in scene.view_layers]})
    for manager in bpy.data.window_managers:
        for window in manager.windows:
            result['windows'].append({name: _identity(getattr(window, name)) for name in
                                      ('scene', 'view_layer', 'workspace', 'screen')})
    return result


def _animation(owner):
    data = owner.animation_data
    if data is None:
        return None
    return {'action': _identity(data.action),
            'settings': _fields(data, ('action_slot_handle', 'action_blend_type',
                'action_extrapolation', 'action_influence', 'use_nla')),
            'drivers': _rows((curve.data_path, curve.array_index, curve.mute,
                curve.driver.type, curve.driver.expression,
                [(variable.name, variable.type,
                  [(_identity(target.id), _fields(target, ('data_path', 'bone_target',
                    'transform_type', 'transform_space', 'rotation_mode')))
                   for target in variable.targets]) for variable in curve.driver.variables])
                for curve in data.drivers),
            'nla': _rows((track.name, track.mute, track.is_solo,
                [(strip.name, _identity(strip.action), _fields(strip, ('frame_start',
                    'frame_end', 'action_frame_start', 'action_frame_end', 'blend_type',
                    'extrapolation', 'influence', 'mute', 'repeat', 'scale')))
                 for strip in track.strips]) for track in data.nla_tracks)}


def _hair_state(source):
    mesh, keys = source.data, source.data.shape_keys
    result = {'source': _identity(source), 'mesh': _identity(mesh),
        'source_properties': _digest(_props(source)), 'mesh_properties': _digest(_props(mesh)),
        'transform': _digest({'parent': _identity(source.parent),
            **_fields(source, ('parent_type', 'parent_bone', 'active_shape_key_index',
                              'show_only_shape_key', 'use_shape_key_edit_mode')),
            'basis': _matrix(source.matrix_basis), 'inverse': _matrix(source.matrix_parent_inverse)}),
        'groups': _rows((group.index, group.name, group.lock_weight) for group in source.vertex_groups),
        'vertices': _rows((vertex.index, tuple(vertex.co), vertex.hide, vertex.select,
                          [(member.group, member.weight) for member in vertex.groups])
                         for vertex in mesh.vertices),
        'edges': _rows((edge.index, tuple(edge.vertices),
                       _fields(edge, ('hide', 'select', 'use_seam', 'use_edge_sharp')))
                      for edge in mesh.edges),
        'faces': _rows((face.index, tuple(face.vertices),
                       _fields(face, ('hide', 'select', 'material_index', 'use_smooth')))
                      for face in mesh.polygons),
        'loops': _rows((loop.vertex_index, loop.edge_index) for loop in mesh.loops),
        'animation': _digest(_animation(source)), 'keys': None}
    if keys is not None:
        result['keys'] = {'id': _identity(keys), 'properties': _digest(_props(keys)),
            'settings': _fields(keys, ('use_relative', 'eval_time')),
            'reference': _identity(keys.reference_key), 'animation': _digest(_animation(keys)),
            'blocks': [{'id': _identity(block), 'relative': _identity(block.relative_key),
                'properties': _digest(_props(block)),
                'settings': _fields(block, ('value', 'mute', 'slider_min', 'slider_max',
                                            'interpolation', 'vertex_group', 'frame')),
                'points': _rows(tuple(point.co) for point in block.data)}
                for block in keys.key_blocks]}
    return result


def _rest_row(bone):
    return {'id': _identity(bone), 'parent': _identity(bone.parent),
        'head': list(bone.head_local), 'tail': list(bone.tail_local),
        'matrix': _matrix(bone.matrix_local), 'properties': _props(bone),
        **_fields(bone, ('use_connect', 'use_deform', 'inherit_scale',
            'use_inherit_rotation', 'use_local_location', 'use_relative_parent',
            'select', 'select_head', 'select_tail', 'hide', 'hide_select'))}


def _rig_state(bpy, rig):
    # Only this authority and its raw recovery Armature dependencies are read.
    # Native ID inventory separately protects addition/removal of unrelated IDs.
    related = {rig.data.as_pointer(): rig.data}
    references = rig.get(REFS, {})
    for value in references.values():
        if isinstance(value, bpy.types.Armature):
            related[value.as_pointer()] = value
    data = [{'id': _identity(armature), 'properties': _digest(_props(armature)),
             'active': _identity(armature.bones.active),
             'rest': _rows(_rest_row(bone) for bone in armature.bones)}
            for armature in sorted(related.values(), key=lambda value: value.as_pointer())]
    objects = []
    for obj in (rig,):
        objects.append({'id': _identity(obj), 'data': _identity(obj.data),
            'properties': _digest(_props(obj)), 'animation': _digest(_animation(obj)),
            'basis': _digest(_matrix(obj.matrix_basis)),
            'pose': _rows({'name': bone.name, 'properties': _props(bone),
                'basis': _matrix(bone.matrix_basis),
                **_fields(bone, ('location', 'rotation_mode', 'rotation_euler',
                    'rotation_quaternion', 'rotation_axis_angle', 'scale',
                    'lock_location', 'lock_rotation', 'lock_scale', 'lock_rotation_w',
                    'lock_rotations_4d')),
                'constraints': [(constraint.name, constraint.type,
                    _fields(constraint, ('mute', 'influence', 'subtarget', 'pole_subtarget')),
                    _identity(getattr(constraint, 'target', None)),
                    _identity(getattr(constraint, 'pole_target', None)))
                    for constraint in bone.constraints]} for bone in obj.pose.bones)})
    return {'armatures': data, 'objects': objects}


def _snapshot(bpy, source):
    domains = {'context': _context(bpy), 'handlers': _handlers(bpy),
               'native_id_inventory': _id_inventory(bpy),
               'hair': _hair_state(source), 'rigs': _rig_state(bpy, source[RIG])}
    hashes = {name: _digest(value) for name, value in domains.items()}
    return {'sha256': _digest(hashes), 'domains': hashes,
            'counts': {'hair_vertices': len(source.data.vertices),
                       'hair_groups': len(source.vertex_groups),
                       'hair_shape_keys': len(source.data.shape_keys.key_blocks)
                            if source.data.shape_keys else 0,
                       'protected_armatures': len(domains['rigs']['armatures']),
                       'rig_objects': len(domains['rigs']['objects'])},
            'context': {'filepath': bpy.data.filepath, 'dirty': bool(bpy.data.is_dirty),
                        'mode': bpy.context.mode, 'scene': bpy.context.scene.name,
                        'frame': bpy.context.scene.frame_current,
                        'subframe': bpy.context.scene.frame_subframe}}


def _error(exc):
    return {'ok': False, 'error_type': type(exc).__name__, 'error': str(exc)}


def _module_info(module):
    path = getattr(module, '__file__', None)
    function = getattr(module, 'read', None)
    code = getattr(function, '__code__', None)
    result = {'name': module.__name__, 'file': path,
              'read_code_sha256': hashlib.sha256(marshal.dumps(code)).hexdigest() if code else None}
    try:
        result['disk_source_sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest() \
                                      if path and Path(path).is_file() else None
    except OSError as exc:
        result['disk_source_error'] = str(exc)
    return result


def _registry_result(module, source):
    try:
        data = module.read(source, validate=True)
        if data is None:
            raise Refusal('The source has no saved Hair registry.')
        return {'ok': True, 'sha256': _digest(data), 'source_uid': data['source_uid'],
                'topology': data['topology'], 'strands': len(data['strands']),
                'bones': sum(len(strand['bones']) for strand in data['strands'])}
    except Exception as exc:
        return _error(exc)


def _live_registry():
    candidates = [module for name, module in tuple(sys.modules.items())
        if (name == 'character_designer.hair_strand_registry'
            or name.endswith('.character_designer.hair_strand_registry'))
        and module is not None]
    unique = {id(module): module for module in candidates}
    if len(unique) != 1:
        raise Refusal('Expected one already-loaded live Hair registry; found ' + str(len(unique)))
    return next(iter(unique.values()))


def _resolve_ref(node, references):
    if not isinstance(node, dict) or set(node) != {'$id'}:
        raise Refusal('The recovery native ID reference is malformed.')
    value = references.get(node['$id'])
    if value is None:
        raise Refusal('The recovery native ID reference is missing: ' + str(node['$id']))
    return value


def _authored_data(rig):
    if rig.get(SESSION) is None:
        return rig.data, {'adopted': False}
    record = json.loads(rig[SESSION])
    references = rig.get(REFS, {})
    authored = _resolve_ref(record['capture']['targets'][0]['data'], references)
    motion = _resolve_ref(record['motion_data'], references)
    return authored, {'adopted': True, 'authored_data': _identity(authored),
        'motion_data': _identity(motion), 'live_data': _identity(rig.data),
        'live_is_motion': rig.data is motion, 'live_is_authored': rig.data is authored,
        'session_sha256': _digest(rig[SESSION]), 'raw_refs_sha256': _digest(references)}


def _chain_flags(source, rig, authored):
    record = json.loads(source[RECORD])
    counts = {'chains': len(record['chains']), 'bones': 0, 'binding_connected': 0,
        'live_connected': 0, 'authored_connected': 0,
        'live_binding_mismatches': 0, 'authored_binding_mismatches': 0,
        'missing_live': 0, 'missing_authored': 0}
    for chain in record['chains']:
        if len(chain['bones']) != len(chain['rest']) or len(chain['bones']) != chain['count']:
            raise Refusal('The saved Hair chain has inconsistent bone/rest/count inventory.')
        owned = [bone for bone in rig.data.bones
            if bone.get('character_designer_hair_bones_source') == source
            and bone.get('character_designer_hair_bones_signature') == chain['signature']]
        names = {bone.name for bone in owned}
        roots = [bone for bone in owned if bone.parent is None or bone.parent.name not in names]
        if len(roots) != 1 or len(owned) != chain['count']:
            raise Refusal('Cannot count flags: owned Hair chain inventory/root is not exact.')
        ordered, current = [], roots[0]
        while current is not None:
            ordered.append(current)
            children = [bone for bone in owned if bone.parent == current]
            if len(children) > 1:
                raise Refusal('Cannot count flags: owned Hair chain is branched.')
            current = children[0] if children else None
        if len(ordered) != len(owned):
            raise Refusal('Cannot count flags: owned Hair chain is disconnected.')
        for live_bone, saved in zip(ordered, chain['rest']):
            name = live_bone.name
            counts['bones'] += 1
            expected = bool(saved['connected'])
            counts['binding_connected'] += int(expected)
            for label, data in (('live', rig.data), ('authored', authored)):
                bone = data.bones.get(name)
                if bone is None:
                    counts['missing_' + label] += 1
                    continue
                actual = bool(bone.use_connect)
                counts[label + '_connected'] += int(actual)
                counts[label + '_binding_mismatches'] += int(actual != expected)
    return counts


def _preflight(config, bpy):
    base = Path(__file__).resolve().parent
    if type(config.get('expected_pid')) is not int or os.getpid() != config['expected_pid']:
        raise Refusal('PID does not match expected_pid.')
    if bpy.app.background:
        raise Refusal('Background Blender is not the artist GUI.')
    if any(screen.is_animation_playing for screen in bpy.data.screens):
        raise Refusal('Animation is playing; diagnosis will not stop playback.')
    if bpy.context.mode.startswith('EDIT') or any(obj.mode == 'EDIT' for obj in bpy.data.objects):
        raise Refusal('Edit Mode is active; diagnosis will not change mode.')
    artist = Path(config['artist'])
    if not artist.is_absolute() or artist.suffix.lower() != '.blend' or not artist.is_file():
        raise Refusal('artist must identify an existing absolute artist .blend path.')
    if not bpy.data.filepath or Path(bpy.data.filepath).resolve() != artist.resolve():
        raise Refusal('The current artist filepath differs from config.artist.')
    candidate = Path(config['candidate_root'])
    allowed = base / 'release_07743' / 'character_designer'
    if not candidate.is_absolute() or candidate.resolve() != allowed.resolve() or not candidate.is_dir():
        raise Refusal('candidate_root must be this diagnostic directory release_07743/character_designer.')
    tree = ast.parse((candidate / '__init__.py').read_text(encoding='utf-8-sig'))
    infos = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in node.targets)]
    if len(infos) != 1 or tuple(infos[0].get('version', ())) != (0, 77, 43):
        raise Refusal('The frozen candidate bl_info version must be 0.77.43.')
    if bpy.context.scene is None:
        raise Refusal('There is no current artist Scene context.')
    sources = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and PROFILE in obj]
    if len(sources) != 1:
        raise Refusal('Expected exactly one configured Hair source; found ' + str(len(sources)))
    source, = sources
    rig = source.get(RIG)
    if rig is None or not isinstance(rig, bpy.types.Object) or rig.type != 'ARMATURE':
        raise Refusal('The configured Hair authoritative rig is missing.')
    return candidate, infos[0], source, rig


def run(config):
    """Read current proof and an isolated candidate; write one exclusive report.

    On any protected-state mismatch this reports the evidence and performs no
    scene/handler repair. Caller must review the report before further action.
    """
    import bpy
    report = Path(config['report'])
    base = Path(__file__).resolve().parent
    if (not report.is_absolute() or report.parent.resolve() != base
            or report.suffix.lower() != '.json' or report.is_symlink()):
        raise Refusal('report must be a new absolute .json path in the diagnostic directory.')
    # Reserve exclusively before native reads or candidate imports.
    with report.open('x', encoding='utf-8', newline='\n') as stream:
        result = {'schema': SCHEMA, 'pid': os.getpid(), 'status': 'refused',
            'blender': {'version': bpy.app.version_string, 'binary': bpy.app.binary_path},
            'limits': [
                'Hashes compare the explicitly captured native state; they cannot prove absence of every host-side effect.',
                'Blender timers, GPU callbacks and Python module-internal caches are not exhaustively enumerable here.',
                'Loaded function bytecode and on-disk source are recorded separately; a disk hash is not a loaded-source proof.',
                'No scene evaluation, mode/frame change, registration, save, repair or restoration is performed.']}
        source = None
        before_modules, before_path = dict(sys.modules), list(sys.path)
        before_meta_path = tuple(sys.meta_path)
        before_bytecode = sys.dont_write_bytecode
        namespace = '_x_hair_diagnosis_' + str(os.getpid()) + '_' + str(time.time_ns())
        candidate = None
        try:
            candidate, info, source, rig = _preflight(config, bpy)
            result['preflight'] = {'ok': True, 'artist': str(Path(config['artist']).resolve()),
                                   'candidate_root': str(candidate), 'candidate_version': info['version']}
            result['identities'] = {'hair': _identity(source), 'mesh': _identity(source.data),
                                    'authority_rig': _identity(rig), 'live_data': _identity(rig.data)}
            result['before'] = _snapshot(bpy, source)
            try:
                authored, result['adoption'] = _authored_data(rig)
                result['chain_flags'] = _chain_flags(source, rig, authored)
            except Exception as exc:
                result['adoption'] = _error(exc)
            try:
                live = _live_registry()
                result['live_module'] = _module_info(live)
                live_package = sys.modules.get(live.__package__)
                result['live_package'] = {'name': live.__package__,
                    'file': getattr(live_package, '__file__', None),
                    'bl_info': getattr(live_package, 'bl_info', None)}
                result['live_registry'] = _registry_result(live, source)
            except Exception as exc:
                result['live_registry'] = _error(exc)
            # Do not execute the package __init__, reload the live add-on, or
            # create __pycache__ inside the frozen source tree.
            if namespace in sys.modules:
                raise Refusal('Private diagnostic namespace unexpectedly already exists.')
            package = types.ModuleType(namespace)
            package.__path__ = [str(candidate)]
            package.__package__ = namespace
            package.__file__ = str(candidate / '__init__.py')
            package.__spec__ = importlib.machinery.ModuleSpec(namespace, loader=None, is_package=True)
            package.__spec__.submodule_search_locations = list(package.__path__)
            package.bl_info = info
            sys.modules[namespace] = package
            sys.dont_write_bytecode = True
            private = importlib.import_module(namespace + '.hair_strand_registry')
            result['candidate_module'] = _module_info(private)
            result['candidate_registry'] = _registry_result(private, source)
            target = sys.modules.get(namespace + '.animation_worklist_target')
            if target is not None:
                try:
                    view = target.control_rest_view(rig)
                    result['adoption_proof'] = {'ok': True, 'view_available': view is not None,
                        'authored_data': _identity(view.original_data) if view else None,
                        'motion_data': _identity(view.motion_data) if view else None,
                        'source_bones': len(view.names) if view else 0}
                except Exception as exc:
                    result['adoption_proof'] = _error(exc)
            else:
                result['adoption_proof'] = {'ok': True, 'view_available': False,
                    'note': 'No managed Rest proof module was imported by the candidate.'}
            result['status'] = 'diagnosed'
        except Exception as exc:
            result['failure'] = _error(exc)
        finally:
            introduced = {name: module for name, module in tuple(sys.modules.items())
                          if name not in before_modules}
            owned = {name: module for name, module in introduced.items()
                     if name == namespace or name.startswith(namespace + '.')}
            result['private_imports'] = [_module_info(module) for name, module in sorted(owned.items())
                                         if module is not None]
            removed = []
            for name, module in sorted(owned.items(), key=lambda row: len(row[0]), reverse=True):
                if sys.modules.get(name) is module:
                    del sys.modules[name]
                    removed.append(name)
            path_changed = sys.path != before_path
            if path_changed:
                sys.path[:] = before_path
            sys.dont_write_bytecode = before_bytecode
            remaining = [name for name in sys.modules if name == namespace or name.startswith(namespace + '.')]
            result['cleanup'] = {'owned_added': len(owned), 'owned_removed': len(removed),
                'owned_remaining': remaining, 'sys_path_changed_during_read': path_changed,
                'sys_path_restored': sys.path == before_path,
                'meta_path_unchanged': tuple(sys.meta_path) == before_meta_path,
                'bytecode_flag_restored': sys.dont_write_bytecode == before_bytecode,
                'existing_module_identities_unchanged': all(sys.modules.get(name) is module
                    for name, module in before_modules.items()),
                'external_modules_added': sorted(name for name in introduced if name not in owned)}
            if source is not None and 'before' in result:
                try:
                    result['after'] = _snapshot(bpy, source)
                    result['protected_state_unchanged'] = result['before'] == result['after']
                    result['changed_domains'] = [name for name, value in result['before']['domains'].items()
                        if result['after']['domains'].get(name) != value]
                except Exception as exc:
                    result['after'] = _error(exc)
                    result['protected_state_unchanged'] = False
                if not result['protected_state_unchanged']:
                    result['status'] = 'protected_state_mismatch_no_repair'
            clean = result['cleanup']
            if (clean['owned_remaining'] or not clean['sys_path_restored']
                    or not clean['meta_path_unchanged'] or not clean['bytecode_flag_restored']
                    or not clean['existing_module_identities_unchanged']):
                result['status'] = 'cleanup_or_import_identity_mismatch_no_repair'
            result['candidate_side_effect_proof'] = {
                'covered_native_state_unchanged': result.get('protected_state_unchanged'),
                'absolute_zero_side_effects_proven': False,
                'limitation': 'Import dependencies may initialize non-enumerable caches or timers; no corrective action was attempted.'}
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    return {'schema': SCHEMA, 'report': str(report), 'status': result['status'],
            'protected_state_unchanged': result.get('protected_state_unchanged'),
            'live_registry': result.get('live_registry'),
            'candidate_registry': result.get('candidate_registry'),
            'failure': result.get('failure')}
