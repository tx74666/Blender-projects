"""008 plus observed official CyclesMaterialSettings and null annotation.

Only the exact bundled five-scalar registered class is supported. Arbitrary
stored extensions and non-null annotations remain rejected. Source code is
pinned once and rechecked with resources, never rehashed per material/frame.
"""
import ast
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'mesh_cache_shader_witness_008.py'
BASE_SHA = 'd3173c8112abca44073e23c4511808251d9df17dda6645bf50897b8b1a4268cb'
CYCLES_PATH = Path('D:/Blender5.2/5.2/scripts/addons_core/cycles/properties.py')
CYCLES_SHA = '77f24ef03164684c5cc866fa748445043b32023cbbd121b5e6523bd6433abd9d'
FIELDS = {'emission_sampling': ('ENUM', 'EnumProperty'),
    'use_bump_map_correction': ('BOOLEAN', 'BoolProperty'),
    'volume_sampling': ('ENUM', 'EnumProperty'), 'volume_interpolation': ('ENUM', 'EnumProperty'),
    'volume_step_rate': ('FLOAT', 'FloatProperty')}
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('Sealed shader008 changed')
sys.path.insert(0, str(HERE))
import mesh_cache_shader_witness_008 as base
if Path(base.__file__).resolve() != BASE_PATH:
    raise RuntimeError('Foreign shader008 module')
require, digest, serialize_id_mapping = base.require, base.digest, base.serialize_id_mapping
SCHEMA, _plain = base.SCHEMA, base._plain
legacy = base.base


class ShaderWitness(base.ShaderWitness):
    def __init__(self):
        super().__init__()
        self._cycles_class = self._cycles_module = self._cycles_pin = None

    def _cycles_type(self, prop):
        import bpy
        module = sys.modules.get('cycles.properties')
        require(module is not None, 'Official Cycles properties module is not loaded')
        cls = vars(module).get('CyclesMaterialSettings')
        require(cls is not None and cls.__module__ == 'cycles.properties'
            and issubclass(cls, bpy.types.PropertyGroup), 'Unexpected Cycles settings class')
        if self._cycles_class is None:
            require(Path(module.__file__).resolve() == CYCLES_PATH.resolve(), 'Cycles module is not the pinned bundled source')
            data = CYCLES_PATH.read_bytes()
            pin = {'path': str(CYCLES_PATH.resolve()), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            require(pin['sha256'] == CYCLES_SHA, 'Bundled Cycles source differs')
            cls_ast = next(node for node in ast.parse(data.decode('utf-8')).body
                if isinstance(node, ast.ClassDef) and node.name == 'CyclesMaterialSettings')
            declarations = {node.target.id: node.annotation for node in cls_ast.body
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
            require(set(declarations) == set(FIELDS), 'Official Cycles source declaration schema differs')
            for name, annotation in declarations.items():
                require(isinstance(annotation, ast.Call) and isinstance(annotation.func, ast.Name)
                    and annotation.func.id == FIELDS[name][1] and not any(keyword.arg in
                        {'get', 'set', 'get_transform', 'set_transform', 'update'} for keyword in annotation.keywords),
                    'Unexpected official Cycles callback/factory: '+name)
            annotations = vars(cls).get('__annotations__', {})
            require(set(annotations) == set(FIELDS) and all(type(annotations[name]) is str
                and ast.dump(ast.parse(annotations[name], mode='eval').body, include_attributes=False)
                    == ast.dump(declarations[name], include_attributes=False) for name in FIELDS),
                'Live Cycles annotations differ from pinned official declaration AST')
            self._cycles_annotations = dict(annotations)
            self._cycles_declaration = digest({name: ast.dump(value, include_attributes=False) for name, value in declarations.items()})
            self._cycles_class, self._cycles_module, self._cycles_pin = cls, module, pin
            token = ('code', str(CYCLES_PATH))
            self.resources[token] = {'identity': ('code-provenance', str(CYCLES_PATH)), 'external': pin}
            self._resource_readers[token] = lambda: {'identity': ('code-provenance', str(CYCLES_PATH)), 'external': self._file(CYCLES_PATH)}
        require(cls is self._cycles_class and module is self._cycles_module
            and prop.fixed_type.as_pointer() == cls.bl_rna.as_pointer(), 'Cycles registered class/RNA identity changed')
        require(vars(cls).get('__annotations__', {}) == self._cycles_annotations,
            'Live Cycles declaration changed after initial validation')
        return cls, self._cycles_declaration

    def _cycles_state(self, value, identity, path, cls, declaration):
        require(type(value) is cls and value.bl_rna.as_pointer() == cls.bl_rna.as_pointer(),
            'Cycles value is not the exact official registered class')
        self._cycles_used = True
        props = [prop for prop in value.bl_rna.properties if prop.identifier not in legacy.SKIP]
        names = {prop.identifier for prop in props}
        require(set(FIELDS) <= names <= set(FIELDS) | {'name'}, 'Unexpected Cycles RNA fields')
        for prop in props:
            expected = FIELDS[prop.identifier][0] if prop.identifier in FIELDS else 'STRING'
            require(prop.type == expected and not bool(getattr(prop, 'is_array', False))
                and bool(getattr(prop, 'is_runtime', False)) == (prop.identifier in FIELDS),
                'Unexpected Cycles RNA type/runtime override: '+prop.identifier)
        before = legacy._raw(value, identity)
        bits = tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props)
        fields = tuple((prop.identifier, _plain(getattr(value, prop.identifier), identity)) for prop in props)
        require(before == legacy._raw(value, identity)
            and bits == tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in props),
            'Cycles scalar getter changed raw/set status: '+path)
        return {'schema': tuple(legacy._schema(prop) for prop in props), 'fields': fields, 'raw': before,
            'set_bits': bits, 'declaration_sha256': declaration, 'official_source': self._cycles_pin}

    def _state(self, value, identity, path, handlers=None, skip=()):
        import bpy
        handlers, skip = dict(handlers or {}), frozenset(skip)
        cycle = None
        for prop in value.bl_rna.properties:
            if prop.identifier in skip:
                continue
            if prop.identifier == 'annotation':
                require(isinstance(value, bpy.types.NodeTree) and prop.type == 'POINTER'
                    and not getattr(prop, 'is_runtime', False) and prop.fixed_type.identifier == 'Annotation'
                    and not getattr(prop.fixed_type, 'is_runtime', False), 'Unknown annotation declaration: '+path)
                def annotation(item):
                    require(item is None, 'Non-null annotation content is outside this proof: '+path)
                    return None
                handlers['annotation'] = annotation
            if prop.identifier == 'cycles' and type(value) is bpy.types.Material and value.is_property_set('cycles'):
                require(prop.type == 'POINTER' and getattr(prop, 'is_runtime', False)
                    and prop.fixed_type.identifier == 'CyclesMaterialSettings', 'Unknown Material.cycles declaration')
                cycle = prop
        if cycle is None:
            return super()._state(value, identity, path, handlers, skip)
        cls, declaration = self._cycles_type(cycle)  # validate before Source pointer getter
        before = legacy._raw(value, identity)
        outer_props = [prop for prop in value.bl_rna.properties if prop.identifier not in legacy.SKIP and prop.identifier not in skip]
        bits = tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in outer_props)
        result = super()._state(value, identity, path, handlers, skip | {'cycles'})
        payload = self._cycles_state(getattr(value, 'cycles'), identity, path+'.cycles', cls, declaration)
        require(before == legacy._raw(value, identity)
            and bits == tuple((prop.identifier, bool(value.is_property_set(prop.identifier))) for prop in outer_props),
            'Material Cycles pointer getter changed raw/set status: '+path)
        result['schema'].append(legacy._schema(cycle))
        result['fields']['cycles'] = payload
        result['set_bits'] += (('cycles', dict(bits)['cycles']),)
        return result

    def capture(self, scene, id_reverse=None, *, depsgraph=None):
        self._cycles_used = False
        value = super().capture(scene, id_reverse, depsgraph=depsgraph)
        if self._cycles_used:
            value['resources'].append({'identity': ('code-provenance', str(CYCLES_PATH)), 'external': self._cycles_pin})
            value['resources'].sort(key=lambda row: legacy._key(row['identity']))
        value['scope']['cycles_extension'] = 'Exact pinned official CyclesMaterialSettings five scalar declarations plus inherited name/raw/setbits; other stored extensions rejected.'
        value['scope']['node_tree_annotation'] = 'Native null annotation only; non-null data rejected.'
        return value
