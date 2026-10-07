"""Disposable canonical cold stop60 with exact QA Body-Key coordinate restore.

Root alone runs BG5.2 serially. No 7ac load, copied legacy binding, imported clip,
Dress keys, artist save or parameter substitution. Collection is not acceptance.
"""
import argparse
import ast
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback
from types import SimpleNamespace as NS
from array import array

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
PROVIDER = REPO/'addons/character_designer/skirt_surface_direct.py'
PROVIDER_SHA = '0facebc081163b01612172d59202a17f4422568c8e88c27cf7608ed083f8be41'
COLD_PROOF = HERE/'actual_direct_cold_current_pose_v4_52_20261007_034418_213/report.json'
COLD_PROOF_SHA = '4807a237182654dc4fe6977dcd89c59394f84cd34816349363f07616cad24977'
FAILED_STOP = HERE/'actual_current_cold_stop_pose_52_20261007_035534_526/result/report.json'
FAILED_STOP_SHA = '3bce7768739568015376d23f631e2111d891fb36f2aa6e8776e634d067d7a49b'
PINS = {
    'verify_direct_cold_install52_v4.py': '4bb8e79fbad87950c75c1999e27d97657733ea42695df8e0f2b3a2ae4f58c536',
    'verify_live_direct_cloth52.py': '9646529e108a7ada6f04c17e013c8f70a558773e29b578ce6d00fbd97fc2f2a5',
    'verify_live_direct_cloth52_disposable_fixture_v6.py': 'bb040e1694612542b520c313d7b59e5ceb0fd3de5cfda75d1ffd422ef8160d94',
    'verify_live_direct_cloth52_movement_centered_collision.py': 'f1721a793a50e80bfd27cc641da5dd5355afe22926bc81fe8c89370332dc67ce',
    'verify_live_direct_cloth52_movement_winding_collision.py': '3ef6233443a3c7c1845afd5843daba13389e32dea89a661f54d2c9b24addfb77',
    'verify_live_direct_cloth52_progressive_manual.py': '0c6c2747123460a31bb67ca7fb3038eed27189dfc296dd0648cfbf569ebc8bd6',
    'diagnose_skin_transfer.py': '9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28',
    'validate_real_dress.py': '613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046',
}


def need(value, message):
    if not value:
        raise RuntimeError('DirectColdMotion52: ' + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(name):
    path = HERE/name
    need(sha(path) == PINS[name], 'Frozen reader/observer differs: ' + name)
    spec = importlib.util.spec_from_file_location('cold_motion_' + path.stem, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def critical_frames(recipe, case):
    rows = {i: recipe(case, i, 60) for i in range(1, 61)}
    result = {1, 30, 59, 60}
    for side in ('left', 'right'):
        result.add(max(rows, key=lambda i: rows[i][side]))
    need(len(result) == 6, 'Six distinct actual recipe contact samples required')
    if case == 'abrupt_stop_turn':
        result.update(stop_phase_frames(recipe).values())
    return sorted(result)


def stop_phase_frames(recipe):
    rows = {i:recipe('abrupt_stop_turn',i,60) for i in range(1,61)}
    distance = max(r['forward_height'] for r in rows.values())
    turn = max(r['turn'] for r in rows.values())
    need(math.isfinite(distance) and distance > 0. and turn == math.pi*.5,
         'Current original stop/turn recipe endpoints changed')
    stopped = min(i for i,r in rows.items() if r['forward_height'] == distance and r['left'] == r['right'] == 0.)
    completed = min(i for i,r in rows.items() if r['turn'] == turn and r['stopped'] is True)
    need(stopped < completed, 'Bounded actual translation-stop/turn-complete order required')
    return {'translation_stopped':stopped,'turn_completed':completed}


def coordinates(owner):
    values = array('f',[0.])* (len(owner)*3)
    need(values.itemsize == 4, 'Exact native Float32 array format unavailable')
    owner.foreach_get('co',values)
    need(all(math.isfinite(v) for v in values), 'Nonfinite native Body coordinates')
    return values


def key_identity(body):
    mesh,keys = body.data,body.data.shape_keys
    need(keys is not None and keys.reference_key is not None, 'Original Body Key identity missing')
    return {'Body':[body.as_pointer(),body.name], 'Mesh':[mesh.as_pointer(),mesh.name,len(mesh.vertices)],
        'Key':[keys.as_pointer(),keys.name,keys.use_relative,keys.reference_key.as_pointer()],
        'blocks':[[k.as_pointer(),k.name,len(k.data),None if k.relative_key is None else k.relative_key.as_pointer()]
                  for k in keys.key_blocks]}


def capture_body_coordinates(body):
    identity = key_identity(body)
    need(len({b[0] for b in identity['blocks']}) == len({b[1] for b in identity['blocks']}) == 12,
         'Native12-Key pointers/names are not unique')
    blocks = [coordinates(k.data) for k in body.data.shape_keys.key_blocks]
    need(len(blocks) == 12 and all(len(v) == 3*len(body.data.vertices) for v in blocks),
         'Original native12-Key coordinate/index coverage incomplete')
    return {'identity':identity,'blocks':blocks,'base':coordinates(body.data.vertices)}


def restore_body_coordinates(body,saved,report,write):
    entry = {'identity_before':saved['identity'],'status':'Unknown','accepted':False,
             'scope':'Private QA restores actual changed Key coordinates only; no runtime fix/artist save',
             'base_vertices_written':False,'diagnostic_cause_confirmed':False,'changed_keys':[]}
    report['Body_Key_coordinate_restore'] = entry;write()
    entry['identity_actual'] = key_identity(body);write()
    need(entry['identity_actual'] == saved['identity'], 'Body/mesh/12-Key pointer/name/order/count/relative identity changed')
    # Validate every finite block and raw base before the first write. A base
    # mesh mutation remains a hard failure; this scope never repairs its verts.
    current = [coordinates(k.data) for k in body.data.shape_keys.key_blocks]
    base = coordinates(body.data.vertices)
    entry['base_vertices_exact'] = base.tobytes() == saved['base'].tobytes()
    entry['float32_byte_order'] = sys.byteorder
    need(all(len(a)==len(b) for a,b in zip(current,saved['blocks'])), 'Native Key coordinate count changed')
    for index,(actual,original) in enumerate(zip(current,saved['blocks'])):
        if actual.tobytes() != original.tobytes():
            a,b = actual.tobytes(),original.tobytes()
            changed = [i for i in range(len(actual)//3) if a[i*12:(i+1)*12] != b[i*12:(i+1)*12]]
            delta = max(math.sqrt(sum((actual[i*3+j]-original[i*3+j])**2 for j in range(3))) for i in changed)
            entry['changed_keys'].append({'index':index,'name':body.data.shape_keys.key_blocks[index].name,
                'changed_vertices':len(changed),'maximum_BodyMesh_local_delta':delta,
                'actual_before_sha256':hashlib.sha256(a).hexdigest(),'saved_sha256':hashlib.sha256(b).hexdigest(),
                'coordinate_unit':'Body mesh local; physical metres not assumed'})
    write();need(entry['base_vertices_exact'], 'Raw Body base vertices changed; no Key-coordinate-only repair allowed')
    for item in entry['changed_keys']:
        body.data.shape_keys.key_blocks[item['index']].data.foreach_set('co',saved['blocks'][item['index']])
    if entry['changed_keys']:
        body.data.shape_keys.update_tag();body.data.update()
    observed = [coordinates(k.data) for k in body.data.shape_keys.key_blocks]
    entry['readback_float32_bytes_exact'] = [a.tobytes()==b.tobytes() for a,b in zip(observed,saved['blocks'])]
    entry['identity_after'] = key_identity(body)
    entry['base_vertices_after_exact'] = coordinates(body.data.vertices).tobytes() == saved['base'].tobytes()
    entry['status'] = 'restored' if all(entry['readback_float32_bytes_exact']) and entry['identity_after']==saved['identity'] and entry['base_vertices_after_exact'] else 'Unknown'
    write();need(entry['status'] == 'restored', 'Body Key exact coordinate readback/identity/base verification failed')


def run_motion(bpy, args, p, cold, q, diag, live, movement, winding, centered, progressive,
               direct, source, rig, body, record, report, write, budget):
    from mathutils import Quaternion, Vector
    from character_designer import skirt_physics as physics, skirt_motion_tuning as tuning, skirt_motion_profiles as profiles
    from character_designer import forearm_twist
    home, context = bpy.context.scene, bpy.context
    original = cold.receipt(bpy, p, q, direct, source, rig, body)
    protected = q.Protection()
    report['Body_input_baseline'] = {name: original[name] for name in
        ('raw_Body','Body_Key_channels','Body_Key_binding','Body_data_users','pose')}
    need(source.data.shape_keys is None and body.data.users == 1 and body.data.shape_keys is not None
         and len(body.data.shape_keys.key_blocks) == 12, 'Exact no-Dress-Key/Body12Key saved scope required')
    body_coordinates = capture_body_coordinates(body)
    report['Body_Key_coordinate_backup'] = {'identity':body_coordinates['identity'],
        'float32_byte_order':sys.byteorder,'key_coordinate_sha256':[hashlib.sha256(v.tobytes()).hexdigest() for v in body_coordinates['blocks']],
        'base_vertex_sha256':hashlib.sha256(body_coordinates['base'].tobytes()).hexdigest(),'captured_before_install':True}
    tx = direct.shared._Transaction(context, source); tx.remember_keys(body.data.shape_keys)
    animation = rig.animation_data
    old_action = None if animation is None else animation.action
    old_slot = None if animation is None else animation.action_slot
    old_nla = [] if animation is None else [(track, track.mute, track.is_solo) for track in animation.nla_tracks]
    old_autokey = home.tool_settings.use_keyframe_insert_auto
    requested = requested_data = cloth = None
    old_hem = None
    restore_errors = []
    try:
        # The one actual public cold install starts from saved controls only.
        installed = physics.add_physics(context, source, backend=direct.BACKEND, body=body, capability='BOTH')
        installed, actual_rig, c, cloth = physics.validate_physics(source)
        need(actual_rig == rig and installed['physics']['backend'] == direct.BACKEND, 'Public backend dispatch differs')
        tuning.apply(context, [source], mode='AUTOMATIC')
        installed, _, c, cloth = physics.validate_physics(source)
        input_obj = bpy.data.objects[installed['physics']['surface']['roles']['INPUT_SURFACE'][0]]
        clone = input_obj.modifiers[1].target
        colliders = [bpy.data.objects[n] for n in installed['physics']['colliders'][:-1]]
        profile = profiles.read(source, installed)
        need(profile['mode'] == 'AUTOMATIC' and profile['capability'] == 'BOTH'
             and cloth.settings.effector_weights.gravity == profile['settings']['gravity'] == 1.,
             'Current default gravity/profile differs; no old0.12 tuning substituted')
        report['native_defaults'] = {'profile': profile, 'cloth_settings': q.simple_rna(cloth.settings),
            'collision_settings': q.simple_rna(cloth.collision_settings), 'effectors': q.simple_rna(cloth.settings.effector_weights),
            'scene_gravity': list(home.gravity), 'scene_use_gravity': home.use_gravity,
            'colliders': {o.name: q.simple_rna(o.collision) for o in colliders+[clone]},
            'default_parameters_accepted': False}
        report['native_pipeline_RNA'] = {o.name: [{
            'type': m.type, 'is_active': m.is_active, 'RNA': direct.shared._rna(m),
            'is_bound': m.is_bound if m.type == 'SURFACE_DEFORM' else None} for m in o.modifiers]
            for o in (source,input_obj,c,clone,*colliders)}
        need(home.render.fps/home.render.fps_base == 30., 'Current native30fps required')
        metres = home.unit_settings.scale_length
        need(math.isfinite(metres) and metres > 0., 'Finite positive current scene metre scale required')
        # Current saved FK is an explicit prerequisite; never neutralize arms,
        # forearms, spine or Dress controls to make a test pass.
        legs, axes, height = q.body_inputs(rig, installed)
        root = rig.pose.bones['CTRL_master']
        thighs = {side: rig.pose.bones[legs[side]['chain'][0]] for side in ('L','R')}
        need(root.rotation_mode == 'XYZ' and all(b.rotation_mode == 'QUATERNION' for b in thighs.values()), 'Native RootXYZ/thighQuaternion required')
        old_location, old_euler = Vector(root.location), Vector(root.rotation_euler)
        old_rotations = {side: Quaternion(b.rotation_quaternion) for side,b in thighs.items()}
        plan = movement.native_plan(NS(movement_stress=True, case=args.case, frames=60), rig, root, home, metres)
        report['movement_plan'] = plan
        if animation is not None:
            animation.action = None
            for track, _mute, _solo in old_nla:
                track.mute, track.is_solo = True, False
        home.tool_settings.use_keyframe_insert_auto = False
        report['input_scope'] = {'unkeyed_native_pose_assignments': True, 'Dress_keys_created': 0, 'Body_Action_created': False,
            'author_actions_temporarily_detached': old_action is not None, 'all_other_pose_channels_preserved': True,
            'imported_clip': False, 'forearm_runtime_frozen_during_motion': False,
            'live_corrective_effects_accepted': False, 'artist_timeline_or_GUI_operated': False}
        # A private comparison object inherits ONLY this newly cold-bound input.
        requested = input_obj.copy(); requested.name = 'QA current cold requested'
        requested_data = input_obj.data.copy(); requested.data = requested_data
        for owner in (requested, requested_data):
            for key in list(owner.keys()): del owner[key]
        home.collection.objects.link(requested)
        requested.hide_render = requested.hide_select = True; requested.hide_set(True)
        need(requested.data.shape_keys is None and requested.modifiers[1].is_bound
             and requested.modifiers[1].target == clone and direct.shared._frame(requested) == direct.shared._frame(input_obj),
             'Private requested comparison lost the fresh native bind/chart')
        graph = context.evaluated_depsgraph_get()
        report['fresh_requested800_copy'] = cold.error(diag.mesh_snapshot(input_obj,graph)['points'],
            diag.mesh_snapshot(requested,graph)['points'],metres)
        need(report['fresh_requested800_copy']['maximum_m'] <= 5.e-5,
             'Fresh bound requested comparison differs beyond original50um input guard')
        need(source.modifiers[-1].type == 'SUBSURF', 'Original final Subsurf required')
        subdiv = requested.modifiers.new('QA same native Subsurf', 'SUBSURF')
        direct.shared._copy_scalars(source.modifiers[-1], subdiv)
        # Reset initializes this actual first recipe input, never frame39's
        # unrelated input. Every later sample still advances the native cache.
        first_move = live.input_recipe(args.case,1,60)
        root.location = old_location + Vector(movement.location_delta(first_move,plan))
        root.rotation_euler = old_euler + Vector((0.,0.,first_move['turn']))
        for side,bone in thighs.items():
            bone.rotation_quaternion = old_rotations[side] @ Quaternion(axes[bone.name],first_move['left' if side=='L' else 'right'])
        reset = physics.reset_simulation(context, source)
        start = reset['start']
        report['public_reset_receipt'] = {'result': reset, 'current_frame': [home.frame_current,home.frame_subframe],
            'native_cache': q.cache_state(cloth), 'state': direct._state(source,installed),
            'Cloth_flags': [cloth.show_viewport,cloth.show_render],
            'first_recipe':first_move, 'physics_parameters_changed':False,
            'held_recalculate_claimed':False}
        need(home.frame_current == start and home.frame_subframe == 0. and cloth.show_viewport
             and cloth.show_render and reset['is_baked'] is False, 'PublicReset did not resume actual start-frame Cloth')
        need(cloth.point_cache.frame_step == 1 and start+59 <= cloth.point_cache.frame_end, 'Owned60-frame cache interval unavailable')
        ring = installed['fit']['rings'][0]
        pins = physics._weights(c)[cloth.settings.vertex_group_mass]
        need(len(ring) == len(set(ring)) == 80 and {i for i,v in pins.items() if v == 1.} == set(ring), 'Actual hard80 native pin identity differs')
        indices = critical_frames(live.input_recipe, args.case)
        report['contact_indices'] = indices
        report['stop_phase_indices'] = stop_phase_frames(live.input_recipe)
        renderer = progressive.two_view_renderer(diag)
        samples, previous, held_frame = [], None, None
        def sample(label, index, *, held=False):
            nonlocal previous
            if held:
                need(label in {'held_leg','held_manual'} and held_frame == [home.frame_current,home.frame_subframe]
                     and (rig.animation_data is None or rig.animation_data.action is None)
                     and not home.tool_settings.use_keyframe_insert_auto,
                     'Held observation requires the exact unchanged author-Action-detached frame')
            tick = time.perf_counter(); graph = context.evaluated_depsgraph_get(); graph_seconds = time.perf_counter()-tick
            tick = time.perf_counter()
            meshes = {name: diag.mesh_snapshot(obj, graph) for name,obj in
                      (('input800',input_obj), ('C800',c), ('final3040',source), ('requested3040',requested))}
            extract_seconds = time.perf_counter()-tick
            final, target = meshes['final3040'], meshes['requested3040']
            need([len(meshes[n]['points']) for n in meshes] == [800,800,3040,3040]
                 and len(final['triangles']) == 5760, 'Actual final/input native counts differ')
            fixed = [i for i,row in enumerate(final['weights']) if any(w['name'] == installed['controls']['waist'] and w['weight'] >= .999 for w in row)]
            need(len(fixed) == 160, 'Original final hard160 weights unavailable')
            final['free_indices'] = [i for i in range(3040) if i not in set(fixed)]
            micro = live.precision_guard(meshes['input800']['points'], metres)
            pin = cold.error(meshes['input800']['points'], meshes['C800']['points'], metres, ring)
            evaluated = rig.evaluated_get(graph)
            root_world = evaluated.matrix_world @ evaluated.pose.bones[root.name].matrix
            row = {'label': label, 'index': index, 'frame': [home.frame_current,home.frame_subframe],
                'native_Root_world': [list(r) for r in root_world],
                'native_left_knee_world': list(evaluated.matrix_world @ evaluated.pose.bones[legs['L']['chain'][1]].head),
                'pin_current_input_error': pin, 'microguard': micro, 'pin_micro_passed': pin['maximum_m'] <= micro['metres'],
                'same_frame_observation_only': held, 'accepted': False,
                'counts': {n: {'vertices':len(m['points']), 'triangles':len(m['triangles'])} for n,m in meshes.items()},
                'input_change': None if previous is None else cold.error(previous['input800']['points'],meshes['input800']['points'],metres),
                'C_change': None if previous is None else cold.error(previous['C800']['points'],meshes['C800']['points'],metres),
                'final_change': None if previous is None else cold.error(previous['final3040']['points'],final['points'],metres),
                'timing': {'graph_get_seconds':graph_seconds,'four_mesh_extraction_seconds':extract_seconds},
                'helper_flags': {o.name: {'hide_get':o.hide_get(), 'hide_viewport':o.hide_viewport,'hide_render':o.hide_render,
                    'modifiers':[[m.type,m.show_viewport,m.show_render] for m in o.modifiers]} for o in (input_obj,c,clone,*colliders)},
                'body_data_users':body.data.users, 'input_bound':input_obj.modifiers[1].is_bound,'C_bound':c.modifiers[1].is_bound}
            samples.append(row); report['samples'] = samples; write()
            need(body.data.users == 1 and row['input_bound'] and row['C_bound'], 'Current native Body/bind isolation changed')
            diagnose = held or index in indices or not row['pin_micro_passed']
            if diagnose:
                physics.validate_physics(source)
                row['geometry_quality'] = live.geometry_quality(final,target,metres)
                tick = time.perf_counter(); body_mesh = diag.mesh_snapshot(body,graph); relay_mesh = diag.mesh_snapshot(clone,graph)
                row['timing']['Body_relay_extraction_seconds'] = time.perf_counter()-tick
                need(len(body_mesh['points']) <= args.body_vertex_limit, 'Actual Body diagnostic exceeds bounded count')
                row['Body_relay_error'] = cold.error(body_mesh['points'],relay_mesh['points'],metres)
                need(body_mesh['edges'] == relay_mesh['edges'] and body_mesh['faces'] == relay_mesh['faces']
                     and row['Body_relay_error']['maximum_m'] <= 2.e-6, 'Native actual Body relay changed topology/world geometry')
                render_bounds = diag.framing(rig,installed,graph); bounds = dict(render_bounds)
                projections = [(point-bounds['waist']).dot(bounds['up']) for m in (final,target,body_mesh) for point in m['points']]
                bounds['lower'],bounds['upper'] = min(projections)-1.e-4, max(projections)+1.e-4
                epsilon = max(1.e-7,1.e-6/metres)
                tick = time.perf_counter()
                crossing = winding.full_surface_body_crossings(diag,final,body_mesh,bounds,args.triangle_pair_limit,epsilon)
                contact = {'strict_Body_crossing':crossing, 'closed3':[], 'accepted':False}
                for collider in colliders:
                    physics._closed_collider(collider)
                    native = winding.winding_closed_collider(centered,q,collider,graph,epsilon,report,label,home.frame_current,write)
                    contact['closed3'].append({'object':collider.name,'all3040':q.collision_metrics(final['points'],native,metres,range(3040))})
                contact['unresolved_counts'] = {name:len(crossing[name]) for name in
                    ('coplanar_unresolved','degenerate_unresolved','boundary_unresolved')}
                contact['Unknown_if_incomplete'] = (crossing['status'] != 'measured'
                    or not crossing['full_surface_filter']['complete'] or any(contact['unresolved_counts'].values()))
                row['contact'] = contact; row['timing']['contact_metrics_seconds'] = time.perf_counter()-tick; write()
                if args.render and (index == indices[1] or index == report['stop_phase_indices']['turn_completed'] or label in {'daily_end','held_manual'}):
                    folder = args.output/label; folder.mkdir()
                    tick = time.perf_counter(); row['render'] = renderer(NS(output=folder,frame=home.frame_current),final,body_mesh,render_bounds)
                    row['timing']['render_seconds'] = time.perf_counter()-tick; write()
                    need(row['render']['success'] is True, 'Actual final front/side render incomplete')
            previous = meshes
            # Held staleness is observed, never waived into output acceptance.
            if not held: need(row['pin_micro_passed'], 'Time-advancing current hard80 pin error exceeded unchanged microguard')
            return row
        report['reset'] = reset; write()
        for index in range(1,61):
            budget(); move = live.input_recipe(args.case,index,60)
            root.location = old_location + Vector(movement.location_delta(move,plan))
            root.rotation_euler = old_euler + Vector((0.,0.,move['turn']))
            for side,bone in thighs.items():
                bone.rotation_quaternion = old_rotations[side] @ Quaternion(axes[bone.name],move['left' if side=='L' else 'right'])
            tick = time.perf_counter(); home.frame_set(start+index-1); frame_seconds = time.perf_counter()-tick
            row = sample('daily_end' if index == 60 else 'forward_'+str(index),index)
            row['timing']['frame_set_seconds'] = frame_seconds; write()
        report['actual_world_motion'] = movement.measured_series(plan,[{'frame':r['index'],'Root':r['native_Root_world']} for r in samples],metres)
        # Two deliberately held endpoint inputs: no seek, reset, hidden keys or
        # same-frame recalculation claim. Every contact uses the actual source.
        budget(); thighs['L'].rotation_quaternion = old_rotations['L'] @ Quaternion(axes[thighs['L'].name],-.55)
        held_frame = [home.frame_current,home.frame_subframe]
        context.view_layer.update(); sample('held_leg',60,held=True)
        hem = rig.pose.bones[installed['controls']['hem']]; old_hem = list(hem.location)
        hem.location = Vector(old_hem)+Vector((0.,-installed['fit']['height_world']*.04,0.))
        context.view_layer.update(); budget(); sample('held_manual',60,held=True)
        report['native_motion_collection_completed'] = True
    finally:
        def restore(label, callback):
            try: callback()
            except Exception as exc: restore_errors.append({'phase':label,'error':repr(exc)})
        if cloth is not None:
            restore('pause_private_Cloth',lambda: (setattr(cloth,'show_viewport',False),setattr(cloth,'show_render',False)))
        # Correctives were active during all measurements. Suppress only the
        # temporary restoration sequence; no end-of-hold recomputation claimed.
        with forearm_twist.defer_runtime(context,flush_on_exit=False):
            if animation is not None:
                restore('author_Action',lambda:setattr(animation,'action',old_action))
                if old_action is not None: restore('author_Action_slot',lambda:setattr(animation,'action_slot',old_slot))
                for track,mute,solo in old_nla:
                    restore('NLA_mute',lambda t=track,v=mute:setattr(t,'mute',v))
                    restore('NLA_solo',lambda t=track,v=solo:setattr(t,'is_solo',v))
            restore('author_context_pose_frame_Keys',tx.restore_context)
            restore('author_Body_Key_coordinates',lambda:restore_body_coordinates(body,body_coordinates,report,write))
        restore('autokey',lambda:setattr(home.tool_settings,'use_keyframe_insert_auto',old_autokey))
        if requested is not None: restore('requested_Object',lambda:bpy.data.objects.remove(requested,do_unlink=True))
        if requested_data is not None:
            restore('requested_Mesh',lambda:(need(requested_data.users == 0,'Private comparison Mesh gained outside user'),bpy.data.meshes.remove(requested_data)))
        restored = cold.receipt(bpy,p,q,direct,source,rig,body)
        fields = ('raw_Dress','raw_Body','Rest','pose','pose_position','drivers','bindings','Body_Key_channels','Body_Key_binding',
                  'Body_data_users','charts','frame','mode','active','selected','active_bone','bone_selection','bone_collections')
        report['author_restore'] = {name:restored[name] == original[name] for name in fields}
        report['author_restore']['autokey_exact'] = home.tool_settings.use_keyframe_insert_auto == old_autokey
        report['author_restore']['raw_Rest_Actions'] = protected.verify()
        report['author_restore']['errors'] = restore_errors; write()
        need(not restore_errors and all(report['author_restore'][n] is True for n in fields)
             and report['author_restore']['autokey_exact'] and report['author_restore']['raw_Rest_Actions']['success'], 'Author restore/protected content differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--artist-protection',type=Path,required=True); parser.add_argument('--artist-protection-sha',required=True)
    parser.add_argument('--body-object',required=True); parser.add_argument('--dress-object',required=True)
    parser.add_argument('--case',choices=('abrupt_stop_turn',),default='abrupt_stop_turn')
    parser.add_argument('--soft-seconds',type=float,default=180.); parser.add_argument('--render',action='store_true')
    parser.add_argument('--body-vertex-limit',type=int,default=100000); parser.add_argument('--triangle-pair-limit',type=int,default=2000)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(), 'Fresh isolated output required')
    need(0. < args.soft_seconds <= 240. and 1 <= args.triangle_pair_limit <= 20000, 'Bounded one-case execution only')
    pins = {HERE/n:s for n,s in PINS.items()}; pins.update({PROVIDER:PROVIDER_SHA,COLD_PROOF:COLD_PROOF_SHA,FAILED_STOP:FAILED_STOP_SHA,Path(__file__):sha(__file__)})
    need(all(sha(path) == value for path,value in pins.items()), 'Current provider/proof/observer pins differ')
    import bpy
    need(bpy.app.background and bpy.app.version[:2] == (5,2) and '--factory-startup' in sys.argv and not bpy.data.filepath,
         'Empty factory BG5.2 required; no UI/artist instance')
    cold = load('verify_direct_cold_install52_v4.py')
    spec = importlib.util.spec_from_file_location('motion_current_artist_readers',cold.COMPARATOR)
    p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
    need(sha(cold.COMPARATOR) == cold.COMPARATOR_SHA and sha(cold.LOCATOR) == cold.LOCATOR_SHA, 'Current Artist reader/locator differs')
    locator = p.load(cold.LOCATOR,cold.LOCATOR_SHA,'motion_explicit_locator')
    disk = p.load(p.DISK,p.DISK_SHA,'motion_disk'); source_manifest = p.load(p.SOURCE,p.SOURCE_SHA,'motion_manifest')
    pins.update({cold.COMPARATOR:cold.COMPARATOR_SHA,cold.LOCATOR:cold.LOCATOR_SHA,p.DISK:p.DISK_SHA,p.SOURCE:p.SOURCE_SHA,
                 args.artist_protection:args.artist_protection_sha})
    before = source_manifest.current_manifest(); started = time.perf_counter(); args.output.mkdir()
    report = {'stage':'CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_BODY_KEY_RESTORE52','case':args.case,'native_motion_collection_completed':False,
        'accepted':False,'effect_accepted':False,'ART_accepted':False,'artist_saved':False,'deployed':False,'export_accepted':False,
        'source_before':before,'errors':[],'scope':'One cold public Direct install, unkeyed native stop60; only private QA Body Key coordinates restored; not runtime corrective fix',
        'prior_failed_stop':{'path':str(FAILED_STOP),'sha256':FAILED_STOP_SHA,'native_pass_claimed':False},
        'execution_budget':{'soft_seconds':args.soft_seconds,'allowed_upper_seconds':240.,'external_timeout_owned_by_Root':True,'external_max_seconds':300.,'geometry_or_performance_gate_changed':False},
        'timing_scope':'Factory one-thread frame update/readback/metrics/serialization, not GUI FPS or isolated solver time'}
    def write():
        tick = time.perf_counter(); (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
        report.setdefault('report_IO_seconds',[]).append(time.perf_counter()-tick)
    def budget(): need(time.perf_counter()-started < args.soft_seconds, 'Soft execution budget exceeded; collection incomplete')
    try:
        current_disk = disk.proof(args.artist_protection,args.artist_protection_sha); report['artist_before'] = current_disk
        prior = json.loads(COLD_PROOF.read_text(encoding='utf-8'))
        need(prior.get('native_component_completed') is True and prior.get('source_files_Artist_exact') is True and prior.get('errors') == []
             and prior.get('private_scene_disposed') is True and prior['source_after'] == before
             and prior['artist_after']['sha256'] == args.artist_protection_sha, 'Actual completed current cold prerequisite differs')
        report['cold_prerequisite'] = {'path':str(COLD_PROOF),'sha256':COLD_PROOF_SHA,'component_only':True,'effect_accepted':False}
        q = load('validate_real_dress.py'); q.simple_rna = p.readers(bpy).simple_rna
        sys.modules['validate_real_dress'] = q
        scene,rig,body,source,record,choices = cold.load_artist(bpy,p,locator,Path(current_disk['receipt']['artist_path']),args.body_object,args.dress_object)
        baseline = q.Protection(); loaded_pose = q.pose_channels(rig)
        sys.path.insert(0,str(REPO/'addons')); package = importlib.import_module('character_designer'); package.register()
        direct = importlib.import_module('character_designer.skirt_surface_direct')
        need(baseline.verify()['success'] and q.pose_channels(rig) == loaded_pose, 'Registration changed protected author data/pose')
        report['explicit_selection'] = choices
        diag = load('diagnose_skin_transfer.py')
        run_motion(bpy,args,p,cold,q,diag,load('verify_live_direct_cloth52.py'),load('verify_live_direct_cloth52_disposable_fixture_v6.py'),
                   load('verify_live_direct_cloth52_movement_winding_collision.py'),load('verify_live_direct_cloth52_movement_centered_collision.py'),
                   load('verify_live_direct_cloth52_progressive_manual.py'),direct,source,rig,body,record,report,write,budget)
    except Exception as exc:
        report['errors'].append({'exception':repr(exc),'traceback':traceback.format_exc()})
    finally:
        try: bpy.ops.wm.read_factory_settings(use_empty=True); report['private_scene_disposed'] = True
        except Exception as exc: report['errors'].append({'disposal':repr(exc)})
        try:
            report['artist_after'] = disk.proof(args.artist_protection,args.artist_protection_sha)
            report['source_after'] = source_manifest.current_manifest()
            report['source_files_Artist_exact'] = report['source_after'] == before and all(sha(path) == value for path,value in pins.items())
            need(report['source_files_Artist_exact'], 'Actual source/helper/proof/Artist bytes changed')
        except Exception as exc: report['errors'].append({'final_guard':repr(exc)})
        report['native_motion_collection_completed'] = report['native_motion_collection_completed'] and not report['errors']
        report['elapsed_seconds'] = time.perf_counter()-started; write()
    print(json.dumps({'collected':report['native_motion_collection_completed'],'errors':report['errors'],'report':str(args.output/'report.json')}))
    return 0 if report['native_motion_collection_completed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
