"""Sealed007 shader proof plus native flat Node.panel_states coverage.

The observed Blender5.2 collection is retained ordinally, including every
native scalar field, raw properties and set-status guards. No UI-field waiver,
stored extension waiver, numeric normalization or resource policy change.
"""
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'mesh_cache_shader_witness_007.py'
BASE_SHA = '8f7f153eba918f4a9cfdf7bf14fd54f98e4f14663de4872540fc2a99a150cf5f'
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('Sealed shader007 changed')
sys.path.insert(0, str(HERE))
import mesh_cache_shader_witness_007 as base
if Path(base.__file__).resolve() != BASE_PATH:
    raise RuntimeError('Foreign shader007 module')
require, digest, serialize_id_mapping = base.require, base.digest, base.serialize_id_mapping
SCHEMA, _plain = base.SCHEMA, base._plain


def panel_property(owner, prop):
    import bpy
    return (isinstance(owner, bpy.types.Node) and prop.identifier == 'panel_states'
        and prop.type == 'COLLECTION' and not getattr(prop, 'is_runtime', False)
        and getattr(prop, 'fixed_type', None) is not None
        and prop.fixed_type.identifier == 'NodePanelState'
        and not getattr(prop.fixed_type, 'is_runtime', False))


class ShaderWitness(base.ShaderWitness):
    def _panels(self, rows, identity, path):
        import bpy
        result = []
        for index, row in enumerate(rows):
            require(type(row) is bpy.types.NodePanelState and row.bl_rna.identifier == 'NodePanelState'
                and not getattr(row.bl_rna, 'is_runtime', False), 'Unknown native node panel row: '+path)
            # The base reader supports scalars; any new pointer/collection or
            # stored registered field still fails before its getter runs.
            result.append(self._state(row, identity, path+'['+str(index)+']'))
        return tuple(result)

    def _state(self, value, identity, path, handlers=None, skip=()):
        handlers = dict(handlers or {})
        for prop in value.bl_rna.properties:
            if prop.identifier == 'panel_states' and prop.identifier not in skip:
                require(panel_property(value, prop), 'Unknown node panel collection declaration: '+path)
                handlers['panel_states'] = lambda rows: self._panels(rows, identity, path+'.panel_states')
        return super()._state(value, identity, path, handlers, skip)
