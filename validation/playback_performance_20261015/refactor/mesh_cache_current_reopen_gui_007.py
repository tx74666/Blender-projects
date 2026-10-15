"""Current artifact GUI: sealed005 lifecycle +006 Base proof +007 contract.

Only private AST namespaces change. Root alone launches a fresh blank GUI;
this module never launches/saves/defer-disables handlers or calls a solver.
The current contract pins real SaveCopy/Full30 provenance, not fixed40644.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback
import types

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE/'mesh_cache_artifact_reopen_gui_005.py'
BASE_SHA = 'd30819f81998d3a262792e4b33d0af0040988307557b07b4972e5c16909f035e'
VISIBILITY_PATH = HERE/'mesh_cache_artifact_reopen_gui_006.py'
VISIBILITY_SHA = '0002e7b85769b7249f542039a9c12000fdb9fee33ea4f211422063e94e3a0703'
CONTRACT_PATH = HERE/'mesh_cache_current_contract_007.py'
CONTRACT_SHA = '6c59089fe69b06f88cc681205fff0cdff805bb52569ddc512239599464a0a855'
SCHEMA = 'x.current-pc2-artifact-gui-reopen/1'
SESSION = None
for path, sha in ((BASE_PATH, BASE_SHA), (VISIBILITY_PATH, VISIBILITY_SHA)):
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError('Sealed GUI source changed: '+path.name)
sys.path.insert(0, str(HERE))
import mesh_cache_artifact_reopen_gui_005 as original
import mesh_cache_artifact_reopen_gui_006 as visibility
require, pin = original.require, original.pin
require(Path(original.__file__).resolve() == BASE_PATH and Path(visibility.__file__).resolve() == VISIBILITY_PATH,
    'Foreign GUI lifecycle module')


def routed_import(name, package=None):
    return importlib.import_module('mesh_cache_current_contract_007'
        if name == 'mesh_cache_artifact_contract_005' else name, package)


def private_classes():
    """Keep all clock/load/timer/cleanup methods; disclose two proof changes."""
    base_source = BASE_PATH.read_bytes()
    layer_source = VISIBILITY_PATH.read_bytes()
    require(hashlib.sha256(base_source).hexdigest() == BASE_SHA
        and hashlib.sha256(layer_source).hexdigest() == VISIBILITY_SHA, 'Sealed GUI sources changed')
    base_tree = ast.parse(base_source.decode('utf-8'))
    cls = copy.deepcopy(next(node for node in base_tree.body if isinstance(node, ast.ClassDef) and node.name == 'ReopenSession'))
    changes = {'mesh_count_constants': 0, 'geometry_field_rename': 0, 'shader_guard': 0, 'result_fields': 0}
    class Counts(ast.NodeTransformer):
        def visit_Constant(self, node):
            if type(node.value) is int and node.value == 69:
                changes['mesh_count_constants'] += 1
                return ast.copy_location(ast.parse('self.expected_mesh_count', mode='eval').body, node)
            if node.value == 'full69_geometry_exact':
                changes['geometry_field_rename'] += 1
                return ast.copy_location(ast.Constant(value='full_current_geometry_exact'), node)
            return node
    cls = Counts().visit(cls)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'verify_frame')
    require(isinstance(method.body[-1], ast.Return) and isinstance(method.body[-1].value, ast.Dict), 'Sealed frame receipt changed')
    guard = ast.parse("require(result['shader_exact'] is True and result['visibility_exact'] is True, 'Current shader or Base proof differs')").body[0]
    method.body.insert(-1, guard)
    changes['shader_guard'] = 1
    for name in ('shader_exact', 'shader_sha256', 'visibility_exact'):
        method.body[-1].value.keys.append(ast.Constant(value=name))
        method.body[-1].value.values.append(ast.parse("result['"+name+"']", mode='eval').body)
        changes['result_fields'] += 1
    require(changes == {'mesh_count_constants': 3, 'geometry_field_rename': 1, 'shader_guard': 1, 'result_fields': 3},
        'Unexpected private GUI proof extraction')
    scope = dict(vars(original))
    scope.update(__file__=str(Path(__file__).resolve()), CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA,
        importlib=types.SimpleNamespace(import_module=routed_import))
    ast.fix_missing_locations(cls)
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(BASE_PATH), 'exec'), scope)
    base = scope['ReopenSession']
    base_ast = hashlib.sha256(ast.dump(cls, include_attributes=False).encode()).hexdigest()
    layer_cls = next(node for node in ast.parse(layer_source.decode('utf-8')).body
        if isinstance(node, ast.ClassDef) and node.name == 'ReopenSession')
    layer_scope = dict(vars(visibility))
    layer_scope.update(__file__=str(Path(__file__).resolve()), _BaseSession=base, BASE_CLASS_AST_SHA=base_ast,
        CONTRACT_PATH=CONTRACT_PATH, CONTRACT_SHA=CONTRACT_SHA)
    exec(compile(ast.Module(body=[layer_cls], type_ignores=[]), str(VISIBILITY_PATH), 'exec'), layer_scope)
    return base, layer_scope['ReopenSession'], {'changes': changes, 'base_class_ast_sha256': base_ast,
        'visibility_class_ast_sha256': hashlib.sha256(ast.dump(layer_cls, include_attributes=False).encode()).hexdigest(),
        'unchanged': '005 start/tick/finish/lifecycle/readiness/flush;006 class AST including one-time Layer selection'}


_BaseSession, _VisibilitySession, EXTRACTION = private_classes()


class ReopenSession(_VisibilitySession):
    def __init__(self, args, stream, report):
        super().__init__(args, stream, report)
        self.expected_mesh_count = len(self.contract['objects'])
        require(self.expected_mesh_count > 0 and self.contract['schema'] == 'x.current-pc2-artifact-contract/1'
            and self.receipt['schema'] == 'x.current-pc2-artifact/1', 'Actual nonempty current artifact required')
        self.report.update(schema=SCHEMA, adapter_visibility_gui=pin(VISIBILITY_PATH), adapter_extraction=EXTRACTION,
            current_snapshot_receipt=self.receipt['current_snapshot_receipt'], current_input=self.receipt['input_before'],
            current_snapshot_provenance_verified=True, expected_mesh_count=self.expected_mesh_count,
            shader_frames=[], current_materials_all_frames_exact=False,
            current_material_resources_initial_exact=False, current_material_resources_after_exact=False,
            current_material_saved_frame_exact=False,
            material_resource_scope='Graph/parameters/driven parameters per integer frame; resource bytes at initial/final animation checks; no pixel/implicit-coordinate claim.')

    def verify_frame(self, bpy):
        row = super().verify_frame(bpy)
        require(row['mesh_count'] == self.expected_mesh_count and row['shader_exact'] is True
            and row['visibility_exact'] is True, 'Current complete frame proof differs')
        if not self.report['shader_frames']:
            require(self.report.get('portable_animation_initial_exact') is True,
                'Initial current animation/resource check not completed')
            self.report['current_material_resources_initial_exact'] = True
        if self.phase == 'RESTORE_VERIFY':
            self.report['current_material_saved_frame_exact'] = self.frame == 1
        else:
            self.report['shader_frames'].append({'frame': self.frame, 'exact': True,
                'sha256': row['shader_sha256'], 'check_sha256': row['check_sha256']})
        return row

    def finish(self, error=None):
        if self.finished:
            return
        try:
            rows = self.report['shader_frames']
            self.report['current_materials_all_frames_exact'] = (
                [row['frame'] for row in rows] == list(range(1, 31)) and all(row['exact'] is True for row in rows))
            # Pinned007.animation_state rechecks live resource readers before returning.
            self.report['current_material_resources_after_exact'] = self.report.get('portable_animation_after_restore_exact') is True
            self.report['adapter_visibility_gui_unchanged'] = pin(VISIBILITY_PATH) == self.report['adapter_visibility_gui']
            require(all(self.report.get(name) is True for name in ('current_snapshot_provenance_verified',
                'current_materials_all_frames_exact', 'current_material_resources_initial_exact',
                'current_material_resources_after_exact', 'current_material_saved_frame_exact',
                'adapter_visibility_gui_unchanged')), 'Current GUI material/resource/provenance proof incomplete')
        except BaseException:
            extra = traceback.format_exc()
            error = error+'\nCurrent GUI proof:\n'+extra if error else extra
        super().finish(error)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('artifact-report', 'artifact-report-sha256', 'report'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--timeout', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    path = Path(args.report).resolve()
    require(path.parent == HERE and path.suffix == '.json' and not path.exists(), 'Unused direct project JSON report required')
    report = {'schema': SCHEMA, 'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'gui_fps_verified': False,
        'no_scene_save': True, 'no_manual_solver_or_parent_helper_calls': True,
        'no_handler_disable_or_runtime_defer': True, 'preview_process_left_alive': True,
        'limits': ['Guarded current SaveCopy at its timestamp; no equivalence to later artist edits.',
            'Integer1–30 complete current Mesh geometry, native Base state and material parameters; no subframe or pixel acceptance.',
            'Initial/final full Layer table/Action/closure/resource bytes; per-frame current Layer and material parameters.',
            'Root aligns view/shading/resolution and prewarms before a separate actual GUI FPS probe.']}
    stream = path.open('x', encoding='utf-8')
    try:
        SESSION = ReopenSession(args, stream, report)
        SESSION.start()
    except BaseException:
        error = traceback.format_exc()
        if SESSION is not None:
            SESSION.finish(error)
        else:
            report.update(error=error, completed=False)
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
            stream.close()
        raise
