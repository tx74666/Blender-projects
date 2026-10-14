"""Standalone UI runner admission only; no Blender/import/worker is launched."""
from copy import deepcopy
import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

PATH = Path(__file__).resolve().parents[1]/'tools/run_character_composition_ui_fixture.py'
SPEC = importlib.util.spec_from_file_location('standalone_composition_ui', PATH)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


def actual_source_model_api():
    """Execute the canonical helper's real body, with only bpy path adapter."""
    path = PATH.parents[1] / 'addons/character_designer/animation_link_source.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {'_sha256', '_source_model'}]
    namespace = {'Path': Path, 'hashlib': hashlib,
                 'bpy': NS(path=NS(abspath=lambda value: value)), '_error': ValueError}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return NS(_source_model=namespace['_source_model'])


def config():
    return dict(schema=driver.SCHEMA, inputBlend='D:/qa/artist_final_validation.blend',
        inputBlendSha256='1'*64, addonPackage='D:/frozen/character_designer',
        runtimeManifest='D:/frozen/python_projection.json', runtimeManifestSha256='2'*64,
        evidenceDirectory='D:/qa/ui-new', numericReport='D:/qa/numeric/composition_native_report.json',
        numericReportSha256='3'*64, seedBlend='D:/qa/numeric/qa_seed.blend', seedBlendSha256='4'*64,
        workItemId='11111111-1111-1111-1111-111111111111', sceneName='Composition QA · Fresh Workspace',
        rigName='CoshaRig', targetGuid='a'*32, modelSha256='5'*64,
        sessionHelper={'path':'D:/tools/composition_session_acceptance.py','sha256':'6'*64},
        sessionConfig={'createAWorkCopy':True,'seekSeconds':[.137,.419],'poseTolerance':2e-5})


def proofs(value):
    ids = ['1'*32, '7'*32]
    native_ids = ['8'*32, '9'*32]
    seed = dict(schema=driver.SEED_SCHEMA, seedBlend=value['seedBlend'], seedBlendSha256=value['seedBlendSha256'],
        sceneName=value['sceneName'], rigName='CoshaRig', rigSceneNames=sorted([value['sceneName'],'Scene']),
        targetGuid=value['targetGuid'], modelSha256=value['modelSha256'], workspacePath='D:/prepared/character_animation_workspace.json',
        workspaceSha256='b'*64, workItemIds=ids, itemIds=native_ids,
        physicalReport='D:/qa/physical/composition_sync_report.json', physicalReportSha256='c'*64)
    numeric = dict(schema='x.validation.character-composition-native/1', completed=True, numeric_completed=True,
        same_b_across_two_a_seek_and_object_motion=True, fresh_native_associations_verified=True,
        protected_prior_actions_unchanged=True, protected_assets_unchanged=True,
        fresh_workspace_cleanup='historical_native_state_and_rows_restored',
        qa_seed=seed, fresh_packet_proofs=[{'work_item_id':item_id,'model_sha256':value['modelSha256']} for item_id in ids],
        fresh_workspace_scene={'name':value['sceneName'],'historical_rig_scene_names':['Scene']})
    physical = dict(schema='x.validation.character-composition-sync/1', completed=True,
        physical_values_equal_foreground_and_two_a=True, actual_fbx_and_metadata_hashes_verified=True,
        items=[{'actualWorkItemId':item_id,'completed':True,'actual_fbx_and_metadata_hashes_verified':True,
            'kind':'SOURCE','newActionId':'','modelSha256':value['modelSha256']} for item_id in ids])
    original = {key:value[key] for key in ('inputBlend','inputBlendSha256','addonPackage','runtimeManifest','runtimeManifestSha256')}
    original.update(sceneName='Scene',compositionModelSha256=value['modelSha256'])
    return numeric, physical, original


class UiFixtureAdmissionTests(unittest.TestCase):
    def test_actual_source_model_Path_digest_tuple_is_unpacked_before_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'actual_character.fbx'
            model.write_bytes(b'actual isolated model bytes')
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            link = {'modelFile': str(model), 'modelSha256': digest}
            calls = []
            result = driver._pin_model(actual_source_model_api(), link, str(model), digest,
                                       lambda path, sha: calls.append((path, sha)))
            self.assertEqual(result, model.resolve())
            self.assertEqual(calls, [(model.resolve(), digest)])
            self.assertIsInstance(calls[0][0], Path)

    def test_actual_source_model_digest_mismatch_rejects_before_UI_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'actual_character.fbx'
            model.write_bytes(b'actual isolated model bytes')
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            calls = []
            with self.assertRaisesRegex(AssertionError, 'linked model digest'):
                driver._pin_model(actual_source_model_api(), {'modelFile': str(model), 'modelSha256': digest},
                                  str(model), '0' * 64, lambda *args: calls.append(args))
            self.assertEqual(calls, [])

    def test_actual_source_model_changed_bytes_remain_strictly_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / 'actual_character.fbx'
            model.write_bytes(b'before')
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            model.write_bytes(b'changed')
            calls = []
            with self.assertRaisesRegex(ValueError, 'model FBX changed'):
                driver._pin_model(actual_source_model_api(), {'modelFile': str(model), 'modelSha256': digest},
                                  str(model), digest, lambda *args: calls.append(args))
            self.assertEqual(calls, [])

    def test_complete_pinned_fixture_and_exact_tested_native_id_accept(self):
        value = config()
        self.assertIs(driver.validate_fixture(value), value)
        numeric, physical, original = proofs(value)
        seed, native_id = driver.validate_reports(value,numeric,physical,original)
        self.assertIs(seed,numeric['qa_seed'])
        self.assertEqual(native_id,'8'*32)

    def test_second_real_work_id_selects_its_own_native_id(self):
        value = config(); value['workItemId'] = '7'*32
        self.assertEqual(driver.validate_reports(value,*proofs(value))[1],'9'*32)

    def test_artist_or_same_input_seed_reject(self):
        for key,new in [('inputBlend','D:/Blender/Projects/Character/X/X.blend'),
                        ('seedBlend',config()['inputBlend'])]:
            value = config(); value[key] = new
            with self.assertRaises(AssertionError): driver.validate_fixture(value)

    def test_mutable_evidence_cannot_contain_seed_runtime_or_helper(self):
        for key in ('seedBlend','inputBlend','runtimeManifest','addonPackage','numericReport'):
            value = config(); value[key] = value['evidenceDirectory']+'/owned/'+Path(value[key]).name
            with self.assertRaises(AssertionError): driver.validate_fixture(value)
        value = config(); value['sessionHelper']['path'] = value['evidenceDirectory']+'/helper.py'
        with self.assertRaises(AssertionError): driver.validate_fixture(value)

    def test_relative_paths_missing_hash_or_invented_display_id_reject(self):
        for key,new in [('seedBlend','seed.blend'),('seedBlendSha256','unrecorded'),
                        ('workItemId','Walk_N'),('rigName','CoshaRig.001')]:
            value = config(); value[key] = new
            with self.assertRaises(AssertionError): driver.validate_fixture(value)

    def test_unknown_output_or_publication_options_reject(self):
        value = config(); value['allowPreparedLinkPublication'] = True
        with self.assertRaises(AssertionError): driver.validate_fixture(value)
        for key in ('evidenceDirectory','addonModule','sync'):
            value = config(); value['sessionConfig'][key] = 'foreign'
            with self.assertRaises(AssertionError): driver.validate_fixture(value)

    def test_nonfinite_or_weak_pose_and_seek_options_reject(self):
        for key,new in [('seekSeconds',[.1,float('nan')]),('seekSeconds',[.1,.1]),
                        ('poseTolerance',.001),('poseTolerance',True),('createAWorkCopy','yes')]:
            value = config(); value['sessionConfig'][key] = new
            with self.assertRaises(AssertionError): driver.validate_fixture(value)

    def test_optional_a_selection_requires_actual_uuid_and_control_name(self):
        value = config(); value['sessionConfig'].update(aWorkItemId='d'*32,rotationControl='hand.L')
        driver.validate_fixture(value)
        for key,new in [('aWorkItemId','A Walk'),('rotationControl','')]:
            changed = deepcopy(value); changed['sessionConfig'][key] = new
            with self.assertRaises(AssertionError): driver.validate_fixture(changed)

    def test_numeric_or_physical_pending_proof_reject(self):
        for target,key in [('numeric','completed'),('numeric','numeric_completed'),
                           ('physical','completed'),('physical','physical_values_equal_foreground_and_two_a'),
                           ('physical','actual_fbx_and_metadata_hashes_verified')]:
            value = config(); numeric,physical,original = proofs(value)
            (numeric if target=='numeric' else physical)[key] = False
            with self.assertRaises(AssertionError): driver.validate_reports(value,numeric,physical,original)

    def test_seed_work_ids_must_equal_both_actual_successful_proofs(self):
        for target in ('numeric','physical','seed'):
            value = config(); numeric,physical,original = proofs(value)
            if target=='numeric': numeric['fresh_packet_proofs'][0]['work_item_id'] = 'd'*32
            elif target=='physical': physical['items'][0]['actualWorkItemId'] = 'd'*32
            else: numeric['qa_seed']['workItemIds'][0] = 'd'*32
            with self.assertRaises(AssertionError): driver.validate_reports(value,numeric,physical,original)

    def test_untested_work_item_and_duplicate_native_receipt_id_reject(self):
        value = config(); value['workItemId'] = 'd'*32
        with self.assertRaises(AssertionError): driver.validate_reports(value,*proofs(value))
        value = config(); numeric,physical,original = proofs(value)
        numeric['qa_seed']['itemIds'][1] = numeric['qa_seed']['itemIds'][0]
        with self.assertRaises(AssertionError): driver.validate_reports(value,numeric,physical,original)

    def test_seed_model_original_input_and_projection_must_remain_exact(self):
        for key,new in [('modelSha256','d'*64),('inputBlendSha256','d'*64),
                        ('runtimeManifestSha256','d'*64),('sceneName','Another Scene')]:
            value = config(); numeric,physical,original = proofs(value); value[key] = new
            with self.assertRaises(AssertionError): driver.validate_reports(value,numeric,physical,original)

    def test_original_and_official_qa_memberships_are_preserved_exactly(self):
        value = config(); numeric,physical,original = proofs(value)
        for owners in [[value['sceneName']],[value['sceneName'],'Scene','Foreign'],['Scene']]:
            numeric['qa_seed']['rigSceneNames'] = owners
            with self.assertRaises(AssertionError): driver.validate_reports(value,numeric,physical,original)

    def test_all_pinned_historical_scene_memberships_are_retained(self):
        value = config(); numeric,physical,original = proofs(value)
        numeric['fresh_workspace_scene']['historical_rig_scene_names'].append('Another Authenticated Original Scene')
        numeric['qa_seed']['rigSceneNames'] = sorted([*numeric['fresh_workspace_scene']['historical_rig_scene_names'],value['sceneName']])
        driver.validate_reports(value,numeric,physical,original)

    def test_native_row_requires_unique_actual_ids_and_exact_rig(self):
        rig = object()
        row = NS(work_item_id='1'*32,item_id='8'*32,rig=rig,new_animation=False)
        saved = NS(items=[row])
        self.assertIs(driver.select_native_row(saved,rig,'1'*32,'8'*32),row)
        for changes in [{'item_id':'9'*32},{'rig':object()},{'new_animation':True}]:
            invalid = NS(**{**vars(row),**changes})
            with self.assertRaises(AssertionError): driver.select_native_row(NS(items=[invalid]),rig,'1'*32,'8'*32)
        with self.assertRaises(AssertionError): driver.select_native_row(NS(items=[row,row]),rig,'1'*32,'8'*32)

    def test_new_empty_evidence_and_owned_startup_cache_accept(self):
        with tempfile.TemporaryDirectory() as parent:
            value = config(); evidence = Path(parent)/'ui'; value['evidenceDirectory'] = str(evidence)
            cache = evidence/'datafiles'; cache.mkdir(parents=True)
            self.assertEqual(driver.claim_evidence(value,cache),evidence)

    def test_prior_reports_or_cache_files_are_never_overwritten(self):
        for location in ('report','cache'):
            with tempfile.TemporaryDirectory() as parent:
                value = config(); evidence = Path(parent)/'ui'; value['evidenceDirectory'] = str(evidence)
                cache = evidence/'datafiles'; cache.mkdir(parents=True)
                path = evidence/'old_report.json' if location=='report' else cache/'old_source.blend'
                path.write_bytes(b'prior evidence')
                with self.assertRaises(AssertionError): driver.claim_evidence(value,cache)
                self.assertEqual(path.read_bytes(),b'prior evidence')

    def test_foreign_or_root_datafiles_cache_reject(self):
        value = config()
        for cache in (value['evidenceDirectory'],'D:/shared-datafiles'):
            with self.assertRaises(AssertionError): driver.claim_evidence(value,cache)


if __name__ == '__main__':
    unittest.main()
