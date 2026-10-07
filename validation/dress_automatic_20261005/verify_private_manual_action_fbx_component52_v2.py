"""Private Manual bone Action v2: fixed pre-write ID closure; Root alone may run Native.

Frozen ab48 PNS input only, then a derived cdesigner-action-*/animation.blend.
Public Direct admission, production model binding, Unity and vertex Cloth remain
unverified. Two explicit in-memory test adaptations retain every Direct graph,
physical endpoint, sampling, FK and FBX gate. No runtime file is modified.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNTIME = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
REST = HERE/'verify_plain_rest_skin_fbx_component52.py'
REST_SHA = '9b93aab9edde5cbf6065e2e8ab9bf81ef27d07a79cd7cb9b792451f466e8564f'
ANIMATION_TEST = RUNTIME.parents[1]/'tests/test_animation_export_blender.py'
ANIMATION_TEST_SHA = '5d2fc6c7ddeadb8800b5f643ce83f194dd4068f2278ce5144d191e91594687c0'
RUNTIME_PINS = {
    'animation_export_worker': '87a4f850fd31583a55e7f610a46b6d3d35696d7f604986a0db371d3a088fe266',
    'bone_collections': 'aa92d856cbbd5df88f05fd700c7ba03c845d25b5941efcf5f23f46138d70a6c5',
    'control_colors': 'bf3668a58a1e5ac0290c1d2ced32ea4d8e32491eb90c2ee62c39a8f62dbdbcbf',
    'dress_export_guard': '4655c3a1de51cfd8560d8d084ab70f697bfde8cf8b3e6d5f434b323e314c8193',
    'dress_export_snapshot': 'a9949be8e5ad42c97fba3bd85c67e4fbb014188c29afe49bc538d2fc8ddd33e2',
    'eye_controls': '8be7a0247417b5e86b30e5ae49724863167e282b22bf1ebb899916076af61521',
    'foot_controls': 'f949f24175ae70d537bfe74bb6be5c0ea3abe72f62c55b842cedb553b6eeb2c3',
    'generated_names': 'a1c49790c61c31e915de15b1a4baa76c75be2b490a6d771eca179921fda4d931',
    'limb_fk_visuals': '228fbdcc2bd8226a9e2d871a25aff8d86df558098b2dcebba28c7a6ffbd405d6',
    'limb_ik': '5692ba78ed296ece885be5d519eb0f59152f4915784624c686880eee49d4dbf3',
    'limb_ik_fk': '9a2a3a3f43f3a4bf136bd42a5735521c26b167d4bc9b0268629bd128ddb4319c',
    'root_control': '243b62967ee08c61657886ed5cab74ca257b75a13bd6b8dad794e9483560e6af',
    'skirt_motion_profiles': 'be77e6f1fdcd6819ee46a3490515a0791b644900f286f04e287b5704706390e1',
    'skirt_original_mode': '8708cadca4d40f6c8f18c98e626019c2a47079a1f36443edebc666ff24da5ae7',
    'skirt_physics': '2d388f7de87ea4bb02e98f7fd28560003c3212a646682057cfe3ebfa0a3413e2',
    'skirt_rig': '0d56bc969f272cd884d1955a21a1c66a0afbeba2424e68b6b41802c71cf5de4c',
    'skirt_surface': 'a58d0e542bca195cd1d8e767e23e76809602bfe95b698668a8cc4b4289855c12',
    'skirt_surface_direct': 'e07634927c790323ffa70c19e52320ce0068fbd65e0447770ff515bea3fdd9c3',
    'skirt_topology': 'c6a1dd310a6968aa825f4281c3ff07386c9da0c763b732e31893fac30d3a511e',
    'spine_ik_fk': 'ad2e82fc9200af280befed0c55c745bc0ce3990f0120c638a6e906ae9f0a264f',
    'torso_controls': '37772c81e8142f5debd9674a6d4c424129a4579eeafbf9cedcef5f718f36b87a',
    'ui_constants': '17faafd78eac7429b05a59decf947d21ffacba029056c7cab9aff240e13f013e',
    'unity_export_worker': '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb',
}
LEGACY = HERE/'verify_private_manual_action_fbx_component52.py'
FAILED_RUN = HERE/'actual_private_manual_action_fbx_component_52_20261007_215111_796_2cf4430baf5b476e8030298b8306d2f1/result'
ID_MAP_PRIMARY = Path('D:/Blender5.2/5.2/scripts/modules/bpy_extras/id_map_utils.py')
HISTORY_PINS = {
    LEGACY: '25e6e3789f44abebdfb2c73c013f912d3833349330abf7a8bcf98322d4037f3a',
    FAILED_RUN/'report.json': 'a55eee8fa3c0458f0d9e227ad52855db605dad478b82653d656f9de9c91c47ce',
    FAILED_RUN/'cdesigner-action-manual-qa/animation.blend': 'ccd152153e0411c30ebfffce035f5a1b8ba91888a1c831ae4ac52f6e5d5e3691',
    ID_MAP_PRIMARY: 'cb37d61f9ea869f60696831a471bb73876d1156ff816c742cea8284ef1687d24',
}



def need(value, message):
    if not value:
        raise RuntimeError('PrivateManualAction52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_worker_node():
    """Remove only the public admission try from this private in-memory copy."""
    tree = ast.parse((RUNTIME/'animation_export_worker.py').read_text(encoding='utf-8'))
    original = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'export_job')
    node = copy.deepcopy(original)
    need(isinstance(node.body[0], ast.Try)
         and 'verify_animation_snapshot' in ast.unparse(node.body[0])
         and '_direct_export_guard' in ast.unparse(node.body[0]), 'Pinned public admission segment differs')
    removed = node.body.pop(0)
    node.name = 'private_component_export_job'
    restored = copy.deepcopy(node)
    restored.name = original.name
    restored.body.insert(0, removed)
    need(ast.dump(restored) == ast.dump(original), 'Private worker changed another execution segment')
    return ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), removed


def action_content(worker, action):
    # No original Action or Image library is repeatedly scanned at every sample.
    return [(curve.data_path, curve.array_index, curve.mute, curve.extrapolation,
             [(list(key.co), list(key.handle_left), list(key.handle_right), key.interpolation)
              for key in curve.keyframe_points],
             [(modifier.type, modifier.mute) for modifier in curve.modifiers])
            for curve in worker._curves(action)]


def id_reference_closure(roots, user_map, required=()):
    # Blender 5.2 bpy_extras.id_map_utils: dependency -> users is reversed.
    references = {}
    for dependency, users in user_map.items():
        for user in users:
            if user != dependency:
                references.setdefault(user, set()).add(dependency)
    reached = set(roots)
    pending = list(reached)
    while pending:
        for dependency in references.get(pending.pop(), ()):
            if dependency not in reached:
                reached.add(dependency)
                pending.append(dependency)
    need(set(required) <= reached, 'A required native ID is outside the fixed write-root closure')
    return reached


def snapshot_immutable_projection(original, mesh_names):
    raw = original['raw_named_weights_UV_Keys']
    need(mesh_names == sorted(set(mesh_names)) and set(mesh_names) <= set(raw),
         'The fixed snapshot Mesh name scope is ambiguous or absent from the original receipt')
    result = copy.deepcopy(original)
    result['raw_named_weights_UV_Keys'] = {name: raw[name] for name in mesh_names}
    return result


def snapshot_mesh_scope(expected, actual):
    # Compare type/name_full/library identities, never old native pointers.
    need(expected == sorted(set(expected), key=repr) and sorted(actual, key=repr) == expected,
         'Reopened snapshot Mesh identity inventory differs from the pre-write closure')
    return True


def asset_state(bpy, worker, names):
    return {'actions': {name: {'name': action.name, 'use_fake_user': action.use_fake_user,
                'is_action_layered': action.is_action_layered,
                'slots': [(slot.handle, slot.identifier, slot.target_id_type) for slot in action.slots],
                'curves': action_content(worker, action)}
                for name in names['actions'] for action in (bpy.data.actions[name],)},
            'materials': {name: [bpy.data.materials[name].use_nodes,
                bpy.data.materials[name].node_tree.name if bpy.data.materials[name].node_tree else None]
                for name in names['materials']},
            'images': {name: [str(Path(bpy.path.abspath(bpy.data.images[name].filepath)).resolve())
                if bpy.data.images[name].filepath else '', bpy.data.images[name].source,
                list(bpy.data.images[name].size), bpy.data.images[name].colorspace_settings.name]
                for name in names['images']}}


def immutable_state(bpy, q, rig, names):
    body_keys = bpy.data.objects['Cosha'].data.shape_keys
    return {'raw_named_weights_UV_Keys': {name: q.digest(q.raw_mesh_content(bpy.data.objects[name]))
                                         for name in names['meshes']},
            'named_Rest': q.digest(q.rest_content(rig)),
            'Body12': {'count': len(body_keys.key_blocks), 'eval_time': body_keys.eval_time,
                       'channels': [(key.name, key.value) for key in body_keys.key_blocks]}}


def sampled_source_state(q, worker, rig, action):
    return {'Rest': q.digest(q.rest_content(rig)), 'Action': action_content(worker, action),
            'constraints': [(bone.name, [(c.as_pointer(), c.type, c.name, c.mute, c.influence,
                c.target.as_pointer() if getattr(c, 'target', None) else None,
                getattr(c, 'subtarget', '') ) for c in bone.constraints]) for bone in rig.pose.bones],
            'drivers': [(c.as_pointer(), c.data_path, c.mute, c.driver.type, c.driver.expression,
                [(v.name, v.type, [(t.id.as_pointer() if t.id else None, t.data_path) for t in v.targets])
                 for v in c.driver.variables]) for c in rig.animation_data.drivers]}


def runtime_closure(rest):
    paths = set()
    for module in tuple(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if not path:
            continue
        path = Path(path).resolve()
        if path.parent == RUNTIME.resolve() and path.suffix == '.py':
            need(path.stem in RUNTIME_PINS and rest.sha(path) == RUNTIME_PINS[path.stem],
                 'An unpinned runtime module entered this private component: ' + str(path))
            paths.add(str(path))
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-script-sha', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE.resolve())
         and not args.output.exists(), 'Use one fresh owned Validation output')
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(scope='PRIVATE_MANUAL_BONE_ACTION_FBX_COMPONENT_V2_FIXED_ROOT_CLOSURE_ONLY', errors=[],
        native_component_verified=False, FBX_roundtrip_verified=False, input_author_restored=False,
        snapshot_raw_named_weights_Rest_Body12_assets_exact=False, sampled_source_protected=False,
        owned_native_cleanup=False, private_scene_disposed=False, pinned_files_unchanged=False,
        public_admission_verified=False, public_export_verified=False, production_model_binding_verified=False,
        Unity_verified=False, Magica_verified=False, simulation_baked=False,
        vertex_Cloth_carried_by_bones=False, final_surface_equivalent=False, export_accepted=False,
        material_texture_roundtrip_verified=False, current_X_loaded=False)
    report['asset_protection_scope'] = ('Original Action name/fake-user/layered flag, slot handle/identifier/target ID type, '
        'curve paths/keys/handles and modifier type/mute; Body12 eval_time and named key values; '
        'original material/node-tree references and image file identity/size/colorspace metadata. '
        'No complete material-node/image-pixel fidelity audit; frozen input file bytes stay exact.')
    report['matrix_threshold_scope'] = ('Inherited animation component gates: static/reference native '
        'matrix component <2e-4, playable FBX component <4e-4; unchanged worker FK/TRS gates. '
        'This does not replace the separate REST model same-index mesh 0.05 mm gate.')

    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append({'name': label, 'seconds': time.perf_counter() - started})
        write()
        print(json.dumps({'ManualAction_phase': label}), flush=True)
        need(time.perf_counter() - started <= args.soft_seconds, 'Soft component budget exceeded')

    bpy = rest = inventory = home = boundary = prior_record = prior_prepare = None
    pins = {}
    try:
        need(sha(REST) == REST_SHA and sha(Path(__file__).resolve()) == args.expected_script_sha,
             'REST reader/self pin differs before helper execution')
        rest = load(REST, 'private_manual_rest_readers')
        pins = dict(rest.PINS)
        pins.update({REST: REST_SHA, ANIMATION_TEST: ANIMATION_TEST_SHA,
                     Path(__file__).resolve(): args.expected_script_sha})
        pins.update({RUNTIME/(name+'.py'): value for name, value in RUNTIME_PINS.items()})
        pins.update(HISTORY_PINS)
        phase('fixed_input_and_sources')
        need(all(rest.sha(path) == expected for path, expected in pins.items()), 'Fixed input/source pin differs')
        report['pins'] = {str(path): value for path, value in pins.items()}
        reference = json.loads(rest.PROOF.read_text(encoding='utf-8'))
        identity = reference['identity']
        need(reference['native_component_verified'] is True and not reference['errors']
             and identity == {'source': 'Dress', 'rig': 'CoshaRig', 'body': 'Cosha',
                 'owner': '857c5aaad1ac4160953847b083deba20', 'scene': 'Scene'}, 'Fixed PNS proof/identity differs')
        import bpy as native_bpy
        from mathutils import Matrix
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(),
             'Use only the fixed disposable Blender 5.2 executable')
        bpy.ops.wm.open_mainfile(filepath=str(rest.SNAPSHOT), load_ui=False)
        home = bpy.data.scenes.get(identity['scene'])
        source, rig, body = (bpy.data.objects[identity[key]] for key in ('source', 'rig', 'body'))
        need(home is not None and all(home.objects.get(obj.name) == obj for obj in (source, rig, body)),
             'Recorded PNS home membership differs')
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        q = rest.readers(rest.QA, ('digest', 'id_name', 'raw_mesh_content', 'rest_content', 'pose_channels'), bpy)
        worker = load(RUNTIME/'animation_export_worker.py', 'private_manual_worker_helpers')
        boundary = worker._dress_snapshot_helpers()
        package = boundary.__package__
        direct = __import__(package + '.skirt_surface_direct', fromlist=['skirt_surface_direct'])
        record = direct.skirt.read_record(source)
        need(record['owner'] == identity['owner'] and record['physics']['backend'] == direct.BACKEND
             and source.data.shape_keys is None and body.data.shape_keys is not None
             and len(body.data.shape_keys.key_blocks) == 12, 'Fixed Direct no-Key Dress/Body12 differs')
        direct.validate(source, rig, record)
        need(not any(m.show_viewport or m.show_render for obj in bpy.data.objects for m in obj.modifiers
                     if m.type == 'CLOTH'), 'No active Cloth is permitted before any QA frame evaluation')
        report['runtime_closure'] = runtime_closure(rest)
        originals = tuple(obj for obj in bpy.data.objects if obj.type in ('MESH', 'ARMATURE'))
        original_receipt = rest.author_receipt(bpy, q, originals)
        names = {kind: sorted(item.name for item in getattr(bpy.data, kind))
                 for kind in ('actions', 'materials', 'images')}
        names['meshes'] = sorted(obj.name for obj in bpy.data.objects if obj.type == 'MESH')
        original_assets = asset_state(bpy, worker, names)
        original_immutable = immutable_state(bpy, q, rig, names)
        ad = rig.animation_data_create()
        need(ad.action is None and not ad.nla_tracks and not ad.use_tweak_mode,
             'Fixed PNS must have no assigned Action/NLA before QA authoring')
        ad_before = {key: getattr(ad, key) for key in
                     ('use_nla', 'action_blend_type', 'action_influence', 'action_extrapolation')}
        frame_before = (home.frame_current, home.frame_subframe)
        mid = rig.pose.bones[record['controls']['chains'][0]['mid']]
        hip = rig.pose.bones['Hips']
        original_mode = __import__(package + '.skirt_original_mode', fromlist=['skirt_original_mode'])
        original_channels = {bone.name: original_mode._channels(bone) for bone in (mid, hip)}
        qa_action = bpy.data.actions.new('.QA Private Manual Bone Action')
        qa_slot = qa_action.slots.new(id_type='OBJECT', name=rig.name)
        action_path = args.output/'cdesigner-action-manual-qa/animation.blend'
        action_path.parent.mkdir()
        phase('three_frame_QA_and_derived_Action_snapshot')
        try:
            ad.action, ad.action_slot, ad.use_nla = qa_action, qa_slot, False
            ad.action_blend_type, ad.action_influence, ad.action_extrapolation = 'REPLACE', 1., 'HOLD'
            hip.rotation_mode = 'XYZ'
            mid_base, hip_base = mid.location.copy(), hip.rotation_euler.copy()
            for frame, displacement, bend in ((1, 0., 0.), (2, .02, .06), (3, -.01, -.035)):
                mid.location = mid_base
                mid.location.x += displacement
                mid.keyframe_insert('location', index=0, frame=frame)
                hip.rotation_euler = hip_base
                hip.rotation_euler.z += bend
                hip.keyframe_insert('rotation_euler', index=2, frame=frame)
            worker._frame(home, home.frame_current_final)
            bpy.context.view_layer.update()
            try:
                worker._direct_export_guard().animation_host_admission(bpy.data.objects, rig, qa_action, qa_slot.handle)
            except ValueError as error:
                need('Direct Dress export validation is pending' in str(error), 'Public admission failed for an unrelated reason')
                report['public_admission_refusal'] = str(error)
            else:
                raise RuntimeError('Public Direct admission unexpectedly opened')
            prior_record, prior_prepare = boundary._record, boundary.prepare_animation_snapshot

            def proved_record(obj):
                raw = obj.get(boundary.RECORD_KEY)
                parsed = json.loads(raw) if type(raw) is str else None
                if isinstance(parsed, dict) and parsed.get('physics', {}).get('backend') == direct.BACKEND:
                    need(obj.name == identity['source'] and obj == bpy.data.objects.get(identity['source'])
                         and parsed['owner'] == identity['owner'] and parsed['rig'] == identity['rig']
                         and obj.get(boundary.RIG_KEY) == bpy.data.objects[identity['rig']],
                         'Private proved-record seam encountered a different Direct source')
                    direct.validate(obj, obj[boundary.RIG_KEY], parsed)
                    return parsed
                return prior_record(obj)

            boundary._record = proved_record
            proofs = boundary.capture_animation_surfaces(bpy.context, rig, qa_action)
            need(len(proofs) == 1 and proofs[0]['source'] == source.name, 'One fully proved Direct subset is required')
            roots = boundary.snapshot_scene_roots(proofs)
            need(roots == {home}, 'The derived Action must retain the real native home Scene')
            # Freeze the exact transport roots before native library expansion.
            write_roots = {rig, qa_action, *roots, *tuple(bpy.data.actions),
                           *tuple(bpy.data.materials), *tuple(bpy.data.images)}
            role_names = {name for group in proofs[0]['roles'].values() for name in group}
            role_names.update(record['physics']['colliders'])
            custom_shapes = {bone.custom_shape for bone in rig.pose.bones if bone.custom_shape is not None}
            required_ids = {source, body, rig, home} | custom_shapes | set(direct._closure(source, rig, record))
            required_ids.update(bpy.data.objects[name] for name in role_names)
            report['derived_snapshot_scope'] = {
                'actual_private_write_roots': sorted((q.id_name(item) for item in write_roots), key=repr),
                'production_coordinator_roots': sorted((q.id_name(item) for item in {rig, qa_action, *roots}), key=repr),
                'extra_private_asset_audit_roots': 'All original Actions/materials/images; no orphan Mesh roots added',
                'required_native_ids': sorted((q.id_name(item) for item in required_ids), key=repr),
                'ID_reference_API_primary': str(ID_MAP_PRIMARY), 'ID_reference_API_primary_sha256': HISTORY_PINS[ID_MAP_PRIMARY],
                'closure_fixed_before_write': True, 'post_reopen_exists_filter_used': False}
            closed_ids = id_reference_closure(write_roots, bpy.data.user_map(), required_ids)
            closed_meshes = [item for item in closed_ids if isinstance(item, bpy.types.Object) and item.type == 'MESH']
            snapshot_names = dict(names, meshes=sorted(item.name for item in closed_meshes))
            snapshot_mesh_ids = sorted((q.id_name(item) for item in closed_meshes), key=repr)
            snapshot_immutable = snapshot_immutable_projection(original_immutable, snapshot_names['meshes'])
            report['derived_snapshot_scope'].update(
                referenced_native_ids=sorted((q.id_name(item) for item in closed_ids), key=repr),
                snapshot_mesh_objects=snapshot_names['meshes'], snapshot_mesh_identities=snapshot_mesh_ids,
                excluded_original_mesh_objects=sorted(set(names['meshes']) - set(snapshot_names['meshes'])),
                excluded_mesh_protection='Complete loaded-input author checks before/after writing and frozen file bytes; no derived Mesh content claim',
                projected_immutable_digest=q.digest(snapshot_immutable))
            before_write = immutable_state(bpy, q, rig, names)
            bpy.data.libraries.write(str(action_path), write_roots, path_remap='ABSOLUTE', compress=True)
            need(action_path.is_file() and immutable_state(bpy, q, rig, names) == before_write,
                 'Action library write changed original raw/named weights/Rest/Body12')
            job = {'rig': rig.name, 'action': qa_action.name, 'action_slot': qa_slot.handle,
                'frame_start': 1., 'frame_end': 3., 'fps': home.render.fps, 'fps_base': home.render.fps_base,
                'sample_rate': home.render.fps/home.render.fps_base, 'unit_scale': home.unit_settings.scale_length,
                'loop': False, 'name': qa_action.name, 'filename': 'private_manual_bone_action.fbx',
                'export_rig_name': identity['rig'], 'stage': str(args.output/'fbx'),
                'dress_surfaces': proofs, 'dress_snapshot_path': str(action_path), 'unsupported_channels': []}
        finally:
            ad.action = None
            for key, value in ad_before.items():
                setattr(ad, key, value)
            for bone in (mid, hip):
                original_mode._restore(bone, original_channels[bone.name])
            home.frame_set(frame_before[0], subframe=frame_before[1])
            bpy.context.view_layer.update()
            need(qa_action.users == 0, 'QA Action acquired an outside user in the loaded-only input')
            bpy.data.actions.remove(qa_action)
        report['input_author_restored'] = (rest.author_receipt(bpy, q, originals) == original_receipt
            and asset_state(bpy, worker, names) == original_assets
            and immutable_state(bpy, q, rig, names) == original_immutable)
        need(report['input_author_restored'], 'Loaded-only frozen input was not restored after library authoring')
        pins[action_path] = rest.sha(action_path)
        report['derived_Action_snapshot'] = {'path': str(action_path), 'sha256': pins[action_path],
            'parent_PNS_sha256': rest.PINS[rest.SNAPSHOT], 'roots_include_recorded_home': True,
            'selected_Action_assignment_only': True, 'original_asset_audit_roots_also_written': True,
            'public_admission_receipt_fabricated': False}
        phase('reopen_Action_and_complete_Direct_preflight')
        bpy.ops.wm.open_mainfile(filepath=str(action_path), load_ui=False)
        home = bpy.data.scenes.get(identity['scene'])
        source, rig, body = (bpy.data.objects[identity[key]] for key in ('source', 'rig', 'body'))
        need(home is not None and all(home.objects.get(obj.name) == obj for obj in (source, rig, body)),
             'Derived Action lost recorded native home membership')
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        report['snapshot_raw_named_weights_Rest_Body12_assets_exact'] = (
            snapshot_mesh_scope(snapshot_mesh_ids, [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
            and immutable_state(bpy, q, rig, snapshot_names) == snapshot_immutable
            and asset_state(bpy, worker, names) == original_assets)
        need(report['snapshot_raw_named_weights_Rest_Body12_assets_exact'], 'Derived Action lost original immutable inputs/assets')
        selected = bpy.data.actions[job['action']]
        direct.validate_snapshot(source, proofs[0])
        boundary._physical_animation_guard(source, direct.skirt.read_record(source), selected)
        # Independent native Manual oracle, using the unchanged existing preflight/strip.
        stripped = boundary.prepare_animation_snapshot(rig, proofs, selected, private_snapshot=str(action_path))
        direct._closure(source, rig, direct.skirt.read_record(source))
        need(stripped[0]['manual_original_preserved'] and stripped[0]['physics_omitted'], 'Manual omission semantics differ')
        ad = rig.animation_data_create()
        ad.action, ad.action_slot = selected, worker._slot(rig, selected, job['action_slot'])
        ad.use_nla, ad.action_blend_type, ad.action_influence, ad.action_extrapolation = False, 'REPLACE', 1., 'HOLD'
        helpers = worker._model_helpers()
        retained = [bone.name for bone in rig.data.bones if not helpers._is_control(bone)]
        normalization = Matrix.Translation(-rig.matrix_world.translation)
        reference_world = normalization @ rig.matrix_world
        expected_rest = {name: reference_world @ rig.data.bones[name].matrix_local for name in retained}
        expected, expected_worlds = [], []
        for frame in (1., 2., 3.):
            worker._frame(home, frame)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            expected_worlds.append(normalization @ evaluated.matrix_world)
            expected.append({name: normalization @ evaluated.matrix_world @ evaluated.pose.bones[name].matrix
                             for name in retained})
        defs = [name for chain in record['chains'] for name in chain['def']]
        relative = [{name: sample['Hips'].inverted() @ sample[name] for name in defs} for sample in expected]
        observed = max(abs(relative[index][name][i][j] - relative[0][name][i][j])
                       for index in (1, 2) for name in defs for i in range(4) for j in range(4))
        report['Manual_DEF_relative_Hips_motion_maxcomponent'] = observed
        need(observed > 1e-5, 'QA Manual control did not produce observable Dress DEF motion relative to Hips')
        # Reopen the untouched derived file; the actual component performs its own complete preflight and strip.
        bpy.ops.wm.open_mainfile(filepath=str(action_path), load_ui=False)
        home = bpy.data.scenes[identity['scene']]
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        source, rig, selected = bpy.data.objects[identity['source']], bpy.data.objects[identity['rig']], bpy.data.actions[job['action']]
        snapshot_mesh_scope(snapshot_mesh_ids, [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
        need(immutable_state(bpy, q, rig, snapshot_names) == snapshot_immutable
             and asset_state(bpy, worker, names) == original_assets, 'Untouched Action snapshot lost its fixed closure inputs/assets')

        def prepared_with_receipt(*values, **options):
            result = prior_prepare(*values, **options)
            direct._closure(source, rig, direct.skirt.read_record(source))
            report['source_after_strip'] = sampled_source_state(q, worker, rig, selected)
            report['strip_receipt'] = result
            return result

        boundary.prepare_animation_snapshot = prepared_with_receipt
        private_tree, removed = private_worker_node()
        report['private_adaptations'] = [
            {'module': str(RUNTIME/'animation_export_worker.py'), 'original_function': 'export_job',
             'removed_from_in_memory_copy_only': ast.unparse(removed),
             'all_other_worker_AST_unchanged': True, 'public_admission_verified': False},
            {'module': str(RUNTIME/'dress_export_snapshot.py'), 'function': '_record',
             'scope': 'Only fixed owned Dress; direct.validate still runs before returning its proved record',
             'physical_guard_and_prepare_strip_unchanged': True, 'disk_file_modified': False}]
        exec(compile(private_tree, str(RUNTIME/'animation_export_worker.py'), 'exec'), worker.__dict__)
        phase('private_selected_Action_FK_FBX_execution')
        result = worker.private_component_export_job(job)
        report['worker_result'] = result
        report['runtime_closure'] = runtime_closure(rest)
        need(result['ok'] is True and result['samples'] == 3 and set(result['bones']) == set(retained)
             and result['has_reference_frame'] is True and result['reference_frame'] == 0
             and result['playable_first_frame'] == 1 and result['playable_last_frame'] == 3
             and abs(result['duration'] - 2./(job['fps']/job['fps_base'])) < 1e-10
             and abs(result['effective_sample_rate']*result['duration'] - 2.) < 1e-10
             and result['maximum_bake_matrix_error'] < 2e-4,
             'Private worker did not produce the expected three-frame/reference skeleton')
        report['sampled_source_protected'] = sampled_source_state(q, worker, rig, selected) == report['source_after_strip']
        need(report['sampled_source_protected']
             and snapshot_mesh_scope(snapshot_mesh_ids, [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
             and immutable_state(bpy, q, rig, snapshot_names) == snapshot_immutable
             and asset_state(bpy, worker, names) == original_assets, 'Worker changed source Rest/raw/weights/Body12/assets')
        export_rig = bpy.data.objects[result['rig']]
        expected_parents = {bone.name: bone.parent.name if bone.parent else None for bone in export_rig.data.bones}
        fbx = args.output/'fbx'/result['filename']
        need(fbx.is_file() and rest.sha(fbx) == result['sha256'], 'Worker FBX receipt differs')
        report['fbx'] = {'path': str(fbx), 'sha256': result['sha256']}
        phase('static_and_animated_FBX_reimports')
        imported = []
        for animate in (False, True):
            scene = bpy.data.scenes.new('Private Manual ' + ('animated' if animate else 'static') + ' reimport')
            scene.unit_settings.system = 'METRIC'
            scene.unit_settings.scale_length = job['unit_scale']
            bpy.context.window.scene = scene
            imported_result = bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=animate, anim_offset=0,
                automatic_bone_orientation=False, force_connect_children=False, ignore_leaf_bones=False)
            arms = [obj for obj in scene.objects if obj.type == 'ARMATURE']
            need('FINISHED' in imported_result and len(arms) == 1 and not any(obj.type == 'MESH' for obj in scene.objects),
                 'Animation-only FBX import must have one skeleton and no meshes')
            arm = arms[0]
            need(set(arm.data.bones.keys()) == set(retained)
                 and {b.name: b.parent.name if b.parent else None for b in arm.data.bones} == expected_parents,
                 'Complete FBX bone names/parents differ')
            bpy.context.view_layer.update()
            static_error = rest.matrix_errors([expected_rest[name] for name in sorted(retained)],
                [arm.matrix_world @ arm.data.bones[name].matrix_local for name in sorted(retained)], job['unit_scale'])
            maximum = max(abs(actual[i][j] - expected_rest[name][i][j])
                for name in retained for actual in [arm.matrix_world @ arm.data.bones[name].matrix_local]
                for i in range(4) for j in range(4))
            need(maximum < 2e-4, 'Static FBX world Rest changed beyond the existing animation-test tolerance')
            root_error = max(abs(arm.matrix_world[i][j] - reference_world[i][j])
                             for i in range(4) for j in range(4))
            need(root_error < 2e-4, 'Static FBX normalized object root changed')
            imported.append({'use_anim': animate, 'all_bones': len(retained), 'names_parents_exact': True,
                'Rest_matrix_error': static_error, 'Rest_maximum_native_component': maximum,
                'normalized_root_maximum_native_component': root_error})
            if not animate:
                continue
            imported_action = arm.animation_data.action if arm.animation_data else None
            need(imported_action is not None and not arm.animation_data.nla_tracks, 'Imported selected Take/NLA differs')
            effective_rate = result['effective_sample_rate']
            need(abs(scene.render.fps/scene.render.fps_base - effective_rate) < 2e-5,
                 'Imported effective FBX sample rate differs')
            keys = [key.co.x for curve in worker._curves(imported_action) for key in curve.keyframe_points]
            need(keys and abs(min(keys)) < 2e-4
                 and abs(max(keys)/scene.render.fps - (result['duration'] + 1./effective_rate)) < 2e-5
                 and abs((result['playable_last_frame'] - result['playable_first_frame'])/effective_rate
                         - result['duration']) < 1e-10, 'FBX reference/Take duration changed')
            world_errors = []
            for index in range(4):
                frame = 0. if index == 0 else (index/effective_rate)*scene.render.fps
                worker._frame(scene, frame)
                bpy.context.view_layer.update()
                evaluated = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
                wanted = expected_rest if index == 0 else expected[index-1]
                wanted_world = reference_world if index == 0 else expected_worlds[index-1]
                root_error = max(abs(evaluated.matrix_world[i][j] - wanted_world[i][j])
                                 for i in range(4) for j in range(4))
                actual = {name: evaluated.matrix_world @ evaluated.pose.bones[name].matrix for name in retained}
                component = max(abs(actual[name][i][j] - wanted[name][i][j])
                                for name in retained for i in range(4) for j in range(4))
                need(max(component, root_error) < (2e-4 if index == 0 else 4e-4),
                     'FBX reference/playable sample differs from all retained native Manual bone matrices')
                world_errors.append({'reference': index == 0, 'playable_index': None if index == 0 else index-1,
                    'import_frame': frame, 'all_bones': len(retained), 'maximum_native_component': component,
                    'normalized_root_maximum_native_component': root_error,
                    'matrix_error': rest.matrix_errors([wanted[name] for name in sorted(retained)],
                        [actual[name] for name in sorted(retained)], job['unit_scale'])})
            imported[-1].update(Action_name=imported_action.name, samples=world_errors,
                source_duration_seconds=result['duration'], Take_duration_seconds=max(keys)/scene.render.fps,
                importer_frame_conversion='FBX seconds * integer scene.render.fps; reference frame included')
        report['reimports'] = imported
        need(sampled_source_state(q, worker, rig, selected) == report['source_after_strip']
             and snapshot_mesh_scope(snapshot_mesh_ids, [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
             and immutable_state(bpy, q, rig, snapshot_names) == snapshot_immutable
             and asset_state(bpy, worker, names) == original_assets,
             'FBX imports changed protected private source inputs or original asset metadata')
        report['FBX_roundtrip_verified'] = True
        phase('private_component_checks_complete')
    except Exception as error:
        report['errors'].append({'error': repr(error), 'traceback': traceback.format_exc()})
    finally:
        if boundary is not None:
            if prior_record is not None:
                boundary._record = prior_record
            if prior_prepare is not None:
                boundary.prepare_animation_snapshot = prior_prepare
        if bpy is not None:
            if inventory is not None:
                try:
                    report['cleanup'] = rest.cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                except Exception as error:
                    report['errors'].append({'owned_cleanup': repr(error)})
            try:
                result = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['private_scene_disposed'] = ('FINISHED' in result and not bpy.data.filepath
                                                    and len(bpy.data.objects) == 0)
            except Exception as error:
                report['errors'].append({'factory_disposal': repr(error)})
        try:
            report['pinned_files_unchanged'] = bool(rest and pins) and all(rest.sha(path) == value for path, value in pins.items())
        except Exception as error:
            report['errors'].append({'pins_after': repr(error)})
        report['native_component_verified'] = (report['FBX_roundtrip_verified'] and report['input_author_restored']
            and report['snapshot_raw_named_weights_Rest_Body12_assets_exact'] and report['sampled_source_protected']
            and report['owned_native_cleanup'] and report['private_scene_disposed']
            and report['pinned_files_unchanged'] and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter() - started
        write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors']}), flush=True)
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
