"""Staged-only two-function boundary checks; no bpy/runtime import or Native."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
OLD_SHA = {'skirt_surface_direct.py':'eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99',
           'skirt.py':'f5d08c213d9b98d47199996b3baced92e3d7cf20fdcedc85987e0e80d676804d'}
NEW_SHA = {'skirt_surface_direct.py':'e07634927c790323ffa70c19e52320ce0068fbd65e0447770ff515bea3fdd9c3',
           'skirt.py':'5f6baf35bad958d4235ebc4c1d935e38e168b1eb4deec0abe7fab462102ea742'}
SERVICE_PATH = REPO/'tests/test_skirt_surface_direct_service.py'
SERVICE_SHA = '940d63dfda070c455fbc617ab9364998c45b80f56887a7a3841cea63ef6e4fa6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(SERVICE_PATH) == SERVICE_SHA
spec = importlib.util.spec_from_file_location('staged_service_boundaries',SERVICE_PATH)
service = importlib.util.module_from_spec(spec); spec.loader.exec_module(service)
service.SOURCE = HERE/'skirt_surface_direct.py'
service.TREE = ast.parse(service.SOURCE.read_text(encoding='utf-8'))
service.FUNCTIONS = {n.name:n for n in service.TREE.body if isinstance(n,ast.FunctionDef)}
SKIRT_TREE = ast.parse((HERE/'skirt.py').read_text(encoding='utf-8'))
REQUEST = next(n for n in SKIRT_TREE.body if isinstance(n,ast.FunctionDef) and n.name=='_add_requested_physics')


def request_env(setup,calls):
    direct = object(); legacy = object(); delta = object(); result = object()
    def add(*args,**kwargs):
        calls.append((args,kwargs)); return result
    physics = NS(DIRECT_SURFACE_BACKEND=direct,ACTUAL_SURFACE_BACKEND=delta,LEGACY_BACKEND=legacy,add_physics=add)
    env = {'_physics':lambda:physics,'_setup':lambda:NS(settings=setup)}
    exec(compile(ast.Module([copy.deepcopy(REQUEST)],[]),str(HERE/'skirt.py'),'exec'),env)
    return env,direct,result


class Boundaries(unittest.TestCase):
    def fixture(self):
        return service.DirectServiceTests().state_fixture()

    def test_scope_exact_only_two_functions_and_canonical_unchanged(self):
        for name,changed in (('skirt_surface_direct.py','set_mode'),('skirt.py','_add_requested_physics')):
            actual=REPO/'addons/character_designer'/name; staged=HERE/name
            self.assertEqual(sha(actual),OLD_SHA[name]);self.assertEqual(sha(staged),NEW_SHA[name])
            old=ast.parse(actual.read_text(encoding='utf-8'));new=ast.parse(staged.read_text(encoding='utf-8'))
            before=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==changed)
            index=next(i for i,n in enumerate(new.body) if isinstance(n,ast.FunctionDef) and n.name==changed)
            new.body[index]=copy.deepcopy(before)
            self.assertEqual(ast.dump(old),ast.dump(new))
        old_fn=next(n for n in ast.parse((REPO/'addons/character_designer/skirt.py').read_text(encoding='utf-8')).body
                    if isinstance(n,ast.FunctionDef) and n.name=='_add_requested_physics')
        self.assertEqual(ast.dump(old_fn.body[2]),ast.dump(REQUEST.body[2]))

    def test_unsealed_manual_requires_reset_and_keeps_cache_fields(self):
        env,source,record,context,output,cloth=self.fixture()
        before=copy.deepcopy(vars(cloth.point_cache))
        env['set_mode'](source,record,'MANUAL')
        self.assertTrue(json.loads(source['direct-state'])['pending'])
        self.assertFalse(output.properties.inputs.Socket_2.value)
        self.assertFalse(cloth.show_viewport);self.assertFalse(cloth.show_render)
        raw=source['direct-state']
        with self.assertRaisesRegex(service.DirectError,'Reset the simulation explicitly'):
            env['set_mode'](source,record,'AUTOMATIC')
        self.assertEqual(source['direct-state'],raw);self.assertEqual(vars(cloth.point_cache),before)

    def test_successful_reset_retains_manual_preview_then_auto_is_explicit(self):
        env,source,record,context,output,cloth=self.fixture()
        env['set_mode'](source,record,'MANUAL');env['reset_completed'](context,source,record)
        self.assertEqual(json.loads(source['direct-state'])['mode'],'MANUAL')
        self.assertFalse(json.loads(source['direct-state'])['pending'])
        self.assertFalse(output.properties.inputs.Socket_2.value);self.assertFalse(cloth.show_viewport)
        with self.assertRaises(service.DirectError):env['require_bake_ready'](source,record)
        env['set_mode'](source,record,'AUTOMATIC');env['require_bake_ready'](source,record)
        self.assertTrue(output.properties.inputs.Socket_2.value);self.assertTrue(cloth.show_viewport)

    def test_original_editing_boundary_still_requires_reset(self):
        env,source,record,context,output,cloth=self.fixture()
        env['set_mode'](source,record,'MANUAL')
        env['set_editing'](source,record,True);env['set_editing'](source,record,False)
        self.assertTrue(json.loads(source['direct-state'])['pending'])
        with self.assertRaises(service.DirectError):env['set_mode'](source,record,'AUTOMATIC')

    def test_legacy_false_does_not_read_setup_and_preserves_original_call(self):
        calls=[]
        def unavailable(_context):self.fail('Legacy read Character Setup')
        env,direct,result=request_env(unavailable,calls)
        context=object();source=object()
        self.assertIs(env['_add_requested_physics'](context,source,False,capability='BOTH'),result)
        self.assertEqual(calls,[((context,source),{})])

    def test_direct_uses_exact_saved_body_pointer_backend_and_same_call(self):
        calls=[];body=NS(type='MESH',name='ExplicitBodyPointer')
        env,direct,result=request_env(lambda _:NS(body=body),calls)
        context=object();source=object()
        self.assertIs(env['_add_requested_physics'](context,source,True,capability='BOTH'),result)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],(context,source))
        self.assertEqual(set(calls[0][1]),{'backend','body','capability'})
        self.assertIs(calls[0][1]['backend'],direct);self.assertIs(calls[0][1]['body'],body)
        self.assertEqual(calls[0][1]['capability'],'BOTH')

    def test_missing_setup_body_and_nonmesh_reject_before_add(self):
        for setup in (None,NS(body=None),NS(body=NS(type='ARMATURE'))):
            calls=[];env,direct,result=request_env(lambda _,saved=setup:saved,calls)
            with self.subTest(setup=setup),self.assertRaisesRegex(ValueError,'actual Body mesh in Character Setup'):
                env['_add_requested_physics'](object(),object(),True)
            self.assertEqual(calls,[])

    def test_existing_delta_is_rejected_before_body_or_allocation(self):
        source=service.Source(rig=object());source.data=NS(shape_keys=None)
        record={'owner':'test','physics':{'backend':'ACTUAL_SURFACE_DELTA_V1'}};calls=[]
        def blocked(*args):self.fail('DELTA reached Body preflight/allocation')
        skirt=NS(RIG_KEY='rig',_require_controls_for_setup=lambda _:calls.append('controls'),
                 read_record=lambda _:(calls.append('read') or record))
        physics=NS(LEGACY_BACKEND='LEGACY_CAGE',backend=lambda value:value['physics']['backend'])
        env=service.loaded(('_install',),skirt=skirt,physics=physics,_body_preflight=blocked,
                           shared=NS(_Transaction=blocked))
        with self.assertRaisesRegex(service.DirectError,'DELTA-to-Direct migration is not validated'):
            env['_install'](object(),source,body=NS(type='MESH'))
        self.assertEqual(calls,['controls','read'])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Boundaries)
    for name in ('test_baked_manual_preview_keeps_cache_and_refuses_stale_automatic',
                 'test_manual_unknown_native_bake_state_refuses_before_writing',
                 'test_bake_readiness_only_accepts_enabled_automatic_output',
                 'test_reset_rejections_and_failed_sync_restore'):
        suite.addTest(service.DirectServiceTests(name))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():print('SOURCE_READY=True; canonical_unchanged=True; Native_executed=False; two_function_scope_only=True')
    raise SystemExit(0 if result.wasSuccessful() else 1)
