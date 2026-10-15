"""Sealed Stage09 Base-state helper, appended to the Stage06 private builder.

The existing Stage08 parent remap remains installed by the caller's old runner.
No handlers/register/UI are added and no original Source IDs are written.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support as base
import mesh_cache_actor_parent_diagnostic_003 as parent

STAGE = HERE/'staged_20261015_09'
MANIFEST_SHA = 'b8faecfb0ce428bbdc3d845494fae7cb2aa5db4b4c9ad875e399194f98529ee6'
SCENE_SHA = '3d06f61b85758723150f518524ea63aee066e545cb4b6ad2a7499ebfb877b4ac'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sealed_copy(globals_dict):
    manifest = base.pin(STAGE/'source_manifest.json')
    require(manifest['sha256'] == MANIFEST_SHA, 'Stage09 manifest changed')
    package = base.verify_package_manifest(STAGE/'addons/character_designer',
        json.loads(Path(manifest['path']).read_text(encoding='utf-8-sig')))
    path = STAGE/'addons/character_designer/forearm_twist_playback_scene.py'
    require(base.pin(path)['sha256'] == SCENE_SHA, 'Stage09 Base-state helper changed')
    node = next(item for item in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(item, ast.FunctionDef) and item.name == '_copy_view_layer_state')
    scope = dict(globals_dict)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    return scope[node.name], {'manifest': manifest, 'scene_source': base.pin(path), 'package': package,
        'function_ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
        'scope': 'Only Stage09 _copy_view_layer_state appended to Stage06 builder; Stage08 parent remap remains explicit and independent. No Stage09 __init__/registration executed.'}


def check_visibility(scene, state, all_layers=True):
    """Read only native Base/Collection flags; no seek, evaluation or file reads."""
    import bpy
    require(state.get('schema') == 'character-designer.private-view-layer-state/1', 'Wrong Base-state contract')
    require(bpy.context.scene is scene and bpy.context.view_layer.name == state['context_view_layer'],
            'Preview context View Layer changed')
    require([layer.name for layer in scene.view_layers] == [row['name'] for row in state['layers']], 'View Layer inventory differs')
    expected = state['layers'] if all_layers else [row for row in state['layers'] if row['name'] == state['context_view_layer']]
    require(expected, 'Context View Layer absent from Base-state contract')
    for row in expected:
        layer = scene.view_layers[row['name']]
        active = layer.objects.active
        actual = {'name': layer.name, 'active': active.name_full if active is not None else None,
            'objects': [{'name': obj.name_full, 'hidden': bool(obj.hide_get(view_layer=layer)),
                         'selected': bool(obj.select_get(view_layer=layer))}
                        for obj in sorted(layer.objects, key=lambda item: item.name_full)]}
        require(actual == row, 'Native Base state differs in View Layer: '+row['name'])
    collections, seen = {}, set()
    def walk(item):
        pointer = int(item.as_pointer())
        if pointer in seen:
            return
        seen.add(pointer)
        require(item.name_full not in collections, 'Ambiguous Collection name in Base-state contract')
        collections[item.name_full] = item
        for child in item.children:
            walk(child)
    walk(scene.collection)
    require(set(collections) == {row['name'] for row in state['collection_hide_select']}, 'Collection membership differs')
    require(all(bool(collections[row['name']].hide_select) == row['hide_select']
                for row in state['collection_hide_select']), 'Collection selectability differs')
    return {'exact': True, 'context_view_layer': state['context_view_layer'], 'layers_checked': len(expected)}


class VisibilityAdapter:
    def __init__(self, scene_module, report):
        self.module, self.report = scene_module, report
        self.original = scene_module.build_isolated_scene
        self.copy, seal = sealed_copy(scene_module.__dict__)
        self.session = None
        self.sources = {Path(__file__).name: base.pin(__file__)}
        self.report.update(visibility_override=seal, visibility_adapter_sources=self.sources)
        self.wrapper = self.build

    def build(self, source):
        require(self.session is None, 'This private visibility adapter builds one Scene only')
        session = self.original(source)
        try:
            state = self.copy(session)
            self.report['visibility_contract'] = state
            self.report['source_to_clone_visibility_exact'] = True
            self.session = session
            return session
        except BaseException:
            try:
                session.close()
            except BaseException:
                self.report['visibility_build_cleanup_error'] = traceback.format_exc()
            raise

    def install(self):
        require(self.module.build_isolated_scene is self.original, 'Builder ownership changed before visibility install')
        self.module.build_isolated_scene = self.wrapper
        return self

    def close(self):
        self.report['visibility_hook_still_owned'] = self.module.build_isolated_scene is self.wrapper
        self.report['visibility_hook_restored'] = parent.restore_owned_hooks((
            ('builder', self.module, 'build_isolated_scene', self.wrapper, self.original),))['builder']
        self.report['visibility_sources_unchanged'] = all(item == base.pin(item['path']) for item in self.sources.values())
        seal = self.report['visibility_override']
        self.report['visibility_stage09_unchanged'] = (seal['manifest'] == base.pin(seal['manifest']['path'])
            and seal['package'] == base.verify_package_manifest(STAGE/'addons/character_designer',
                json.loads(Path(seal['manifest']['path']).read_text(encoding='utf-8-sig'))))
        require(all(self.report[key] is True for key in ('visibility_hook_still_owned', 'visibility_hook_restored',
                'visibility_sources_unchanged', 'visibility_stage09_unchanged')), 'Visibility adapter cleanup/source seal failed')
