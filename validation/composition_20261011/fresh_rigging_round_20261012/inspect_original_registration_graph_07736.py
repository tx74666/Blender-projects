"""One read-only in-process diagnostic; no CD imports or runtime callbacks."""
import gc
import hashlib
import json
import math
import os
import sys
import types
from collections import deque
from pathlib import Path

import bpy

ROUND = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012')
OUTPUT = ROUND / 'original_runtime_registration_graph_01'
MANIFEST = ROUND / 'package_c1e59f7f/python_projection.json'
MANIFEST_SHA = 'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'

def require(value, message):
    if not value:
        raise RuntimeError(message)

def source_pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def cd_name(name):
    return isinstance(name, str) and (name == 'character_designer' or name.startswith('character_designer.'))

def id_ref(value):
    if value is None:
        return None
    return {'type': value.bl_rna.identifier, 'name': value.name,
            'pointer': value.as_pointer(), 'python_id': id(value),
            'library': value.library.filepath if value.library else None}

def plain(value, depth=0):
    require(depth <= 24, 'Read-only raw value depth exceeded.')
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return {'float_hex': value.hex(), 'finite': math.isfinite(value)}
    if isinstance(value, bpy.types.ID):
        return {'native_id': id_ref(value)}
    if hasattr(value, 'items'):
        return {str(k): plain(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return {'set': sorted((plain(v, depth + 1) for v in value), key=lambda v: json.dumps(v, sort_keys=True))}
    # Blender mathutils values implement the sequence protocol without __iter__.
    count = len(value)
    require(count <= 100000, 'Read-only raw sequence too large.')
    return [plain(value[index], depth + 1) for index in range(count)]

def rna_group(value, depth=0):
    require(depth <= 12, 'Read-only PropertyGroup depth exceeded.')
    result = {}
    for prop in value.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type':
            continue
        actual = getattr(value, name)
        if prop.type == 'COLLECTION':
            require(len(actual) <= 10000, 'Read-only PropertyGroup collection too large.')
            result[name] = [rna_group(row, depth + 1) for row in actual]
        elif prop.type == 'POINTER' and isinstance(actual, bpy.types.PropertyGroup):
            result[name] = rna_group(actual, depth + 1)
        else:
            result[name] = plain(actual)
    try:
        result['$custom_properties'] = plain(dict(value.items()))
    except TypeError as error:
        result['$custom_properties_unsupported'] = str(error)
    return result

def attempt(operation):
    try:
        return {'known': True, 'value': operation()}
    except Exception as error:
        return {'known': False, 'error': type(error).__name__ + ': ' + str(error)}

def function(value):
    if isinstance(value, (staticmethod, classmethod)):
        value = value.__func__
    if isinstance(value, types.MethodType):
        value = value.__func__
    return value if isinstance(value, types.FunctionType) else None

require(os.getpid() == 14500 and not bpy.app.background, 'Wrong original process.')
require(Path(bpy.data.filepath).resolve() == Path(r'D:/Blender/Projects/Character/X/X.blend').resolve(), 'Wrong artist file.')
require(source_pin(MANIFEST)['sha256'] == MANIFEST_SHA, 'Frozen manifest changed.')
require(not OUTPUT.exists(), 'Do not overwrite a previous diagnostic.')
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
root_class = bpy.types.CHARACTERDESIGNER_PT_main
root_globals = root_class.draw.__globals__
require(root_globals.get('__name__') == 'character_designer' and root_globals['bl_info']['version'] == (0, 77, 36), 'Unexpected registered root namespace.')
before = {'dirty': bool(bpy.data.is_dirty), 'filepath': bpy.data.filepath,
          'scene_pointer': bpy.context.scene.as_pointer(), 'active_object': id_ref(bpy.context.view_layer.objects.active)}
# No heap walk. The single direct-referrer query is limited to the known root dict.
root_modules = [obj for obj in gc.get_referrers(root_globals)
                if isinstance(obj, types.ModuleType) and vars(obj) is root_globals]
queue = deque([(root_globals, 'registered PT_main.draw')])
spaces, actual_spaces, modules, edges, aliases = {}, {}, {}, [], {}
inspected_closures = set()

def enqueue(namespace, origin):
    if cd_name(namespace.get('__name__')) and id(namespace) not in spaces:
        queue.append((namespace, origin))

def inspect_value(value, origin, source_namespace):
    if isinstance(value, types.ModuleType) and cd_name(value.__name__):
        namespace = vars(value)
        modules[id(value)] = {'id': id(value), 'name': value.__name__, 'globals_id': id(namespace),
            'file': namespace.get('__file__'), 'same_as_sys_modules': sys.modules.get(value.__name__) is value}
        edges.append({'from_globals': source_namespace, 'attribute': origin, 'module_id': id(value), 'to_globals': id(namespace)})
        enqueue(namespace, origin)
    fn = function(value)
    if fn is not None and cd_name(fn.__globals__.get('__name__')):
        enqueue(fn.__globals__, origin)
        if source_namespace == id(root_globals) or 'register' in origin or 'stop_' in origin:
            aliases[str(source_namespace) + ':' + origin] = {
                'function_id': id(fn), 'name': fn.__qualname__, 'module': fn.__module__,
                'globals_id': id(fn.__globals__), 'globals_file': fn.__globals__.get('__file__'),
                'code_file': fn.__code__.co_filename}
        if id(fn) in inspected_closures:
            return
        inspected_closures.add(id(fn))
        for index, cell in enumerate(fn.__closure__ or ()):
            try:
                closed = cell.cell_contents
            except ValueError:
                continue
            if isinstance(closed, types.ModuleType) or function(closed) is not None:
                inspect_value(closed, origin + '.closure[' + str(index) + ']', source_namespace)

for module in root_modules:
    inspect_value(module, 'gc direct root module', id(root_globals))
while queue:
    namespace, origin = queue.popleft()
    if id(namespace) in spaces:
        continue
    require(len(spaces) < 512, 'Module graph exceeds narrow CD bound.')
    row = {'globals_id': id(namespace), 'name': namespace.get('__name__'),
           'file': namespace.get('__file__'), 'discovered_from': origin}
    spaces[id(namespace)] = row
    actual_spaces[id(namespace)] = namespace
    if row['file']:
        row['source'] = attempt(lambda p=row['file']: source_pin(p))
        relative = '__init__.py' if row['name'] == 'character_designer' else row['name'][len('character_designer.'):].replace('.', '/') + '.py'
        row['frozen_sha256'] = manifest['files'].get(relative)
        row['matches_frozen_source'] = row['source']['known'] and row['source']['value']['sha256'] == row['frozen_sha256']
    for key, value in tuple(namespace.items()):
        inspect_value(value, key, id(namespace))
        if isinstance(value, type) and cd_name(getattr(value, '__module__', None)):
            for method_name, method in tuple(vars(value).items()):
                inspect_value(method, key + '.' + method_name, id(namespace))

def fn_record(value):
    fn = function(value)
    if fn is None:
        return {'type': type(value).__name__, 'python_id': id(value)}
    cells = []
    for index, cell in enumerate(fn.__closure__ or ()):
        try:
            item = cell.cell_contents
            cells.append({'index': index, 'type': type(item).__name__, 'python_id': id(item),
                'module': getattr(item, '__module__', None), 'name': getattr(item, '__name__', None),
                'globals_id': id(item.__globals__) if isinstance(item, types.FunctionType) else None,
                'scalar': plain(item) if type(item) in (str, bool, int, float, type(None)) else None})
        except ValueError:
            cells.append({'index': index, 'empty': True})
    return {'python_id': id(fn), 'module': fn.__module__, 'name': fn.__qualname__,
        'code_file': fn.__code__.co_filename, 'globals_id': id(fn.__globals__),
        'globals_in_registered_root_graph': id(fn.__globals__) in spaces, 'closure': cells}

classes = []
for cls in root_globals['CLASSES']:
    identifier = cls.__name__
    base = next((base for base in (bpy.types.Operator, bpy.types.Panel, bpy.types.PropertyGroup, bpy.types.UIList) if issubclass(cls, base)), None)
    if base is bpy.types.Operator:
        prefix, name = cls.bl_idname.split('.', 1)
        identifier = prefix.upper() + '_OT_' + name
    elif base is bpy.types.Panel:
        identifier = cls.bl_idname or cls.__name__
    actual = base.bl_rna_get_subclass_py(identifier) if base is not None else None
    classes.append({'name': cls.__name__, 'identifier': identifier, 'module': cls.__module__,
        'python_id': id(cls), 'actual_python_id': id(actual) if actual else None,
        'registered': bool(getattr(cls, 'is_registered', False)), 'actual_same': actual is cls,
        'methods': {name: fn_record(method) for name, method in vars(cls).items() if function(method) is not None}})
pointer_types = []
for owner, name, expected in [(bpy.types.WindowManager, name, cls) for name, cls in root_globals['_WINDOW_MANAGER_POINTER_TYPES']] + [
        (bpy.types.Scene, 'character_designer_setup', root_globals['CharacterDesignerSetup']),
        (bpy.types.Scene, 'character_designer_animation_worklist', root_globals['CharacterDesignerAnimationWorklistState']),
        (bpy.types.Object, 'character_designer_unity_export', root_globals['CharacterDesignerUnityExport'])]:
    prop = owner.bl_rna.properties.get(name)
    fixed = getattr(prop, 'fixed_type', None)
    pointer_types.append({'owner': owner.__name__, 'name': name, 'expected_class_id': id(expected),
        'actual_type': getattr(prop, 'type', None), 'fixed_identifier': getattr(fixed, 'identifier', None),
        'exact_fixed_type': fixed == expected.bl_rna})
handlers = {}
for name in dir(bpy.app.handlers):
    collection = getattr(bpy.app.handlers, name)
    if isinstance(collection, list):
        rows = [fn_record(fn) for fn in collection if cd_name(getattr(fn, '__module__', None))]
        if rows:
            handlers[name] = rows
timers = []
seen_functions = set()
for namespace in actual_spaces.values():
    for name, value in tuple(namespace.items()):
        fn = function(value)
        if fn is not None and id(fn) not in seen_functions:
            seen_functions.add(id(fn))
            if bpy.app.timers.is_registered(fn):
                timers.append({'namespace_id': id(namespace), 'name': name, **fn_record(fn)})
scene_rows = {scene.name: {'identity': id_ref(scene), 'custom_properties': attempt(lambda s=scene: plain(dict(s.items()))),
    'clock': [scene.frame_current, scene.frame_subframe, scene.frame_start, scene.frame_end],
    'properties': {prop.identifier: attempt(lambda s=scene, n=prop.identifier: rna_group(getattr(s, n)))
                   for prop in bpy.types.Scene.bl_rna.properties if prop.identifier.startswith('character_designer')}} for scene in bpy.data.scenes}
wm_rows = {str(wm.as_pointer()): {'identity': id_ref(wm),
    'properties': {prop.identifier: attempt(lambda w=wm, n=prop.identifier: rna_group(getattr(w, n)))
                   for prop in bpy.types.WindowManager.bl_rna.properties if prop.identifier.startswith('character_designer')}} for wm in bpy.data.window_managers}
actions = [{'identity': id_ref(action), 'users': action.users, 'fake_user': action.use_fake_user,
    'custom_properties': attempt(lambda a=action: plain(dict(a.items()))),
    'slots': [{'handle': slot.handle, 'identifier': slot.identifier, 'target_id_type': slot.target_id_type} for slot in action.slots]} for action in bpy.data.actions]
after = {'dirty': bool(bpy.data.is_dirty), 'filepath': bpy.data.filepath,
         'scene_pointer': bpy.context.scene.as_pointer(), 'active_object': id_ref(bpy.context.view_layer.objects.active)}
report = {'schema': 'x.diagnostic.original-registration-graph/1', 'diagnostic_completed': True,
    'semantic_preservation_pass_claimed': False, 'source': source_pin(__file__), 'pid': os.getpid(),
    'root_globals_id': id(root_globals), 'root_module_object_found': bool(root_modules),
    'root_module_objects': [modules[id(module)] for module in root_modules],
    'function_globals_not_replaced': True, 'modules': list(modules.values()), 'namespaces': list(spaces.values()),
    'module_edges': edges, 'root_and_lifecycle_function_aliases': aliases,
    'RNA_classes': classes, 'pointer_types': pointer_types, 'handlers': handlers,
    'graph_known_registered_timers': timers, 'timer_enumeration_complete_claimed': False,
    'before': before, 'after': after, 'cheap_context_equal': before == after,
    'raw_scene_snapshot': scene_rows, 'raw_window_manager_snapshot': wm_rows, 'Action_metadata_snapshot': actions,
    'full_Action_motion_or_geometry_scanned': False, 'registered_or_unregistered': False,
    'imported_CD_modules_or_called_runtime_functions': False, 'scene_mutation_or_file_save_performed': False}
OUTPUT.mkdir()
with (OUTPUT / 'report.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps({'report': str(OUTPUT / 'report.json'), 'root_module_object_found': bool(root_modules),
    'namespace_count': len(spaces), 'module_count': len(modules), 'class_count': len(classes)}, ensure_ascii=False), flush=True)
