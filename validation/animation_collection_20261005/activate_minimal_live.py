"""Reviewed, explicit 0.76.2 -> 0.76.3 animation-only hot activation.

This file defines ``run`` and does nothing on import. It never calls Save,
Refresh, open_mainfile, addon register/unregister, an animation operator, or a
PropertyGroup register/unregister. Only four new Operators and six new RNA
fields are registered. Existing registered Python classes retain their identity.

Use the same file on a saved worklist fixture in background Blender first. GUI
use requires both a successful fixture report and an injected-failure rollback
report with this exact script/inventory hash. This is a local, bounded migration,
not a general add-on reload. A failed preservation/rollback check is a blocker.
"""

import ast
from copy import deepcopy
import datetime
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback
import zipfile

import bpy


BASE_SHA256 = 'f3b00d2e92fa9954d7816aff9ff7bb099b06395cafffa5e274e1d69b6006f9e7'
FROM_VERSION = (0, 76, 2)
TO_VERSION = (0, 76, 3)
DELTA = frozenset(('__init__.py', 'animation.py', 'animation_link_source.py', 'animation_worklist.py',
                   'animation_worklist_collection.py', 'animation_worklist_fingerprint.py',
                   'animation_worklist_queue.py', 'animation_worklist_ui.py'))
NEW_MODULES = ('animation_worklist_queue', 'animation_worklist_fingerprint',
               'animation_worklist_collection')
NEW_OPERATORS = (
    'CHARACTERDESIGNER_OT_worklist_add_ready',
    'CHARACTERDESIGNER_OT_worklist_scan_changes',
    'CHARACTERDESIGNER_OT_worklist_sync_changed',
    'CHARACTERDESIGNER_OT_worklist_cancel_collection',
)
NEW_FIELDS = {
    'CharacterDesignerAnimationWorklistItem': frozenset((
        'last_synced_receipt', 'scan_state', 'scan_reason', 'sync_selected')),
    'CharacterDesignerAnimationWorklistState': frozenset(('collection_status', 'scan_completed')),
}
ANIMATION_FUNCTIONS = ('stop_animation_runtime', '_poll_action_export', '_link_idle')
MAIN_FIELDS = ('CLASSES', 'WORKLIST_CLASSES', 'stop_worklist_ui', 'bl_info',
               'ADDON_LOADED_SIGNATURE', 'ADDON_REFRESH_LAST_STATE', 'ADDON_REFRESH_LAST_ERROR')
_MISSING = object()
FOLDER = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def identity(value):
    if value is None:
        return None
    return (value.bl_rna.identifier, value.as_pointer(),
            getattr(value, 'name', None), getattr(getattr(value, 'library', None), 'filepath', None))


def plain(value, depth=0):
    require(depth <= 32, 'Saved native values exceed the bounded snapshot depth.')
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, bpy.types.ID):
        return identity(value)
    if isinstance(value, bpy.types.PropertyGroup):
        return pg_snapshot(value, depth + 1)
    if isinstance(value, (set, frozenset)):
        return sorted(plain(item, depth + 1) for item in value)
    items = getattr(value, 'items', None)
    if callable(items):
        return {str(key): plain(item, depth + 1) for key, item in items()}
    to_list = getattr(value, 'to_list', None)
    if callable(to_list):
        return plain(to_list(), depth + 1)
    try:
        iterator = iter(value)  # Native mathutils sequences can omit __iter__.
    except TypeError as exc:
        raise RuntimeError('Cannot prove saved native value: ' + type(value).__name__) from exc
    return [plain(item, depth + 1) for item in iterator]


def pg_snapshot(group, depth=0):
    require(depth <= 32, 'PropertyGroup snapshot exceeds the bounded depth.')
    ignored = NEW_FIELDS.get(group.bl_rna.identifier, ())
    result = {'type': group.bl_rna.identifier, 'raw': plain(dict(bpy.types.bpy_struct.items(group))), 'fields': {}}
    for prop in group.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type' or name in ignored:
            continue
        present = group.is_property_set(name)
        if not present:
            result['fields'][name] = [False]
            continue
        value = getattr(group, name)
        if prop.type == 'POINTER' and isinstance(value, bpy.types.PropertyGroup):
            captured = pg_snapshot(value, depth + 1)
        elif prop.type == 'COLLECTION':
            captured = [pg_snapshot(item, depth + 1) if isinstance(item, bpy.types.PropertyGroup)
                        else identity(item) for item in value]
        else:
            captured = plain(value)
        result['fields'][name] = [True, captured]
    # Ignore only the new RNA schema. The complete raw storage retains even
    # pre-existing opaque values under these names; exact before/after equality
    # rejects newly created storage or edits to any existing value.
    return result


def id_pg_snapshot(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        if prop.identifier.startswith('character_designer') and prop.type == 'POINTER':
            if not owner.is_property_set(prop.identifier):
                result[prop.identifier] = [False]
                continue
            value = getattr(owner, prop.identifier)
            if isinstance(value, bpy.types.PropertyGroup):
                result[prop.identifier] = [True, pg_snapshot(value)]
    return result


def action_snapshot(action):
    curves = []
    slots = tuple(getattr(action, 'slots', ()))
    layers = []
    if slots:
        for layer in action.layers:
            strips = []
            for strip in layer.strips:
                bags = []
                for slot in slots:
                    bag = strip.channelbag(slot, ensure=False) if hasattr(strip, 'channelbag') else None
                    if bag is not None:
                        bags.append((slot.handle, tuple(bag.fcurves)))
                strips.append((strip.type, tuple(slot for slot, _curves in bags)))
                for slot, slot_curves in bags:
                    curves.extend((slot, curve) for curve in slot_curves)
            layers.append((layer.name, strips))
    else:
        curves.extend((None, curve) for curve in getattr(action, 'fcurves', ()))
    frozen = []
    for slot, curve in curves:
        keys = [tuple(plain(getattr(key, name)) for name in (
            'co', 'handle_left', 'handle_right', 'interpolation', 'easing',
            'handle_left_type', 'handle_right_type', 'type', 'amplitude', 'back', 'period',
            'select_control_point', 'select_left_handle', 'select_right_handle'))
            for key in curve.keyframe_points]
        modifiers = []
        for modifier in curve.modifiers:
            settings = {}
            for prop in modifier.bl_rna.properties:
                if prop.identifier == 'rna_type':
                    continue
                value = getattr(modifier, prop.identifier)
                if prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
                    settings[prop.identifier] = plain(value)
                elif prop.type == 'COLLECTION':
                    settings[prop.identifier] = [tuple(plain(getattr(point, key)) for key in ('frame', 'min', 'max'))
                                                for point in value]
                else:
                    settings[prop.identifier] = identity(value)
            modifiers.append(settings)
        # Hash every original field, one complete curve at a time. Before/after
        # snapshots retain ordered digests instead of two giant keyframe trees.
        record = (slot, curve.data_path, curve.array_index, curve.extrapolation,
                  curve.mute, curve.lock, curve.select, keys,
                  [plain(point.co) for point in curve.sampled_points], modifiers)
        frozen.append(digest(record))
        del record, keys, modifiers
    return {'id': identity(action), 'raw': plain(dict(bpy.types.bpy_struct.items(action))),
            'fake_user': action.use_fake_user, 'frame_range': plain(action.frame_range),
            'slots': [(slot.handle, slot.identifier, slot.target_id_type) for slot in slots],
            'layers': layers, 'curves': frozen}


def animation_binding(owner):
    data = owner.animation_data
    if data is None:
        return None
    return {'action': identity(data.action), 'slot': getattr(data, 'action_slot_handle', None),
            'use_nla': data.use_nla, 'blend': data.action_blend_type,
            'extrapolation': data.action_extrapolation, 'influence': data.action_influence,
            'tracks': [(track.name, track.mute, track.is_solo,
                [(strip.name, identity(strip.action), getattr(strip, 'action_slot_handle', None),
                  strip.frame_start, strip.frame_end, strip.mute, strip.influence)
                 for strip in track.strips]) for track in data.nla_tracks]}


def snapshot(main):
    groups = [(identity(owner), id_pg_snapshot(owner)) for collection in (
        bpy.data.scenes, bpy.data.window_managers, bpy.data.objects) for owner in collection]
    scenes = []
    for scene in bpy.data.scenes:
        view_layers = []
        for view in scene.view_layers:
            view_layers.append((view.name, identity(view.objects.active),
                [(identity(obj), obj.select_get(view_layer=view)) for obj in view.objects]))
        scenes.append((identity(scene), scene.frame_current, scene.frame_subframe,
                       animation_binding(scene), view_layers))
    objects = []
    for obj in bpy.data.objects:
        pose = []
        if obj.type == 'ARMATURE' and obj.pose:
            pose = [(bone.name, plain(bone.location), plain(bone.rotation_euler),
                     plain(bone.rotation_quaternion), plain(bone.rotation_axis_angle),
                     plain(bone.scale), bone.rotation_mode, plain(bone.matrix_basis),
                     bone.select, bone.hide) for bone in obj.pose.bones]
        objects.append((identity(obj), obj.mode, animation_binding(obj), pose))
    handlers = {name: [id(fn) for fn in getattr(bpy.app.handlers, name)]
                for name in dir(bpy.app.handlers) if not name.startswith('_')
                and isinstance(getattr(bpy.app.handlers, name), list)}
    return {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
            'context_mode': bpy.context.mode, 'groups': groups,
            'actions': [action_snapshot(action) for action in bpy.data.actions],
            'scenes': scenes, 'objects': objects, 'handlers': handlers,
            'windows': [(identity(window.scene), identity(window.view_layer),
                         identity(window.workspace), identity(window.screen),
                         [(area.as_pointer(), area.type, area.ui_type) for area in window.screen.areas])
                        for wm in bpy.data.window_managers for window in wm.windows],
            'old_classes': [(cls.__name__, id(cls), cls.bl_rna.as_pointer()) for cls in main.CLASSES
                            if cls.__name__ not in NEW_OPERATORS]}


def _normalized_animation(tree):
    tree = deepcopy(tree)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ANIMATION_FUNCTIONS:
            node.args = ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])
            node.body = [ast.Pass()]
        elif isinstance(node, ast.ClassDef) and node.name == 'CHARACTERDESIGNER_OT_animation_export_cancel':
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name == 'execute':
                    method.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def validate_inventory(path, root):
    record = json.loads(path.read_text(encoding='utf-8'))
    require(set(record['allowed_delta']) == DELTA, 'Unexpected candidate mutation scope.')
    require(record['base_sha256'] == BASE_SHA256 and sha(record['base']) == BASE_SHA256,
            'The reviewed 0.76.2 release is missing or changed.')
    candidate = Path(record['candidate'])
    require(sha(candidate) == record['candidate_sha256'], 'Candidate archive changed.')
    expected = record['file_sha256']
    with zipfile.ZipFile(record['base']) as base:
        base_files = {name.removeprefix('character_designer/'): base.read(name)
                      for name in base.namelist() if not name.endswith('/')}
    require(set(expected) == set(base_files) | {name + '.py' for name in NEW_MODULES},
            'Candidate must add exactly the three pure/service modules.')
    installed = {}
    for name, expected_hash in expected.items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe candidate relative path.')
        target = (root / relative).resolve()
        require(target.is_relative_to(root), 'Installed candidate escaped its package root.')
        require(sha(target) == expected_hash, 'Installed candidate mismatch: ' + name)
        installed[name] = target.read_bytes()
    changed = {name for name in installed if name not in base_files or installed[name] != base_files[name]}
    require(changed == DELTA, 'Candidate differs outside or omits the eight approved files.')
    with zipfile.ZipFile(candidate) as archive:
        archive_files = {name.removeprefix('character_designer/'): archive.read(name)
                         for name in archive.namelist() if not name.endswith('/')}
    require(set(archive_files) == set(expected) and all(
        hashlib.sha256(data).hexdigest() == expected[name] for name, data in archive_files.items()),
        'Candidate archive and inventory disagree.')
    old_main = ast.parse(base_files['__init__.py'])
    new_main = ast.parse(installed['__init__.py'])
    infos = []
    for tree in (old_main, new_main):
        info = next(node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in node.targets))
        infos.append(ast.literal_eval(info.value))
        info.value = ast.Constant(value=None)
    require(infos[0].pop('version') == FROM_VERSION and infos[1].pop('version') == TO_VERSION
            and infos[0] == infos[1], 'Main metadata changes exceed the approved version.')
    require(ast.dump(old_main) == ast.dump(new_main), 'Main source changes exceed version metadata.')
    old_animation, new_animation = (ast.parse(files['animation.py']) for files in (base_files, installed))
    require(_normalized_animation(old_animation) == _normalized_animation(new_animation),
            'Animation changes exceed the three functions and cancel method patched here.')
    return record, installed


def idle_gate(main, package):
    require(tuple(main.bl_info['version']) == FROM_VERSION, 'Expected loaded 0.76.2 before activation.')
    main._validate_registration_integrity()
    require(not main.ADDON_REFRESH_PENDING and not bpy.app.timers.is_registered(main._reload_addon_deferred),
            'A full add-on refresh is pending.')
    require(bpy.context.mode in {'OBJECT', 'POSE'}, 'Leave active editing modes before activation.')
    require(all(obj.mode in {'OBJECT', 'POSE'} for obj in bpy.data.objects), 'An object remains in Edit Mode.')
    require(not any(window.screen.is_animation_playing for wm in bpy.data.window_managers
                    for window in wm.windows), 'Pause timeline playback first.')
    animation = importlib.import_module(package + '.animation')
    ui = importlib.import_module(package + '.animation_worklist_ui')
    require(animation._job is None and animation._export_window_manager is None,
            'Animation generation/export retains an active owner.')
    exporter = importlib.import_module(package + '.animation_export')
    require(exporter.active_job() is None, 'Animation export is active.')
    model_export = importlib.import_module(package + '.unity_export')
    require(not model_export.export_running(), 'Character model export is active.')
    require(not ui._DRAGS, 'Finish the Worklist pointer gesture first.')
    require(not getattr(main, '_LIVE_PREVIEW_SOURCE_KEY', None), 'Hair Centerline preview is active.')
    for short, field in (('forearm_twist', '_SESSION'), ('delta_symmetry', '_RUNTIME'), ('skirt', '_ACTIVE_BAKES')):
        module = sys.modules.get(package + '.' + short)
        require(module is None or not getattr(module, field, None), 'Finish active preview/bake: ' + short)
    hair = importlib.import_module(package + '.hair_wiggle_adapter')
    require(not hair.status().get('active'), 'Hair motion preview is active.')
    collection = sys.modules.get(package + '.animation_worklist_collection')
    require(collection is None or not collection.running(), 'A collection batch is active.')
    for fn in (animation._poll_job, animation._poll_action_export):
        require(not bpy.app.timers.is_registered(fn), 'A stale animation timer is still registered.')
    return animation, ui


def validate_qa(paths, script_hash, inventory_hash):
    required = {'passed', 'rolled_back'}
    observed = set()
    for path in paths:
        report = json.loads(Path(path).read_text(encoding='utf-8'))
        require(report['script_sha256'] == script_hash and report['inventory_sha256'] == inventory_hash,
                'Factory QA reports use another script or candidate.')
        require(report.get('background') is True and report.get('fixture_worklist_rows', 0) > 0,
                'Factory QA must exercise saved populated Worklist RNA.')
        require(report.get('preserved') is True and report.get('old_registered_classes_preserved') is True,
                'Factory preservation proof is incomplete.')
        if report['status'] == 'rolled_back':
            require(report.get('injected_failure') == 'after_all' and report.get('rollback_complete') is True,
                    'Rollback QA must cover every mutation before injection.')
        observed.add(report['status'])
    require(required <= observed, 'GUI activation requires success and full injected rollback factory reports.')


def run(candidate_inventory, *, report_path=None, package='character_designer',
        qa_reports=(), _fail_at=None):
    """Apply the bounded patch, returning an explicit report; never save a scene.

    ``_fail_at='after_all'`` is background-only rollback QA. No override exists
    for a failed GUI QA gate. Callers must inspect ``status`` rather than infer
    success from the script returning. Report files must stay in this Validation.
    """
    script_hash = sha(__file__)
    inventory_path = Path(candidate_inventory).resolve()
    report = {'schema': 'character-designer.minimal-live-activation/1',
              'script_sha256': script_hash, 'inventory_sha256': sha(inventory_path),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'background': bool(bpy.app.background), 'runtime': bpy.app.version_string,
              'status': 'blocked', 'injected_failure': _fail_at,
              'preserved': False, 'rollback_complete': False,
              'old_registered_classes_preserved': False, 'saved': False}
    output = None
    if report_path is not None:
        output = Path(report_path).resolve()
        require(output.is_relative_to(FOLDER) and output.suffix == '.json', 'Report must remain in this Validation folder.')
        require(not bpy.data.filepath or output != Path(bpy.data.filepath).resolve(), 'Report cannot overwrite an artist file.')
    before = None
    mutated = False
    module_before = {}
    root_attrs = {}
    new_properties, registered_ops = [], []
    ui_classes, annotations = {}, {}
    old_draw, old_cancel = None, None
    try:
        require(_fail_at in (None, 'after_properties', 'after_operators', 'after_all'), 'Unknown failure stage.')
        require(not _fail_at or bpy.app.background, 'Failure injection is only for isolated factory QA.')
        main = sys.modules.get(package)
        require(main is not None and hasattr(main, 'CLASSES'), 'The expected add-on is not loaded.')
        root = Path(main.__file__).resolve().parent
        require(root.name == 'character_designer', 'Unexpected add-on package location.')
        require({Path(value).resolve() for value in main.__path__} == {root}, 'Ambiguous package search path.')
        for name, module in tuple(sys.modules.items()):
            if name.startswith(package + '.') and getattr(module, '__file__', None):
                require(Path(module.__file__).resolve().is_relative_to(root),
                        'A loaded add-on submodule has another source root: ' + name)
        animation, ui = idle_gate(main, package)
        inventory, source = validate_inventory(inventory_path, root)
        if not bpy.app.background:
            validate_qa(qa_reports, script_hash, report['inventory_sha256'])
        before = snapshot(main)
        before_hash = digest(before)
        report['before_sha256'] = before_hash
        report['fixture_worklist_rows'] = sum(len(scene.character_designer_animation_worklist.items)
                                              for scene in bpy.data.scenes)
        report['artist_path'] = bpy.data.filepath
        artist_path = Path(bpy.data.filepath) if bpy.data.filepath else None
        artist_sha = sha(artist_path) if artist_path and artist_path.is_file() else None
        report['artist_disk_sha256_before'] = artist_sha
        old_classes = tuple(main.CLASSES)
        ui_classes = {cls.__name__: cls for cls in ui.WORKLIST_CLASSES}
        require(len(ui_classes) == len(ui.WORKLIST_CLASSES), 'Duplicate old Worklist RNA class names.')
        require(all(main._registered_rna_class(cls) is cls for cls in old_classes), 'Stale registered class owner.')
        old_draw = ui.CHARACTERDESIGNER_UL_animation_worklist.draw_item
        old_cancel = animation.CHARACTERDESIGNER_OT_animation_export_cancel.execute
        for short in ('animation', 'animation_worklist_ui', 'animation_link_source', 'animation_worklist', *NEW_MODULES):
            full = package + '.' + short
            module = sys.modules.get(full)
            module_before[full] = (module, dict(module.__dict__) if module is not None else None)
            root_attrs[short] = main.__dict__.get(short, _MISSING)
        root_saved = {name: main.__dict__.get(name, _MISSING) for name in MAIN_FIELDS}
        for name, fields in NEW_FIELDS.items():
            cls = ui_classes[name]
            annotations[name] = cls.__annotations__
            require(not any(field in cls.bl_rna.properties or hasattr(cls, field) for field in fields),
                    'New RNA fields already exist; this is not a clean 0.76.2 migration.')
        for name in NEW_OPERATORS:
            identifier = 'CHARACTER_DESIGNER_OT_' + name.removeprefix('CHARACTERDESIGNER_OT_')
            require(name not in ui_classes and bpy.types.Operator.bl_rna_get_subclass_py(identifier) is None,
                    'A new collection Operator is already registered.')

        mutated = True
        # SourceResult is a plain Python dataclass, not registered RNA. The
        # approved source-only repair preserves unchanged Render Result enums.
        link_source = importlib.import_module(package + '.animation_link_source')
        importlib.reload(link_source)
        # Worklist has no RNA declarations or persistent handlers. Reloading the
        # same module object keeps existing callback global namespaces coherent.
        worklist = importlib.import_module(package + '.animation_worklist')
        importlib.reload(worklist)
        for short in NEW_MODULES:
            full = package + '.' + short
            module = importlib.import_module(full)
            if module_before[full][0] is not None:
                importlib.reload(module)
            require(Path(module.__file__).resolve() == root / (short + '.py'), 'Service module has another source root.')
        # Executing definitions in the real UI namespace creates unregistered
        # candidate classes. Immediately restore every old registered class name.
        exec(compile(source['animation_worklist_ui.py'], str(root / 'animation_worklist_ui.py'), 'exec'), ui.__dict__)
        candidate_annotations = {name: dict(ui.__dict__[name].__annotations__) for name in NEW_FIELDS}
        candidate_draw = ui.CHARACTERDESIGNER_UL_animation_worklist.draw_item
        candidate_ops = [ui.__dict__[name] for name in NEW_OPERATORS]
        for name, cls in ui_classes.items():
            ui.__dict__[name] = cls
        for name, fields in NEW_FIELDS.items():
            cls = ui_classes[name]
            require(set(candidate_annotations[name]) - set(annotations[name]) == fields,
                    'Candidate PropertyGroup schema adds another field: ' + name)
            for field in sorted(fields):
                definition = candidate_annotations[name][field]
                new_properties.append((cls, field))
                setattr(cls, field, definition)
                cls.__annotations__ = {**cls.__annotations__, field: definition}
                require(field in cls.bl_rna.properties, 'Dynamic RNA field was not registered: ' + field)
        if _fail_at == 'after_properties':
            raise RuntimeError('Injected rollback after_properties')
        for cls in candidate_ops:
            registered_ops.append(cls)
            bpy.utils.register_class(cls)
            require(main._registered_rna_class(cls) is cls, 'New Operator has stale RNA registration.')
        if _fail_at == 'after_operators':
            raise RuntimeError('Injected rollback after_operators')
        ui.CHARACTERDESIGNER_UL_animation_worklist.draw_item = candidate_draw
        ui.WORKLIST_CLASSES = tuple(ui_classes.values()) + tuple(candidate_ops)
        tree = ast.parse(source['animation.py'])
        definitions = [deepcopy(node) for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name in ANIMATION_FUNCTIONS]
        require({node.name for node in definitions} == set(ANIMATION_FUNCTIONS), 'Missing animation patch function.')
        exec(compile(ast.fix_missing_locations(ast.Module(body=definitions, type_ignores=[])),
                     str(root / 'animation.py'), 'exec'), animation.__dict__)
        cancel_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                            and node.name == 'CHARACTERDESIGNER_OT_animation_export_cancel')
        cancel_method = deepcopy(next(node for node in cancel_class.body
                                      if isinstance(node, ast.FunctionDef) and node.name == 'execute'))
        cancel_method.name = '_minimal_live_cancel_execute'
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cancel_method], type_ignores=[])),
                     str(root / 'animation.py'), 'exec'), animation.__dict__)
        animation.CHARACTERDESIGNER_OT_animation_export_cancel.execute = animation.__dict__.pop('_minimal_live_cancel_execute')
        main.WORKLIST_CLASSES = ui.WORKLIST_CLASSES
        main.CLASSES = old_classes + tuple(candidate_ops)
        main.stop_worklist_ui = ui.stop_worklist_ui
        main.bl_info = {**main.bl_info, 'version': TO_VERSION}
        main.ADDON_LOADED_SIGNATURE = main._source_signature()
        main.ADDON_REFRESH_LAST_STATE, main.ADDON_REFRESH_LAST_ERROR = False, ''
        if _fail_at == 'after_all':
            raise RuntimeError('Injected rollback after_all')
        main._validate_registration_integrity()
        require(main.CharacterDesignerAnimationWorklistState is ui_classes['CharacterDesignerAnimationWorklistState'],
                'The saved Worklist pointer type was replaced.')
        require(all(main._registered_rna_class(cls) is cls for cls in old_classes), 'An old RNA class identity changed.')
        after = snapshot(main)
        require(after == before, 'Native artist/PropertyGroup/Action/editor state changed.')
        require(not artist_sha or sha(artist_path) == artist_sha, 'The artist file was written.')
        report.update(status='passed', preserved=True, old_registered_classes_preserved=True,
                      after_sha256=digest(after), property_groups_preserved=True,
                      new_field_storage_preserved=True,
                      added_operators=[cls.__name__ for cls in registered_ops],
                      added_properties=[(cls.__name__, field) for cls, field in new_properties],
                      version=list(TO_VERSION), artist_disk_sha256_after=artist_sha)
    except Exception as exc:
        report['error'], report['traceback'] = str(exc), traceback.format_exc()
        if mutated:
            rollback_errors = []
            def restore(label, callback):
                try:
                    callback()
                except Exception as restore_exc:
                    rollback_errors.append(label + ': ' + str(restore_exc))

            if old_draw is not None:
                restore('old UIList draw', lambda: setattr(
                    ui_classes['CHARACTERDESIGNER_UL_animation_worklist'], 'draw_item', old_draw))
            if old_cancel is not None:
                restore('old cancel method', lambda: setattr(
                    animation.CHARACTERDESIGNER_OT_animation_export_cancel, 'execute', old_cancel))

            def remove_operator(cls):
                owner = main._registered_rna_class(cls)
                if owner is cls:
                    bpy.utils.unregister_class(cls)
                else:
                    require(owner is None, 'A foreign Operator replaced the local registration.')

            for cls in reversed(registered_ops):
                restore('new Operator ' + cls.__name__, lambda cls=cls: remove_operator(cls))
            for cls, field in reversed(new_properties):
                if field in cls.bl_rna.properties or hasattr(cls, field):
                    restore('new field ' + field, lambda cls=cls, field=field: delattr(cls, field))
            for name, value in annotations.items():
                restore('old annotations ' + name, lambda name=name, value=value: setattr(
                    ui_classes[name], '__annotations__', value))

            def restore_module(full, module, values):
                if module is None:
                    sys.modules.pop(full, None)
                else:
                    module.__dict__.clear()
                    module.__dict__.update(values)
                    sys.modules[full] = module

            for full, (module, values) in reversed(tuple(module_before.items())):
                restore('module ' + full, lambda full=full, module=module, values=values:
                        restore_module(full, module, values))

            def restore_root(name, value):
                if value is _MISSING:
                    main.__dict__.pop(name, None)
                else:
                    main.__dict__[name] = value

            for name, value in (*root_attrs.items(), *root_saved.items()):
                restore('main alias ' + name, lambda name=name, value=value: restore_root(name, value))
            try:
                main._validate_registration_integrity()
                after = snapshot(main)
                require(after == before, 'Rollback did not preserve the complete native snapshot, including dirty state.')
                require(not artist_sha or sha(artist_path) == artist_sha, 'Rollback found a changed artist file.')
                require(all(main._registered_rna_class(cls) is cls for cls in old_classes), 'Rollback lost old RNA class identities.')
                report.update(status='rolled_back' if not rollback_errors else 'rollback_incomplete',
                              rollback_complete=not rollback_errors, preserved=True,
                              old_registered_classes_preserved=True, after_sha256=digest(after),
                              version=list(FROM_VERSION), artist_disk_sha256_after=artist_sha)
            except Exception as rollback_exc:
                rollback_errors.append(str(rollback_exc))
                report.update(status='rollback_incomplete', rollback_complete=False)
            report['rollback_errors'] = rollback_errors
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return report
