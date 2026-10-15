"""Bounded mesh-material/World graph witness; no evaluation or scene writes.

Graph, stored/evaluated parameters and initial/final resource bytes are covered.
This is not a shader execution, implicit-coordinate or rendered-pixel oracle.
Only explicit ID routes may change identities; numeric values stay exact.
"""
import hashlib
import importlib
import json
import math
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
PORTABLE_SHA = 'c6881b78c9de8af661b6ecbf264e4e8a4f9861ce645246d9e8dccb1fc298b680'
SCHEMA = 'x.bounded-material-graph/1'
SKIP = frozenset(('rna_type', 'id_data', 'original', 'is_evaluated', 'users', 'tag',
    'is_updated', 'is_updated_data', 'is_updated_transform', 'session_uid',
    'library', 'library_weak_reference', 'asset_data',
    'override_library', 'preview', 'is_embedded_data', 'is_library_indirect',
    'is_editable', 'is_missing', 'is_runtime_data', 'use_fake_user', 'use_extra_user'))
NODE_UI = frozenset(('location', 'location_absolute', 'dimensions', 'width', 'height',
    'select', 'show_options', 'show_preview', 'show_texture', 'hide', 'label',
    'use_custom_color', 'color', 'warning_propagation', 'parent'))
NESTED = {'ColorRamp': {'elements': 'ColorRampElement'},
    'CurveMapping': {'curves': 'CurveMap'}, 'CurveMap': {'points': 'CurveMapPoint'},
    'ColorMapping': {'color_ramp': 'ColorRamp'}, 'TexMapping': {}, 'ImageUser': {},
    'ColorRampElement': {}, 'CurveMapPoint': {}, 'MaterialLineArt': {},
    'WorldLighting': {}, 'WorldMistSettings': {}, 'ColorManagedInputColorspaceSettings': {}}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _portable():
    path = HERE/'native_artifact_action_witness_008.py'
    require(hashlib.sha256(path.read_bytes()).hexdigest() == PORTABLE_SHA,
        'Portable animation helper changed')
    module = importlib.import_module('native_artifact_action_witness_008')
    require(Path(module.__file__).resolve() == path, 'Foreign portable animation helper')
    return module


def _key(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def serialize_id_mapping(source_to_target):
    """Serialize only the caller's explicit native Source -> target ID map."""
    portable = _portable()
    rows = [{'target': portable.identity(target), 'source': portable.identity(source)}
        for source, target in source_to_target.items()]
    require(len({_key(row['target']) for row in rows}) == len(rows), 'Duplicate target ID route')
    require(len({_key(row['source']) for row in rows}) == len(rows), 'Duplicate source ID route')
    return sorted(rows, key=lambda row: _key(row['target']))


def _plain(value, identity):
    import bpy
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite shader parameter')
        return ('float', value.hex())
    if isinstance(value, bpy.types.ID):
        return ('ID', identity(value))
    if isinstance(value, (set, frozenset)):
        return ('set', sorted((_plain(item, identity) for item in value), key=repr))
    if hasattr(value, 'items'):
        return tuple((str(key), _plain(item, identity)) for key, item in value.items())
    try:
        return tuple(_plain(item, identity) for item in value)
    except TypeError as error:
        raise RuntimeError('Unsupported shader value: '+type(value).__name__) from error


def _raw(value, identity):
    import bpy
    try:
        rows = bpy.types.bpy_struct.items(value)
    except TypeError as error:
        require(str(error) == "bpy_struct.items(): this type doesn't support IDProperties",
            'Unexpected raw shader storage error: '+str(error))
        return ('native-no-ID-properties',)
    return tuple((str(key), _plain(item, identity)) for key, item in rows)


def _schema(prop):
    return (prop.identifier, prop.type, bool(getattr(prop, 'is_array', False)),
        int(getattr(prop, 'array_length', 0)), getattr(prop, 'subtype', ''),
        tuple((item.identifier, item.value) for item in prop.enum_items) if prop.type == 'ENUM' else ())


class ShaderWitness:
    def __init__(self):
        self.portable = _portable()
        self.resources = {}
        self._resource_readers = {}

    def _routes(self, id_reverse):
        import bpy
        if id_reverse is None:
            routes = {}
        elif isinstance(id_reverse, dict):
            routes = {_key(self.portable.identity(target)): self.portable.identity(source)
                for target, source in id_reverse.items()}
            require(len(routes) == len(id_reverse), 'Duplicate explicit native ID route')
        else:
            routes = {_key(row['target']): row['source'] for row in id_reverse}
            require(len(routes) == len(id_reverse), 'Duplicate serialized ID route')
        require(len({_key(source) for source in routes.values()}) == len(routes), 'Non-injective shader ID routes')
        def identity(value):
            if value is None:
                return None
            require(isinstance(value, bpy.types.ID), 'Shader identity is not a native ID')
            if value.is_evaluated:
                value = value.original
            original = self.portable.identity(value)
            return routes.get(_key(original), original)
        return identity

    def _animation(self, owner, identity):
        import bpy
        # Rebind only our own function globals; the sealed module is untouched.
        env = dict(vars(self.portable))
        for name, function in vars(self.portable).items():
            if isinstance(function, types.FunctionType) and function.__module__ == self.portable.__name__:
                env[name] = types.FunctionType(function.__code__, env, name, function.__defaults__, function.__closure__)
        env['identity'] = identity
        env['plain'] = lambda value: _plain(value, identity)
        env['props'] = lambda value: _raw(value, identity)
        original_state = env['state']
        def state(value):
            fields, raw = original_state(value)
            # The canonical explicit identity already covers an ID's name.
            # Layer/strip/group/point names are content and stay unchanged.
            if isinstance(value, bpy.types.ID):
                fields = tuple((name, field) for name, field in fields if name not in {'name', 'name_full'})
            return fields, raw
        env['state'] = state
        actions = env['referenced_actions'](owner)
        return (env['animation'](owner), tuple(sorted(
            ((identity(action), env['action'](action)) for action in set(actions)), key=repr)))

    def _state(self, value, identity, path, handlers=None, skip=()):
        import bpy
        require(isinstance(value, bpy.types.bpy_struct), 'Non-native shader struct: '+path)
        require(not getattr(value.bl_rna, 'is_runtime', False), 'Runtime shader type: '+path)
        handlers = handlers or {}
        fields, schema = {}, []
        raw_before = _raw(value, identity)
        excluded = SKIP | frozenset(skip)
        if isinstance(value, bpy.types.ID):
            excluded |= {'name', 'name_full'}
        props = [prop for prop in value.bl_rna.properties if prop.identifier not in excluded]
        set_before = tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props)
        set_bits = dict(set_before)
        for prop in props:
            name = prop.identifier
            schema.append(_schema(prop))
            if getattr(prop, 'is_runtime', False):
                require(prop.type == 'POINTER' and not set_bits[name]
                    and getattr(prop, 'fixed_type', None) is not None,
                    'Unsupported stored/registered shader field: '+path+'.'+name)
                fields[name] = {'scope': 'unset-registered-pointer-no-getter',
                    'fixed_type': prop.fixed_type.identifier, 'default': None, 'is_property_set': False}
                continue
            if name in handlers:
                fields[name] = handlers[name](getattr(value, name))
            elif prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
                fields[name] = _plain(getattr(value, name), identity)
            else:
                raise RuntimeError('Unsupported shader content: '+path+'.'+name+' ('+prop.type+')')
        require(raw_before == _raw(value, identity), 'Shader getter changed raw storage: '+path)
        require(set_before == tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props),
            'Shader getter changed native set status: '+path)
        return {'schema': schema, 'fields': fields, 'raw': raw_before, 'set_bits': set_before}

    def _nested(self, value, identity, path, expected=None):
        if value is None:
            return None
        kind = value.bl_rna.identifier
        require(kind in NESTED and (expected is None or kind == expected), 'Unsupported nested shader settings: '+path+':'+kind)
        handlers = {}
        for name, target in NESTED[kind].items():
            prop = value.bl_rna.properties[name]
            if prop.type == 'COLLECTION':
                handlers[name] = lambda items, target=target, name=name: tuple(
                    self._nested(item, identity, path+'.'+name+'['+str(i)+']', target) for i, item in enumerate(items))
            else:
                handlers[name] = lambda item, target=target, name=name: self._nested(item, identity, path+'.'+name, target)
        return self._state(value, identity, path, handlers)

    @staticmethod
    def _file(path):
        path = Path(path).resolve(strict=True)
        require(path.is_file(), 'Shader resource is not a file: '+str(path))
        before = path.stat()
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                hasher.update(block)
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Resource changed while hashing')
        return {'path': str(path), 'bytes': after.st_size, 'sha256': hasher.hexdigest()}

    def _image(self, image, identity):
        import bpy
        require(image.source == 'FILE' and not image.is_dirty and not image.is_multiview,
            'Only clean single-file shader images supported: '+image.name_full+':'+image.source)
        def read():
            packed = tuple({'filepath': str(Path(bpy.path.abspath(entry.filepath, library=image.library)).absolute()), 'bytes': len(entry.packed_file.data),
                'sha256': hashlib.sha256(entry.packed_file.data).hexdigest()} for entry in image.packed_files)
            external = None if packed else self._file(bpy.path.abspath(image.filepath, library=image.library))
            return {'identity': identity(image), 'packed': packed, 'external': external}
        token = (int(image.as_pointer()), _key(identity(image)))
        if token not in self.resources:
            self.resources[token] = read()
            self._resource_readers[token] = read
        # Read every current parameter; bytes are revalidated explicitly outside timing.
        skip = {'pixels', 'packed_file', 'packed_files', 'tiles', 'views', 'render_slots',
            'filepath', 'filepath_raw', 'size', 'bindcode', 'depth', 'channels', 'has_data',
            'is_dirty', 'is_float', 'is_stereo_3d', 'is_multiview', 'display_aspect',
            'type', 'colorspace_settings', 'stereo_3d_format', 'preview', 'animation_data'}
        state = self._state(image, identity, 'Image:'+image.name_full, skip=skip)
        colorspace = self._nested(image.colorspace_settings, identity, 'Image.colorspace_settings')
        return {'identity': identity(image), 'state': state, 'colorspace': colorspace,
            'absolute_path': str(Path(bpy.path.abspath(image.filepath, library=image.library)).absolute()),
            'resource': self.resources[token]}

    def verify_resources(self):
        for token, read in self._resource_readers.items():
            require(read() == self.resources[token], 'Shader resource bytes/path changed: '+repr(token))
        return True

    def capture(self, scene, id_reverse=None, *, depsgraph=None):
        """Read stored or depsgraph-evaluated parameters; never seek/update/solve."""
        import bpy
        require(bpy.app.version[:2] == (5, 2), 'Bounded shader witness requires Blender5.2')
        identity = self._routes(id_reverse)
        components, trees, tree_active, resources = {}, {}, set(), {}
        def resource(row):
            key = _key(row['identity'])
            require(key not in resources or resources[key] == row, 'Conflicting explicitly mapped shader resources')
            resources[key] = row
        def evaluated(value):
            return value.evaluated_get(depsgraph) if depsgraph is not None else value
        def references(value):
            if value is None:
                return None
            if isinstance(value, bpy.types.Image):
                library(value)
                result = self._image(value, identity)
                resource(result['resource'])
                return result
            require(isinstance(value, bpy.types.ID), 'Unsupported shader reference')
            return identity(value)
        def library(value):
            logical = identity(value)
            while logical[0] == 'embedded':
                logical = logical[1][0]
            path = logical[2]
            if path is not None:
                token = ('library', path)
                if token not in self.resources:
                    def read(path=path):
                        return {'identity': ('linked-library-origin', path), 'external': self._file(path)}
                    self.resources[token] = read()
                    self._resource_readers[token] = read
                resource(self.resources[token])
        def socket(value, path):
            handlers = {'default_value': parameter}
            return self._state(value, identity, path, handlers,
                skip={'node', 'links', 'rna_type', 'description', 'label', 'bl_rna', 'draw_color', 'draw_color_simple'})
        def parameter(value):
            return references(value) if isinstance(value, bpy.types.ID) else _plain(value, identity)
        def tree(value):
            if value is None:
                return None
            require(isinstance(value, bpy.types.ShaderNodeTree), 'Non-shader node tree')
            library(value)
            token = _key(identity(value))
            require(token not in tree_active, 'Cyclic ShaderNodeTree: '+token)
            if token in trees:
                return identity(value)
            tree_active.add(token)
            nodes = []
            for node in value.nodes:
                kind = node.bl_rna.identifier
                require((kind.startswith('ShaderNode') or kind in {'NodeGroupInput', 'NodeGroupOutput', 'NodeReroute', 'NodeFrame'})
                    and kind != 'ShaderNodeScript' and type(node) is getattr(bpy.types, kind, None),
                    'Unsupported/custom shader node: '+kind)
                path = token+'.node['+node.name+']'
                require(not any(prop.identifier in {'filepath', 'filepath_raw', 'file_path', 'filename'}
                    for prop in node.bl_rna.properties), 'Unsupported external-file shader node: '+path)
                handlers = {'inputs': lambda items, path=path: tuple(socket(item, path+'.input['+str(i)+']') for i, item in enumerate(items)),
                    'outputs': lambda items, path=path: tuple(socket(item, path+'.output['+str(i)+']') for i, item in enumerate(items)),
                    'node_tree': tree, 'image': references, 'object': references,
                    'internal_links': lambda items: tuple((link.from_socket.identifier, link.to_socket.identifier) for link in items)}
                for prop in node.bl_rna.properties:
                    if prop.type == 'POINTER' and getattr(prop, 'fixed_type', None) is not None and prop.fixed_type.identifier in NESTED:
                        handlers[prop.identifier] = lambda item, path=path, name=prop.identifier: self._nested(item, identity, path+'.'+name)
                state = self._state(node, identity, path, handlers, skip=NODE_UI | {'text'})
                nodes.append((node.name, kind, state))
            links = tuple((link.from_node.name, list(link.from_node.outputs).index(link.from_socket),
                link.to_node.name, list(link.to_node.inputs).index(link.to_socket), bool(link.is_muted), bool(link.is_valid)) for link in value.links)
            def interface(current):
                return tuple(self._state(item, identity, token+'.interface['+str(i)+']',
                    {'parent': lambda parent: None if parent is None else parent.index,
                     'default_value': parameter}, skip={'description', 'interface_items'})
                    for i, item in enumerate(current.items_tree))
            state = self._state(value, identity, token, {'interface': interface},
                skip={'nodes', 'links', 'animation_data', 'grease_pencil', 'view_center', 'type', 'bl_icon'})
            trees[token] = {'state': state, 'nodes': nodes, 'links': links, 'animation': self._animation(value, identity)}
            tree_active.remove(token)
            return identity(value)
        def owner(value):
            library(value)
            current = evaluated(value)
            path = _key(identity(value))
            handlers = {'node_tree': tree}
            for prop in current.bl_rna.properties:
                if prop.type == 'POINTER' and getattr(prop, 'fixed_type', None) is not None and prop.fixed_type.identifier in NESTED:
                    handlers[prop.identifier] = lambda item, path=path, name=prop.identifier: self._nested(item, identity, path+'.'+name)
            require(not isinstance(current, bpy.types.Material) or not current.is_grease_pencil, 'Grease-pencil materials outside mesh shader scope')
            state = self._state(current, identity, path, handlers,
                skip={'animation_data', 'texture_paint_images', 'texture_paint_slots', 'grease_pencil'})
            components[path] = digest({'state': state, 'animation': self._animation(value, identity)})
        materials, bindings = set(), []
        for obj in sorted((item for item in scene.objects if item.type == 'MESH'), key=lambda item: _key(identity(item))):
            slots = tuple((slot.link, references(slot.material)) for slot in obj.material_slots)
            data = tuple(references(material) for material in obj.data.materials)
            bindings.append((identity(obj), slots, data))
            materials.update(slot.material for slot in obj.material_slots if slot.material is not None)
            materials.update(material for material in obj.data.materials if material is not None)
        for material in sorted(materials, key=lambda item: _key(identity(item))):
            owner(material)
        if scene.world is not None:
            owner(scene.world)
        components['bindings'] = digest(bindings)
        components['world_binding'] = digest(identity(scene.world))
        components.update({'tree:'+key: digest(value) for key, value in trees.items()})
        components['resources'] = digest(resources)
        content = {'components': components}
        return {'schema': SCHEMA, 'sha256': digest(content), **content,
            'resources': sorted(resources.values(), key=lambda item: _key(item['identity'])),
            'scope': {'graph_and_parameters': True, 'evaluated_parameters': depsgraph is not None,
                'resource_bytes': 'first encounter and explicit verify_resources; no per-frame filesystem hashing',
                'native_ID_routes_only': True, 'pixel_output_or_implicit_coordinates': False,
                'unset_registered_pointers': 'schema/default/unset marker only; getter and extension contents unobserved; stored extensions rejected',
                'editor_layout_and_ID_bookkeeping': False}}
