"""SOURCE PREPARED: saved-disk private Scene closure, native high-leg + paired hold.

No Artist load/save, public Recalculate hookup, world-mesh interpolation or render.
The first native800/final3040 seed must be measured clear before another step.
"""
import argparse
import ast
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNTIME = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
PARENT = HERE/'verify_direct_original_leg_contact52_v3.py'
PARENT_SHA = '9b6ed084c34e4cdfdf3dad5992001e6e639a71078170e12dcecb77ab36ec84bf'
PARENT_REPORT = HERE/'actual_direct_original_leg_contact_v3_e0b_52_20261007_150150_739_f37d7377be5243b485f70f08caa29c4e/result/report.json'
PARENT_REPORT_SHA = '93e254a1dd85dd7485db66459a37043348804a6b10f83cac725b6dc299ac5d4e'
ARITHMETIC = HERE/'verify_direct_same_frame_recalculate52.py'
ARITHMETIC_SHA = 'ef014aaa2d573ab8ddb5001b43594370d24d3b6fe6b5753e4c42997e03b8caab'
INPUT = HERE/'private_current_controls_input_20261008_140155_539_56f2fda074bc44a1b195a3e6ea21fb54/X.controls-only-input.blend'
INPUT_SHA = '5bf64e5463fc46c625b5796852666fce251e2c0cd25dbe8aa39427a964df7812'
INPUT_RECEIPT = INPUT.parent/'input-receipt.json'
INPUT_RECEIPT_SHA = '81b0984aa604402cdd9f25f610b036d0a10f44e7daa357a097761d63be9933f3'
# Current Dress/Original endpoints are separate from the frozen historical reader
# pins. Registration's complete source tree is also bound by the CLI manifest and
# audited before/after; this list does not claim all imported modules are executed.
CURRENT_PINS = {
    '__init__.py': 'b4cd30708ee661a775068f62441d6b2bff528d3c17eb5c3a8e3b99821f625e92',
    'skirt.py': '4141430d5e691ca94ce8d9303bf1fe54f780bc3cb0bb06c1ef00e383f079d727',
    'skirt_rig.py': '0d56bc969f272cd884d1955a21a1c66a0afbeba2424e68b6b41802c71cf5de4c',
    'skirt_shared_rig.py': 'd31f7c8840617ea598053177cfb03c9b8e28dcf156ed932b684789b5ba630a14',
    'skirt_surface.py': 'a58d0e542bca195cd1d8e767e23e76809602bfe95b698668a8cc4b4289855c12',
    'skirt_surface_direct.py': '7ac0faf70d4cd8db6bec4bbf3c71aad4187b8b295aed542bc09534bd59dda0f5',
    'skirt_physics.py': '4a033b3bae40c3dba52cb4a522173c3a7532c84ca5c04ee55ad712af98a406d1',
    'skirt_topology.py': 'c6a1dd310a6968aa825f4281c3ff07386c9da0c763b732e31893fac30d3a511e',
    'skirt_motion_profiles.py': 'be77e6f1fdcd6819ee46a3490515a0791b644900f286f04e287b5704706390e1',
    'skirt_motion_tuning.py': '95fe79380b63f2b424f1df60f8b26f9a4ad4a54119fcc3eb4f2e83547e21f3ea',
    'skirt_original_mode.py': 'd382e40c2be9771dd0ae6ac2bf7b3b668108535c8f930e2695702ee19d7e25ff',
    'skirt_motion_ui.py': 'd4d6ab9173c11778447752215c75a6993438bf76fb494933047381f08c683430',
    'body_original_mode.py': 'd2d8e122c77a56ef314893470a197107462235aff159a05254fa7146e1e8b661',
    'body_rest_resync.py': '41d048dbb8892d8d1baea2f90d3335a7dc29ebb3124e9b220be6048687301c03',
    'character_setup.py': '8e6a2f3b7cdb2470d45ed0441a589d35ed2ec5ddea7ea828a0c5b0222d5677f9',
    'limb_ik.py': '5692ba78ed296ece885be5d519eb0f59152f4915784624c686880eee49d4dbf3',
    'limb_ik_fk.py': '9a2a3a3f43f3a4bf136bd42a5735521c26b167d4bc9b0268629bd128ddb4319c',
    'limb_fk_visuals.py': '228fbdcc2bd8226a9e2d871a25aff8d86df558098b2dcebba28c7a6ffbd405d6',
    'foot_controls.py': 'f949f24175ae70d537bfe74bb6be5c0ea3abe72f62c55b842cedb553b6eeb2c3',
    'root_control.py': '243b62967ee08c61657886ed5cab74ca257b75a13bd6b8dad794e9483560e6af',
    'torso_controls.py': '37772c81e8142f5debd9674a6d4c424129a4579eeafbf9cedcef5f718f36b87a',
    'spine_ik_fk.py': 'ad2e82fc9200af280befed0c55c745bc0ce3990f0120c638a6e906ae9f0a264f',
    'eye_controls.py': '8be7a0247417b5e86b30e5ae49724863167e282b22bf1ebb899916076af61521',
    'bone_collections.py': 'aa92d856cbbd5df88f05fd700c7ba03c845d25b5941efcf5f23f46138d70a6c5',
    'bone_display.py': '733adce1dd9d10cf41d0fb4916ed1b54337f83f8c0b1bf7cd8a000f6fcc9ab13',
    'generated_names.py': 'a1c49790c61c31e915de15b1a4baa76c75be2b490a6d771eca179921fda4d931',
    'control_colors.py': 'bf3668a58a1e5ac0290c1d2ced32ea4d8e32491eb90c2ee62c39a8f62dbdbcbf',
    'bone_color_palette.py': 'c0fb02f35bd9f1eaaf75307bad71d537180c82ad7f1b52e43ca1d75359e0629d',
    'control_pose_assets.py': '61b2750df48247e024a90f7b27a359344b298253f62440ce351cdb4cfecae3a4',
    'control_pose_capture.py': '461ddba7fe2f6bc71038f01364f6d90f34d0b5f96ecb3c2a536952aaa9db569a',
    'mesh_copy.py': 'a43aabff39a1ed9525df53352b859943a5571edeb30405d34338a5bebf264150',
    'forearm_twist.py': '4f159b83a2bac2aebbc9e23f03ce958da75a10728d0f21010f1178b476d66bf3',
    'forearm_original_inventory.py': '28a86885c5cba5579cd054a41d27933787f33ec0d19cf452f4a858da4ca069ac',
    'forearm_twist_math.py': 'bf32b47bdb11b897467b8606578baaff8acc218150ed3dab83cced03e364c421',
    'forearm_twist_topology.py': '01a7fb1a13451971b58ae49ffe1295a25c8344d9726fd3606825a063a2274f18',
    'forearm_twist_profile.py': '71f9c61af778bb26bddbb23ef334a8dd1a39928a84c5e8fea3145ffc5d1ff947',
    'forearm_twist_edit.py': '23b794256a6760c20747cc86cabb83a4db6abb20cba6842c6a09a383fde716e5',
    'forearm_twist_cache.py': '963ba3c447ed691a2a76f9ca6249cedb3cb57b7276033109f286acefdc3288ce',
    'forearm_twist_symmetry.py': '620c7b85ca2352caa5d0391162657ff1f5564d1d57ed0cd6ff34f8105703b6f3',
    'ui_constants.py': '17faafd78eac7429b05a59decf947d21ffacba029056c7cab9aff240e13f013e',
}
LEG_ANGLE_RAD = -math.radians(75.)
WARM_FRAMES, PAIR_FRAMES = 60, 100
ENDPOINTS = (1, 31, 60, 73, 100)
CONTACT_LABELS = tuple(('A_' if branch == 'A' else 'B_') +
                       ({1:'N1', 31:'Lmid31', 60:'Ltarget60', 73:'hold73', 100:'hold100'}[index])
                       for branch in ('A', 'B') for index in ENDPOINTS)


def need(value, message):
    if not value:
        raise RuntimeError('NativeWarmStart52: ' + message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def load(path, expected, name):
    need(sha(path) == expected, 'Frozen source changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_state(path):
    before = path.stat(); value = sha(path); after = path.stat()
    need((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'File changed during read')
    return dict(path=str(path.resolve()), bytes=after.st_size, mtime_ns=after.st_mtime_ns, sha256=value)


def disk_inputs():
    need(sha(INPUT_RECEIPT) == INPUT_RECEIPT_SHA, 'Exact Root copy receipt required')
    row = json.loads(INPUT_RECEIPT.read_text(encoding='utf-8'))
    need(set(row) == {'scope','artistPath','artistLogicalDirectory','artistSha256','artistLength',
        'artistModifiedUtcTicks','copiedPath','copiedSha256','copiedLength','sourceDiskBeforeAfterExact',
        'liveUnsavedArtistIncluded','controlsOnlyNativeVerified','noStoredExternalCacheNativeVerified','createdUtc'},
        'Unknown copy receipt schema')
    artist = Path(row['artistPath'])
    need(artist.is_absolute() and artist.resolve() != INPUT.resolve()
         and Path(row['copiedPath']).resolve() == INPUT.resolve()
         and Path(row['artistLogicalDirectory']).resolve() == artist.parent.resolve()
         and row['sourceDiskBeforeAfterExact'] is True and row['liveUnsavedArtistIncluded'] is False
         and row['controlsOnlyNativeVerified'] is False and row['noStoredExternalCacheNativeVerified'] is False,
         'Private saved-disk receipt boundary differs')
    for field in ('artistLength','copiedLength','artistModifiedUtcTicks'):
        need(type(row[field]) is int and row[field] > 0, 'Exact Int64 receipt fields required')
    original, private = file_state(artist), file_state(INPUT)
    need(original['sha256'] == private['sha256'] == row['artistSha256'] == row['copiedSha256'] == INPUT_SHA
         and original['bytes'] == private['bytes'] == row['artistLength'] == row['copiedLength']
         and original['mtime_ns']//100 + 621355968000000000 == row['artistModifiedUtcTicks'],
         'Saved Artist or its fixed copy changed; no Native load')
    return dict(receipt=row, receipt_sha256=INPUT_RECEIPT_SHA, artist=original, private_input=private,
                live_unsaved_included=False, artist_loaded=False)


def label(phase, index):
    need(phase in ('A','B') and type(index) is int and 1 <= index <= PAIR_FRAMES, 'Owned paired100 interval required')
    return phase + '_' + {1:'N1',31:'Lmid31',60:'Ltarget60',73:'hold73',100:'hold100'}.get(index, str(index))


def recipe(original, phase, index):
    label(phase, index)
    value = copy.deepcopy(original('A', 1))
    ramp = min(1., (index-1)/(WARM_FRAMES-1))
    value['leg']['L'][0] = LEG_ANGLE_RAD*ramp*ramp*(3.-2.*ramp)
    if phase == 'B' and index > WARM_FRAMES:
        phase_value = min(1., (index-WARM_FRAMES-1)/12.)
        value['hem_fraction'] = phase_value*phase_value*(3.-2.*phase_value)
    return value


def raw_zero(row):
    cross = row.get('strict_Body_crossing', {})
    closed = row.get('closed3', [])
    return (cross.get('status') == 'measured' and cross.get('complete') is True
            and type(cross.get('actual_crossing_pair_count')) is int and cross['actual_crossing_pair_count'] == 0
            and row.get('Unknown_if_incomplete') is False and len(closed) == 3
            and all(value.get('all800', {}).get('sampled_vertices') == 800
                    and value['all800'].get('inside_vertices') == 0
                    and value['all800'].get('maximum_penetration_m') == 0. for value in closed))


def cloth800_contact(diag, winding, centered, q, physics, meshes, body_mesh, colliders,
                     graph, bounds, limit, epsilon, report, name, frame, write, metres):
    raw = dict(meshes['C800'], free_indices=list(range(800)))
    need(len(raw['points']) == 800, 'Actual Cloth800 missing')
    band = dict(bounds)
    positions = [(point-band['waist']).dot(band['up']) for mesh in (raw,body_mesh) for point in mesh['points']]
    band['lower'], band['upper'] = min(positions)-epsilon, max(positions)+epsilon
    cross = diag.triangle_crossings(raw, body_mesh, band, limit, epsilon)
    cross['complete'] = (cross.get('dress_region_triangles') == len(raw['triangles'])
                         and cross.get('body_region_triangles') == len(body_mesh['triangles']))
    unresolved = {key:len(cross[key]) for key in ('coplanar_unresolved','degenerate_unresolved','boundary_unresolved')}
    result = dict(strict_Body_crossing=cross, closed3=[], unresolved_counts=unresolved,
                  Unknown_if_incomplete=cross.get('status') != 'measured' or not cross['complete'] or any(unresolved.values()),
                  accepted=False, scope='All native Cloth800 vertices/triangles against actual Body and exact three proxies')
    for obj in colliders:
        physics._closed_collider(obj)
        native = winding.winding_closed_collider(centered,q,obj,graph,epsilon,report,name+'_C800',frame,write)
        result['closed3'].append(dict(object=obj.name,all800=q.collision_metrics(raw['points'],native,metres,range(800))))
    result['measured_zero'] = raw_zero(result)
    return result


def relay_contract(direct, context, source, rig, body, installed, clone, report, write):
    direct.validate(source, rig, installed)
    need(clone != body and clone.data != body.data and clone.data.users == 1
         and clone.data.shape_keys is None and not clone.data.vertices
         and [modifier.type for modifier in clone.modifiers] == ['NODES','COLLISION'],
         'Independent actual-Body Geometry Nodes relay required; shared Body Mesh refused')
    direct._body_node(source, installed)
    proof = direct._body_geometry_proof(context, body, clone)
    report['actual_private_relay_contract'] = proof; write()
    need(proof['native_same_graph'] is True and proof['maximum_m'] <= 2.e-6, 'Actual Body relay differs')


def pair_summary(rows, endpoints, cold, response, metres, report):
    a, b = rows['A'], rows['B']
    fields = ('index','frame','Body_world_sha256','Body_counts','native_Body_controls','native_Root_world')
    need(len(a) == len(b) == PAIR_FRAMES and all(all(field in row for field in fields) for row in a+b), 'Incomplete paired inputs')
    differences = [{'index':index,'field':field} for index,(left,right) in enumerate(zip(a,b),1)
                   for field in fields if left[field] != right[field]]
    report['paired_body_exact'] = dict(complete=True, exact=not differences, differences=differences,
        scope='Both native100 branches, same physical indices; Body mesh hash and six leg/root matrices exact')
    need(not differences, 'Manual branch changed paired Body input')
    prefix = {str(index):cold.error(endpoints['A',index]['final3040']['points'],
                                   endpoints['B',index]['final3040']['points'],metres)
              for index in (1,31,60)}
    report['same_input_prefix_final'] = prefix
    need(all(row['maximum_m'] <= 5.e-5 for row in prefix.values()), 'Same native prefix output differs beyond original50um guard')
    last_a, last_b = endpoints['A',PAIR_FRAMES], endpoints['B',PAIR_FRAMES]
    report['same_time_Manual_response'] = response(
        last_a['final3040']['points'],last_b['final3040']['points'],
        last_a['requested3040']['points'],last_b['requested3040']['points'],list(range(3040)),metres)
    report['same_time_Manual_input'] = cold.error(last_a['input800']['points'],last_b['input800']['points'],metres)
    signal = report['same_time_Manual_response']
    need(report['same_time_Manual_input']['maximum_m'] > 5.e-5
         and signal['response_rms_m'] > 0. and signal['same_time_dot_gain'] > 0., 'No measured correctly directed Manual surface response')
    report['Manual_fidelity_accepted'] = False
    report['response_scope'] = 'Actual same-time full3040 delta; no feasible-region, exact target fidelity or artwork claim'


def prepared_namespace():
    parent = load(PARENT,PARENT_SHA,'warm_start_frozen_originalleg_v3')
    n, _, original_source, ast_helper = parent.prepared_namespace()
    n['_MISSING_GLOBALS'] = ast_helper._BASE.missing_globals
    original = ast.parse(original_source).body[0]
    changed = copy.deepcopy(original)
    original_try = next(node for node in original.body if isinstance(node,ast.Try))
    new_try = next(node for node in changed.body if isinstance(node,ast.Try))
    old_recipe = n['_RECIPE']
    n.update(_RECIPE=lambda phase,index:recipe(old_recipe,phase,index),_LABEL=label,
             _CONTACT_LABELS=CONTACT_LABELS,_RAW_CONTACT=cloth800_contact,_RAW_ZERO=raw_zero,
             _RELAY=relay_contract,_PAIR=pair_summary,_LEG_ANGLE=LEG_ANGLE_RAD)
    nodes = [node for node in ast.parse(ARITHMETIC.read_text(encoding='utf-8')).body
             if isinstance(node,ast.FunctionDef) and node.name == 'response']
    need(sha(ARITHMETIC) == ARITHMETIC_SHA and len(nodes) == 1, 'Frozen response observer changed')
    values = dict(need=need,math=math)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ARITHMETIC),'exec'),values)
    n['_RESPONSE'] = values['response']
    sample = next(node for node in new_try.body if isinstance(node,ast.FunctionDef) and node.name == 'sample')
    diagnosis = next(node for node in sample.body if isinstance(node,ast.If) and ast.unparse(node.test) == 'diagnose')
    marker = next(index for index,node in enumerate(diagnosis.body) if isinstance(node,ast.Assign)
                  and ast.unparse(node.targets[0]) == "row['contact']")
    extra = ast.parse("""row['cloth800_contact'] = _RAW_CONTACT(diag,winding,centered,q,physics,meshes,body_mesh,colliders,graph,bounds,args.triangle_pair_limit,epsilon,report,label,home.frame_current,write,metres)
contact['cloth800_contact'] = row['cloth800_contact']
if index == 1 and not manual:
    report.setdefault('seed_checks', []).append({'label':label,'native800_zero':_RAW_ZERO(row['cloth800_contact']),'final3040_zero':_ENDPOINT_ZERO(contact),'accepted':False})
    write()
    need(_ENDPOINT_ZERO(contact) and _RAW_ZERO(row['cloth800_contact']), 'Unsafe or Unknown native800/final3040 seed; no further warm-start steps')
""").body
    diagnosis.body[marker+1:marker+1] = extra
    phase = next(node for node in new_try.body if isinstance(node,ast.FunctionDef) and node.name == 'run_phase')
    for node in ast.walk(phase):
        if isinstance(node,ast.Call) and ast.unparse(node.func) == 'range' and [ast.unparse(arg) for arg in node.args] == ['1','31']:
            node.args[1] = ast.Constant(PAIR_FRAMES+1)
        elif isinstance(node,ast.BinOp) and ast.unparse(node) == 'start + 29':
            node.right = ast.Constant(PAIR_FRAMES-1)
        elif isinstance(node,ast.Assign) and ast.unparse(node.targets[0]) == 'label':
            node.value = ast.parse('_LABEL(phase,index)',mode='eval').body
        elif isinstance(node,ast.Compare) and ast.unparse(node) == 'index in (1, 16, 30)':
            node.comparators[0] = ast.Tuple(elts=[ast.Constant(value) for value in ENDPOINTS],ctx=ast.Load())
        elif isinstance(node,ast.Constant) and isinstance(node.value,str) and 'owned30 interval' in node.value:
            node.value = node.value.replace('owned30 interval','owned100 interval')
    start = next(index for index,node in enumerate(new_try.body) if isinstance(node,ast.Assign)
                 and ast.unparse(node.targets[0]) == 'same_frame')
    new_try.body[start:] = ast.parse("""_RELAY(direct,context,source,rig,body,installed,clone,report,write)
report['movement_plan'] = {'leg_delta_radians':_LEG_ANGLE,'leg_delta_degrees':75.,'warm_frames':60,'paired_frames_per_branch':100,'Manual_ramp_frames':12,'Manual_final_hold_frames':27,'native_Body_height_world':height,'Hem_local_delta':list(hem_delta),'rig_world':world_evidence,'Root_rest':rest_evidence,'axis_mapping':'Passed OriginalLeg native rest-inverse world+X quaternion input mechanism; high75 amplitude and slower60 ramp are new, not borrowed acceptance','no_pose_mode_or_matrix_setter':True,'accepted':False}
run_phase('A')
run_phase('B')
_PAIR(phase_rows,endpoints,cold,_RESPONSE,metres,report)
report['complete_final_contacts'] = len(contacts) == len(_CONTACT_LABELS) and [row['label'] for row in contacts] == list(_CONTACT_LABELS) and all(_ENDPOINT_ZERO(row) for row in contacts)
report['C800_vs_final3040'] = [{'label':row['label'],'C800_zero':_RAW_ZERO(row['cloth800_contact']),'final3040_zero':_ENDPOINT_ZERO(row)} for row in contacts]
report['native_stages_completed'] = True
write()
need(report['complete_final_contacts'], 'Final3040 has actual Body/proxy crossings or Unknown; no warm-start contact acceptance')
""").body
    need(ast.dump(ast.Module(body=new_try.finalbody,type_ignores=[])) ==
         ast.dump(ast.Module(body=original_try.finalbody,type_ignores=[])), 'Original Body12/Original/selection/physics cleanup finally changed')
    n.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[changed],type_ignores=[])),str(Path(__file__).resolve()),'exec'),n)
    return n, parent, original, changed


def owned_inputs(bpy, scene, source, rig, body, report, write):
    entry = dict(completed=False, external_blend_libraries=[library.filepath for library in bpy.data.libraries],
                 IDs=[], simulation_objects=[obj.name for obj in scene.objects])
    report['owned_native_input_preflight'] = entry; write()
    need(not entry['external_blend_libraries'], 'External linked Blend dependency refused; no original library/cache operation')
    for group in ('scenes','objects','meshes','armatures','shape_keys','actions','node_groups','collections'):
        for item in getattr(bpy.data,group):
            row = dict(kind=group,name=item.name,library=None if item.library is None else item.library.filepath,
                       override=item.override_library is not None)
            entry['IDs'].append(row)
            if row['library'] is not None or row['override']:
                write(); need(False, 'Non-owned simulation/author ID refused: ' + item.name)
        write()
    need(all(scene.objects.get(obj.name) == obj for obj in (source,rig,body))
         and source.data is not body.data and body.data.users == 1,
         'Explicit owned Scene Body/Dress/rig inputs differ')
    entry['completed'] = True; write()


def storage_preflight(bpy, scene, source, record, report, write):
    entry = dict(controls_only=False,stored_external_cache_refused=False,caches=[],source_cache_operations=0,completed=False)
    report['input_native_preflight'] = entry; write()
    need(not record.get('physics') and not any(mod.type in {'CLOTH','SOFT_BODY'} for mod in source.modifiers),
         'Actual private input must be controls-only; do not remove its physics/cache')
    entry['controls_only'] = True; write()
    caches = []
    for obj in scene.objects:
        for modifier in obj.modifiers:
            if hasattr(modifier,'point_cache'):
                caches.append((obj.name+'/'+modifier.name,modifier.point_cache))
        for system in obj.particle_systems:
            caches.append((obj.name+'/'+system.name,system.point_cache))
    if scene.rigidbody_world is not None:
        caches.append(('RigidBodyWorld',scene.rigidbody_world.point_cache))
    for name,cache in caches:
        row = {field:getattr(cache,field) for field in
               ('is_baked','is_baking','use_disk_cache','use_external','filepath','info','frame_start','frame_end')}
        row['owner'] = name; entry['caches'].append(row); write()
        need(not any(row[field] for field in ('is_baked','is_baking','use_disk_cache','use_external'))
             and (not row['info'] or row['info'].startswith('0 frames in memory (0 B)')),
             'Stored/unsafe private-input cache refused without Reset/free/delete: ' + name)
    entry['stored_external_cache_refused'] = entry['completed'] = True; write()
    return entry


def image_paths(bpy, logical_directory):
    rows = []
    for image in bpy.data.images:
        raw = image.filepath
        resolved = None if not raw else (logical_directory/raw[2:] if raw.startswith('//')
                   else Path(raw) if Path(raw).is_absolute() else logical_directory/raw)
        rows.append(dict(image=image.name,raw=raw,resolved_readonly=None if resolved is None else str(resolved.resolve()),
                         exists=None if resolved is None else resolved.is_file(),packed=image.packed_file is not None,
                         filepath_modified=False,texture_pixels_verified=False))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-source-manifest-sha',required=True)
    parser.add_argument('--scene',required=True)
    parser.add_argument('--body-object',default='Cosha'); parser.add_argument('--dress-object',default='Dress')
    parser.add_argument('--soft-seconds',type=float,default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(), 'Fresh private output only')
    need(0. < args.soft_seconds <= 180. and len(args.expected_source_manifest_sha) == 64
         and all(value in '0123456789abcdef' for value in args.expected_source_manifest_sha), 'Bounded exact source admission required')
    n,parent,_,_ = prepared_namespace(); base = n['load'](n['BASE'],n['BASE_SHA'],'warm_start_reader_parent')
    cold = n['load'](base.COLD,base.COLD_SHA,'warm_start_cold_readers')
    p = n['load'](cold.COMPARATOR,cold.COMPARATOR_SHA,'warm_start_raw_readers')
    manifest = n['load'](p.SOURCE,p.SOURCE_SHA,'warm_start_manifest')
    locator = n['load'](cold.LOCATOR,cold.LOCATOR_SHA,'warm_start_explicit_locator')
    pins = {**n['_EXTRA_PINS'],PARENT:PARENT_SHA,PARENT_REPORT:PARENT_REPORT_SHA,ARITHMETIC:ARITHMETIC_SHA,
            base.COLD:base.COLD_SHA,cold.COMPARATOR:cold.COMPARATOR_SHA,cold.LOCATOR:cold.LOCATOR_SHA,
            p.QA:p.QA_SHA,p.SOURCE:p.SOURCE_SHA,INPUT:INPUT_SHA,INPUT_RECEIPT:INPUT_RECEIPT_SHA,
            Path(__file__).resolve():sha(__file__),**{RUNTIME/name:value for name,value in CURRENT_PINS.items()}}
    need(CURRENT_PINS and all(sha(path) == value for path,value in pins.items()), 'Prepared current or frozen historical pin changed')
    before = manifest.current_manifest(); inputs_before = disk_inputs()
    need(n['digest'](before) == args.expected_source_manifest_sha, 'Actual current full source manifest differs')
    import bpy
    need(bpy.app.background and bpy.app.version[:2] == (5,2) and '--factory-startup' in sys.argv
         and '--disable-autoexec' in sys.argv and not bpy.data.filepath
         and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(), 'Empty protected factory5.2 only')
    need(any(flag in sys.argv and sys.argv[sys.argv.index(flag)+1] == '1' for flag in ('-t','--threads')), 'Owned one-thread child required')
    args.render=False; args.body_vertex_limit=100000; args.triangle_pair_limit=20000
    args.output.mkdir(); started=time.perf_counter(); registration_attempted=False; package=None
    report = dict(stage='PRIVATE_SAVED_DISK_NATIVE_WARM_START_V1_52',source_prepared_only=False,
        native_stages_completed=False,native_component_verified=False,accepted=False,effect_accepted=False,
        ART_accepted=False,current_artist_verified=False,current_live_unsaved_verified=False,
        Unity_verified=False,export_accepted=False,public_Recalculate_supported=False,artist_saved=False,deployed=False,
        material_texture_verified=False,rendered=False,source_before=before,input_before=inputs_before,errors=[],
        full_walk_run_squat_stop_final_surface_accepted=False,all_time_contact_verified=False,
        closed_Body_volume_verified=False,self_intersection_verified=False,
        source_manifest_sha256=n['digest'](before),pins={str(path):value for path,value in pins.items()},
        scope='Only owned child Scene closure from fixed saved-disk copy; no original Artist or source cache load/operation',
        historical_parent=dict(path=str(PARENT),sha256=PARENT_SHA,report=str(PARENT_REPORT),report_sha256=PARENT_REPORT_SHA,
            runtime_provider_sha=n['PROVIDER_SHA'],runtime_skirt_sha=n['SKIRT_SHA'],current_input_equivalence_claimed=False),
        runtime=dict(process_id=os.getpid(),binary=bpy.app.binary_path,version=list(bpy.app.version)),
        current_runtime_pins=CURRENT_PINS,old_sameframe_shared_Body_assumption_reused=False,
        path='Native quaternion high75deg over60 steps then two matched40 holds; no mesh interpolation or own animation/Key creation')
    def write():
        target=args.output/'report.json'; temporary=args.output/'report.json.part'
        temporary.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
        os.replace(temporary,target)
    def budget():
        need(time.perf_counter()-started < args.soft_seconds, 'Owned native budget exhausted')
    write()
    try:
        result=bpy.ops.wm.read_factory_settings(use_empty=True)
        report['initial_factory_empty']=('FINISHED' in result and not bpy.data.filepath
            and not any(len(getattr(bpy.data,key)) for key in
                ('objects','meshes','armatures','shape_keys','actions','materials','node_groups','images','collections')))
        write(); need(report['initial_factory_empty'],'Initial child factory is not empty; no library input load')
        with bpy.data.libraries.load(str(INPUT),link=False) as (available,requested):
            report['available_saved_scenes']=list(available.scenes); write()
            need(args.scene in available.scenes, 'Explicit saved Scene is missing; no fallback')
            requested.scenes=[args.scene]
        need(len(requested.scenes) == 1 and requested.scenes[0] is not None, 'Native private Scene closure load failed')
        scene=requested.scenes[0]; bpy.context.window.scene=scene
        q=p.readers(bpy); choices=[]
        _,rig,body,source,record=locator.locate_explicit(bpy,p,args.body_object,args.dress_object,choices)
        report['owned_scene_closure'] = dict(input=str(INPUT),input_sha256=INPUT_SHA,scene=scene.name,
            linked=False,all_native_IDs_in_owned_child=False,source_file_opened_as_Artist=False,explicit_selection=choices)
        owned_inputs(bpy,scene,source,rig,body,report,write)
        report['owned_scene_closure']['all_native_IDs_in_owned_child']=True; write()
        storage_preflight(bpy,scene,source,record,report,write)
        report['image_relative_paths_readonly']=image_paths(bpy,Path(inputs_before['receipt']['artistLogicalDirectory']))
        loaded=q.Protection(); pose=q.pose_channels(rig)
        sys.path.insert(0,str(RUNTIME.parent)); package=importlib.import_module('character_designer')
        registration_attempted=True; package.register()
        direct=importlib.import_module('character_designer.skirt_surface_direct')
        need(Path(direct.__file__).resolve() == (RUNTIME/'skirt_surface_direct.py').resolve()
             and loaded.verify()['success'] and q.pose_channels(rig) == pose, 'Canonical registration changed private authored input')
        report['private_authored_before_registration_exact']=True; write()
        n['exercise'](bpy,args,base,cold,p,q,direct,None,source,rig,body,report,write,budget)
    except Exception as error:
        report['errors'].append(dict(exception=repr(error),traceback=traceback.format_exc()))
    finally:
        if registration_attempted:
            try: package.unregister()
            except Exception as error: report['errors'].append(dict(unregister=repr(error)))
        try:
            result=bpy.ops.wm.read_factory_settings(use_empty=True)
            report['private_scene_disposed']=('FINISHED' in result and not bpy.data.filepath
                and not any(len(getattr(bpy.data,key)) for key in ('objects','meshes','armatures','shape_keys','actions','materials','node_groups','images','collections')))
            need(report['private_scene_disposed'], 'Owned private closure not disposed to empty factory')
        except Exception as error: report['errors'].append(dict(disposal=repr(error)))
        try:
            report['input_after']=disk_inputs(); report['source_after']=manifest.current_manifest()
            report['source_files_input_Artist_exact']=(report['input_after']==inputs_before
                and report['source_after']==before and all(sha(path)==value for path,value in pins.items()))
            need(report['source_files_input_Artist_exact'], 'Actual source/input/Artist file protection changed')
        except Exception as error: report['errors'].append(dict(final_guard=repr(error)))
        report['native_component_verified']=(report['native_stages_completed'] and report.get('complete_final_contacts') is True
            and report.get('paired_body_exact',{}).get('exact') is True and len(report.get('seed_checks',[])) == 2
            and report.get('source_files_input_Artist_exact') is True and report.get('private_scene_disposed') is True and not report['errors'])
        report['elapsed_seconds']=time.perf_counter()-started; write()
    print(json.dumps(dict(native_component_verified=report['native_component_verified'],report=str(args.output/'report.json'),errors=report['errors'])))
    return 0 if report['native_component_verified'] else 2


def pure_checks():
    from types import SimpleNamespace as NS
    n,parent,original,changed=prepared_namespace()
    n['base'] = None  # The real exercise binds this reader before calling run_motion.
    need(all(not n['_MISSING_GLOBALS'](n[name]) for name in ('run_motion','exercise')), 'Actual compiled closure incomplete')
    original_recipe=n['_PROG'].recipe
    for index in range(1,PAIR_FRAMES+1):
        a,b=recipe(original_recipe,'A',index),recipe(original_recipe,'B',index)
        need(a['leg']==b['leg'] and a['root_drop_fraction']==b['root_drop_fraction']==0., 'Manual changed Body recipe')
        if index<=WARM_FRAMES: need(a==b, 'Matched native warm prefix changed')
    need(recipe(original_recipe,'A',1)==original_recipe('A',1)
         and recipe(original_recipe,'A',60)['leg']['L'][0]==LEG_ANGLE_RAD
         and recipe(original_recipe,'A',100)['leg']['L'][0]==LEG_ANGLE_RAD,'Actual native75 target mapping differs')
    need(recipe(original_recipe,'B',61)['hem_fraction']==0. and recipe(original_recipe,'B',73)['hem_fraction']==recipe(original_recipe,'B',100)['hem_fraction']==1., 'Matched Manual hold mapping differs')
    need(not raw_zero({}) and not raw_zero(dict(Unknown_if_incomplete=True)), 'Unknown raw seed accepted')
    raw=dict(strict_Body_crossing=dict(status='measured',complete=True,actual_crossing_pair_count=0),Unknown_if_incomplete=False,
             closed3=[dict(all800=dict(sampled_vertices=800,inside_vertices=0,maximum_penetration_m=0.)) for _ in range(3)])
    need(raw_zero(raw), 'Exact raw seed control failed')
    raw['strict_Body_crossing']['actual_crossing_pair_count']=1
    need(not raw_zero(raw), 'Crossing raw seed accepted')
    raw['strict_Body_crossing']['actual_crossing_pair_count']=0; raw['closed3'][0]['all800']['inside_vertices']=1
    need(not raw_zero(raw), 'Inside raw seed accepted')
    # Execute the actual read-only storage guard with small endpoint fakes.
    # Each rejection must retain its actual read; no fake models or solver logic.
    values=dict(is_baked=False,is_baking=False,use_disk_cache=False,use_external=False,
                filepath='//untouched-cache',info='',frame_start=1,frame_end=250)
    cache=NS(**values); obj=NS(name='Owned',modifiers=[NS(name='Other',point_cache=cache)],particle_systems=[])
    scene=NS(objects=[obj],rigidbody_world=None); source=NS(modifiers=[])
    report={}; writes=[]
    need(storage_preflight(None,scene,source,{},report,lambda:writes.append(True))['completed'] is True,
         'Unstored cache read control failed')
    for field,value in (('is_baked',True),('use_external',True),('info','1 frame in memory (16 KiB)')):
        cache=NS(**dict(values,**{field:value})); obj.modifiers[0].point_cache=cache; report={}
        try: storage_preflight(None,scene,source,{},report,lambda:None)
        except RuntimeError: pass
        else: need(False,'Unsafe cache passed: '+field)
        entry=report['input_native_preflight']
        need(not entry['completed'] and entry['caches'][0][field]==value
             and vars(cache)==dict(values,**{field:value}) and entry['source_cache_operations']==0,
             'Unsafe cache read was lost or mutated')
    report={}
    try: storage_preflight(None,scene,source,{'physics':{'present':True}},report,lambda:None)
    except RuntimeError: pass
    else: need(False,'Existing source physics admitted')
    need(report['input_native_preflight']['controls_only'] is False,'False controls-only claim retained')
    report={}; bpy=NS(data=NS(libraries=[NS(filepath='D:/external-unowned.blend')]))
    try: owned_inputs(bpy,scene,None,None,None,report,lambda:None)
    except RuntimeError: pass
    else: need(False,'External linked Scene dependency admitted')
    need(report['owned_native_input_preflight']['completed'] is False,'Unknown ownership reported complete')
    need(all(sha(path)==value for path,value in n['_EXTRA_PINS'].items())
         and sha(PARENT_REPORT)==PARENT_REPORT_SHA
         and all(sha(RUNTIME/name)==value for name,value in CURRENT_PINS.items()), 'Frozen historical/current source read differs')
    disk_inputs()
    tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    need(not any(isinstance(node,ast.Call) and ast.unparse(node.func) in
         ('bpy.ops.wm.open_mainfile','bpy.ops.wm.save_as_mainfile','bpy.ops.wm.save_mainfile','points_on_path') for node in ast.walk(tree)), 'Artist load/save or world interpolation appeared')
    print(json.dumps(dict(source_prepared=True,native_run=False,real_native_leg_axis_mechanism_preserved=True,
        new_high_leg_degrees=75.,same_time_pair100=True,original_finally_AST_exact=True,unsafe_raw_seed_controls_rejected=3,
        unsafe_storage_or_external_ID_controls_rejected=5,partial_cache_evidence_retained=True,
        current_runtime_pins=len(CURRENT_PINS),copy_receipt_actual_read_verified=True,accepted=False)))


if __name__ == '__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
