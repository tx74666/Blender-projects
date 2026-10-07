"""Private air5 progressive leg/Manual Reset replay and controlled squat QA.

Root alone runs factory BG5.2, soft180/external240. One fresh installation,
unkeyed native input, no imported clip/foot planting/GUI/default or artist save.
Matched Body trajectories and physical indices are required for the Manual
counterfactual. Sparse full-surface contacts are not whole-time/ART acceptance.
"""
import ast
import builtins
import copy
import dis
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
from types import CodeType

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
AIR = HERE/'verify_direct_cold_stop_tail_air5_52.py'
AIR_SHA = '751cc7d2d1a6e14b96cadf664211c97c6d324af979a351d16a474f4e7d3165db'
AIR_PROOF = HERE/'actual_direct_cold_stop_tail_air5_e0b_52_20261007_072600_392/result/report.json'
AIR_PROOF_SHA = 'a595112339181b5eed962fa92a31fd09f252326616026d95f1844fcc904d981c'
PROVIDER_SHA = 'eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99'
COLD = HERE/'actual_direct_cold_e0b_bake_guards_52_20261007_062634_189/report.json'
COLD_SHA = '0a016dc10d5cf706cbd529449a330d630d7e87459189b3f2cd068557a050d959'
ARTIST_RECEIPT_SHA = '4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f'
CONTACT_LABELS = ('A_N1','A_L16','A_L30','Manual_T','B_T30','C_squat16','C_squat30')
AUTOMATIC_CONTACT_LABELS = tuple(label for label in CONTACT_LABELS if label != 'Manual_T')


def need(value, message):
    if not value:
        raise RuntimeError('ProgressivePoseReset52: '+message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_air():
    need(sha(AIR) == AIR_SHA and sha(AIR_PROOF) == AIR_PROOF_SHA, 'Frozen air candidate/actual proof differs')
    spec = importlib.util.spec_from_file_location('progressive_frozen_air5',AIR)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def smooth(value):
    value = min(1.,max(0.,value)); return value*value*(3.-2.*value)


def recipe(phase, index):
    need(phase in ('A','B','C') and type(index) is int and 1 <= index <= 30, 'Exact three thirty-step phases required')
    ramp = smooth((index-1)/15.)
    if phase in ('A','B'):
        return {'leg':{'L':[-.55*ramp,0.,0.],'R':[0.,0.,0.]},'root_drop_fraction':0.,
                'hem_fraction':smooth((index-16)/8.) if phase == 'B' else 0.}
    return {'leg':{side:[-math.radians(60.)*ramp,math.radians(100.)*ramp,-math.radians(20.)*ramp]
                   for side in ('L','R')},'root_drop_fraction':.15*ramp,'hem_fraction':0.}


def matched_body_proof(baseline, replay):
    """Exact native world input witnesses at equal physical indices, no gain proxy."""
    fields = ('index','frame','Body_world_sha256','Body_counts','native_Body_controls','native_Root_world')
    complete = (type(baseline) is list and type(replay) is list and len(baseline) == len(replay) == 30
                and [row.get('index') for row in baseline] == list(range(1,31))
                and [row.get('index') for row in replay] == list(range(1,31))
                and all(all(field in row for field in fields) for row in baseline+replay))
    differences = []
    if complete:
        for a,b in zip(baseline,replay):
            differences.extend({'index':a['index'],'field':field,'before':a[field],'after':b[field]}
                               for field in fields if a[field] != b[field])
    return {'complete30':bool(complete),'same_actual_Body_trajectory_and_physical_time':bool(complete and not differences),
            'differences':differences[:3], 'matching_fields':list(fields), 'Manual_faithfulness_accepted':False,
            'scope':'Independent resets and equal native physical frame indices; only Hem differs','accepted':False}


def endpoint_zero(contact):
    if type(contact) is not dict: return False
    cross = contact.get('strict_Body_crossing',{})
    regions = cross.get('full_surface_filter',{})
    closed = contact.get('closed3',[])
    return (cross.get('status') == 'measured' and regions.get('complete') is True
            and type(cross.get('actual_crossing_pair_count')) is int and cross['actual_crossing_pair_count'] == 0
            and type(contact.get('unresolved_counts')) is dict and set(contact['unresolved_counts'])
                 == {'coplanar_unresolved','degenerate_unresolved','boundary_unresolved'}
            and all(type(n) is int and n == 0 for n in contact['unresolved_counts'].values())
            and contact.get('Unknown_if_incomplete') is False and len(closed) == 3
            and all(type(row.get('all3040',{}).get('sampled_vertices')) is int
                    and row['all3040']['sampled_vertices'] == 3040
                    and type(row['all3040'].get('inside_vertices')) is int and row['all3040']['inside_vertices'] == 0
                    and type(row['all3040'].get('maximum_penetration_m')) in (int,float)
                    and math.isfinite(row['all3040']['maximum_penetration_m'])
                    and row['all3040']['maximum_penetration_m'] == 0. for row in closed))


def endpoint_complete(contact):
    """A measured penetrating Manual target is complete, but not feasible."""
    if type(contact) is not dict: return False
    cross=contact.get('strict_Body_crossing',{})
    closed=contact.get('closed3',[])
    return (cross.get('status')=='measured' and cross.get('full_surface_filter',{}).get('complete') is True
            and type(cross.get('actual_crossing_pair_count')) is int and cross['actual_crossing_pair_count'] >= 0
            and contact.get('Unknown_if_incomplete') is False
            and type(contact.get('unresolved_counts')) is dict and set(contact['unresolved_counts'])
                == {'coplanar_unresolved','degenerate_unresolved','boundary_unresolved'}
            and all(type(n) is int and n==0 for n in contact['unresolved_counts'].values())
            and len(closed)==3 and all(type(row.get('all3040',{}).get('sampled_vertices')) is int
                and row['all3040']['sampled_vertices']==3040
                and type(row['all3040'].get('inside_vertices')) is int and 0 <= row['all3040']['inside_vertices'] <= 3040
                and type(row['all3040'].get('maximum_penetration_m')) in (int,float)
                and math.isfinite(row['all3040']['maximum_penetration_m'])
                and row['all3040']['maximum_penetration_m'] >= 0. for row in closed))


def final_contact_gate(contacts):
    """Six Automatic endpoints only; Manual pre-Cloth feasibility is separate."""
    collected=(type(contacts) is list and len(contacts)==7
               and all(type(row) is dict for row in contacts)
               and tuple(row.get('label') for row in contacts)==CONTACT_LABELS)
    automatic=[row for row in contacts if row.get('label') in AUTOMATIC_CONTACT_LABELS] if collected else []
    manual=next((row for row in contacts if row.get('label')=='Manual_T'),None) if collected else None
    target_status=('measured_feasible' if endpoint_zero(manual) else
                   'measured_infeasible' if endpoint_complete(manual) else 'Unknown')
    return {'expected_sample_labels':list(CONTACT_LABELS),'all7_samples_collected':collected,
            'Automatic_expected_labels':list(AUTOMATIC_CONTACT_LABELS),
            'Automatic_all6_complete_measured_zero':bool(collected and len(automatic)==6 and all(endpoint_zero(row) for row in automatic)),
            'Manual_target_feasibility':{'label':'Manual_T','status':target_status,
                'included_in_Automatic_zero_gate':False,'preCloth_visible_target_not_simulated_output':True,'accepted':False},
            'all3040_including_fixed160':True,'all_native_Body_triangles_required':True,
            'sparse_only':True,'ART_accepted':False}


def timing_summary(values):
    need(values and all(type(v) in (int,float) and math.isfinite(v) and v >= 0 for v in values), 'Complete native timings required')
    ordered=sorted(values); size=len(values)
    median=ordered[size//2] if size%2 else (ordered[size//2-1]+ordered[size//2])/2.
    return {'count':size,'median_seconds':median,'nearest_rank_P95_seconds':ordered[math.ceil(.95*size)-1],
            'maximum_seconds':ordered[-1],'GUI_FPS_claimed':False}


def missing_compiled_globals(function):
    """Resolve real compiled nested code against its actual globals and builtins."""
    namespace=function.__globals__
    native_builtins=namespace.get('__builtins__',builtins)
    builtin_names=set(native_builtins if type(native_builtins) is dict else vars(native_builtins))
    missing=set()
    def walk(code):
        for instruction in dis.get_instructions(code):
            if instruction.opname=='LOAD_GLOBAL' and instruction.argval not in namespace and instruction.argval not in builtin_names:
                missing.add(instruction.argval)
        for constant in code.co_consts:
            if isinstance(constant,CodeType): walk(constant)
    walk(function.__code__)
    return sorted(missing)


BODY = '''
        report.update(stage='CURRENT_ARTIST_DIRECT_PROGRESSIVE_POSE_RESET52',case='progressive_reset_squat',
            scope='One fresh air5 candidate; paired native Body trajectories, Manual Hem and Reset replay, controlled squat',
            motion_recipe={'physical_steps':90,'phases':{'A':'leg baseline30','B':'matched leg plus progressive Hem30','C':'squat30'},
                'Manual_same_frame_increments':8,'imported_clip':False,'foot_planted':False,'Dress_keys_created':0,'Actions_created':0},
            collision_accepted=False,naturalness_accepted=False,Manual_faithfulness_accepted=False,
            full_time_contact_accepted=False,self_intersection_verified=False,cache_content_preserved='Unproven')
        need(args.render and args.soft_seconds <= 180. and args.artist_protection_sha == _ARTIST_RECEIPT_SHA,
             'Same protected current Artist, six front/side images and soft180 required')
        prior=json.loads(_AIR_PROOF.read_text(encoding='utf-8'))
        need(prior['native_motion_collection_completed'] is True and prior['errors'] == []
             and prior['private_scene_disposed'] is True and prior['source_files_Artist_exact'] is True
             and prior['source_before'] == report['source_before'] == prior['source_after']
             and prior['artist_after']['sha256'] == args.artist_protection_sha,
             'Actual complete current-source/current-Artist Air5 component required')
        report['air5_prerequisite']={'path':str(_AIR_PROOF),'sha256':_AIR_PROOF_SHA,'component_only':True,'effect_accepted':False}
        installed = physics.add_physics(context,source,backend=direct.BACKEND,body=body,capability='BOTH')
        installed,actual_rig,c,cloth = physics.validate_physics(source)
        need(actual_rig == rig and installed['physics']['backend'] == direct.BACKEND, 'Actual fresh public Direct installation differs')
        tuning.apply(context,[source],mode='AUTOMATIC')
        input_obj=bpy.data.objects[installed['physics']['surface']['roles']['INPUT_SURFACE'][0]]
        clone=input_obj.modifiers[1].target
        colliders=[bpy.data.objects[name] for name in installed['physics']['colliders'][:-1]]
        need(len(colliders) == 3 and input_obj.modifiers[1].is_bound and c.modifiers[1].is_bound, 'Fresh BodySD/three proxies required')
        before_air=_AIR.native_parameters(context,q,profiles,source,installed,cloth,colliders,clone)
        report['private_air5']={'before':before_air,'accepted':False,'production_default_changed':False}; write()
        need(_AIR.canonical(before_air) == _AIR.canonical(prior['air_damping_variant']['before']), 'Actual prior full native cold parameters differ')
        tuning.apply(context,[source],{'air_damping':5.0})
        installed,_,c,cloth=physics.validate_physics(source)
        after_air=_AIR.native_parameters(context,q,profiles,source,installed,cloth,colliders,clone)
        report['private_air5'].update(after=after_air,proof=_AIR.air_change_proof(before_air,after_air)); write()
        need(report['private_air5']['proof']['passed'] and _AIR.canonical(after_air) == _AIR.canonical(prior['air_damping_variant']['after']),
             'Only actual air3-to5 edit allowed; every other physical parameter must match')
        need(home.render.fps/home.render.fps_base == 30., 'Native30fps required')
        metres=home.unit_settings.scale_length
        need(math.isfinite(metres) and metres>0., 'Positive finite metres required')
        legs,axes,height=q.body_inputs(rig,installed)
        root=rig.pose.bones['CTRL_master']; bone_names=[name for side in ('L','R') for name in legs[side]['chain']]
        need(len(bone_names)==len(set(bone_names))==6 and root.rotation_mode=='XYZ'
             and not rig.parent and not rig.constraints and not root.parent and not root.constraints
             and root.bone.use_local_location and all(rig.pose.bones[name].rotation_mode=='QUATERNION' for name in bone_names),
             'Original unconstrained local-location RootXYZ and six native FK quaternion inputs required')
        world_evidence=movement.uniform_evidence([list(row) for row in rig.matrix_world])
        rest_evidence=movement.uniform_evidence([list(row) for row in root.bone.matrix_local])
        old_location=Vector(root.location); old_euler=Vector(root.rotation_euler)
        old_rotations={name:Quaternion(rig.pose.bones[name].rotation_quaternion) for name in bone_names}
        hem=rig.pose.bones[installed['controls']['hem']]; old_hem=list(hem.location)
        hem_delta=Vector((0.,-installed['fit']['height_world']*.04,0.))
        if animation is not None:
            animation.action=None
            for track,_mute,_solo in old_nla: track.mute,track.is_solo=True,False
        home.tool_settings.use_keyframe_insert_auto=False
        report['input_scope']={'unkeyed_native_pose_assignments':True,'Dress_keys_created':0,'Actions_created':0,
            'author_actions_temporarily_detached':old_action is not None,'all_other_pose_channels_preserved':True,
            'foot_planted':False,'imported_clip':False,'artist_timeline_or_GUI_operated':False}
        report['movement_plan']={'leg_forward_radians':-.55,'Hem_local_delta':list(hem_delta),
            'squat_radians':[-math.radians(60.),math.radians(100.),-math.radians(20.)],
            'squat_Root_world_drop_fraction':.15,'native_Body_height_world':height,
            'rig_world':world_evidence,'Root_rest':rest_evidence,'no_pose_mode_or_matrix_setter':True,'accepted':False}
        requested=input_obj.copy(); requested_data=input_obj.data.copy(); requested.data=requested_data
        requested.name='QA progressive current requested'
        for owner in (requested,requested_data):
            for key in list(owner.keys()): del owner[key]
        home.collection.objects.link(requested)
        requested.hide_render=requested.hide_select=True; requested.hide_set(True)
        need(requested.data.shape_keys is None and requested.modifiers[1].is_bound
             and requested.modifiers[1].target==clone and direct.shared._frame(requested)==direct.shared._frame(input_obj),
             'Private requested comparison lost fresh bind/chart')
        graph=context.evaluated_depsgraph_get()
        copy_error=cold.error(diag.mesh_snapshot(input_obj,graph)['points'],diag.mesh_snapshot(requested,graph)['points'],metres)
        report['fresh_requested800_copy']=copy_error; write()
        need(copy_error['maximum_m']<=5.e-5 and source.modifiers[-1].type=='SUBSURF','Fresh requested copy/nativeSubsurf differs')
        subdiv=requested.modifiers.new('QA same native Subsurf','SUBSURF'); direct.shared._copy_scalars(source.modifiers[-1],subdiv)
        ring=installed['fit']['rings'][0]; pins=physics._weights(c)[cloth.settings.vertex_group_mass]
        need(len(ring)==len(set(ring))==80 and {i for i,v in pins.items() if v==1.}==set(ring), 'Actual hard80 identity differs')
        samples=[]; contacts=[]; previous=None; squat_body_reference=None
        endpoints={}; phase_rows={}; phase_times={}; renderer=progressive.two_view_renderer(diag)
        report['contact_labels']=list(_CONTACT_LABELS)
        def apply_move(move):
            for side in ('L','R'):
                for name,angle in zip(legs[side]['chain'],move['leg'][side]):
                    rig.pose.bones[name].rotation_quaternion=old_rotations[name] @ Quaternion(axes[name],angle)
            drop=Vector((0.,0.,-height*move['root_drop_fraction']))
            root.location=old_location+Vector(movement.matvec(rest_evidence['inverse3'],movement.matvec(world_evidence['inverse3'],drop)))
            hem.location=Vector(old_hem)+hem_delta*move['hem_fraction']
        def sample(label,index,*,manual=False,diagnose=False,render=False):
            nonlocal previous,squat_body_reference
            budget(); tick=time.perf_counter(); graph=context.evaluated_depsgraph_get(); graph_seconds=time.perf_counter()-tick
            tick=time.perf_counter()
            meshes={name:diag.mesh_snapshot(obj,graph) for name,obj in
                (('input800',input_obj),('C800',c),('final3040',source),('requested3040',requested))}
            body_mesh=diag.mesh_snapshot(body,graph); extract_seconds=time.perf_counter()-tick
            final=meshes['final3040']; target=meshes['requested3040']
            need([len(meshes[name]['points']) for name in meshes]==[800,800,3040,3040]
                 and len(final['triangles'])==5760 and len(body_mesh['points'])<=args.body_vertex_limit
                 and all(math.isfinite(v) for mesh in list(meshes.values())+[body_mesh] for point in mesh['points'] for v in point),
                 'Finite complete native800/final3040/Body counts required')
            fixed=[i for i,weights in enumerate(final['weights']) if any(w['name']==installed['controls']['waist'] and w['weight']>=.999 for w in weights)]
            need(len(fixed)==160,'Actual final hard160 weight mapping required')
            final['free_indices']=[i for i in range(3040) if i not in set(fixed)]
            eval_rig=rig.evaluated_get(graph); rw=eval_rig.matrix_world
            native_controls={name:[list(row) for row in rw @ eval_rig.pose.bones[name].matrix] for name in bone_names}
            native_root=[list(row) for row in rw @ eval_rig.pose.bones[root.name].matrix]
            micro=live.precision_guard(meshes['input800']['points'],metres)
            pin=cold.error(meshes['input800']['points'],meshes['C800']['points'],metres,ring)
            row={'label':label,'index':index,'frame':[home.frame_current,home.frame_subframe],
                'Body_world_sha256':hashlib.sha256(q.pack(body_mesh['points']).tobytes()).hexdigest(),
                'Body_counts':[len(body_mesh['points']),len(body_mesh['triangles'])],
                'native_Body_controls':native_controls,'native_Root_world':native_root,
                'native_leg_joints':{side:[list(rw @ eval_rig.pose.bones[name].head) for name in legs[side]['chain']] for side in ('L','R')},
                'Body_data_users':body.data.users,'input_bound':input_obj.modifiers[1].is_bound,'C_bound':c.modifiers[1].is_bound,
                'pin_current_input_error':pin,'microguard':micro,'pin_micro_passed':pin['maximum_m']<=micro['metres'],
                'Manual_visible_preCloth_not_cached_output':manual,'state':direct._state(source,installed),
                'Cloth_flags':[cloth.show_viewport,cloth.show_render],
                'input_change':None if previous is None else cold.error(previous['input800']['points'],meshes['input800']['points'],metres),
                'final_change':None if previous is None else cold.error(previous['final3040']['points'],final['points'],metres),
                'timing':{'graph_get_seconds':graph_seconds,'four_mesh_and_Body_extraction_seconds':extract_seconds},'accepted':False}
            if label.startswith('C_'):
                if squat_body_reference is None: squat_body_reference=[point.copy() for point in body_mesh['points']]
                row['actual_Body_mesh_from_squat_N']=cold.error(squat_body_reference,body_mesh['points'],metres)
            samples.append(row); report['samples']=samples; write()
            physics.validate_physics(source)
            need(body.data.users==1 and row['input_bound'] and row['C_bound'],'Actual Body/bind isolation changed')
            need(manual or row['pin_micro_passed'],'Advancing current hard80 pin failed unchanged microguard')
            if manual:
                need(row['state']['mode']=='MANUAL' and row['Cloth_flags']==[False,False],'Manual observation unexpectedly enabled stale Cloth')
            else:
                need(row['state']['mode']=='AUTOMATIC' and row['Cloth_flags']==[True,True],'Actual Automatic output unavailable')
            if diagnose:
                tick=time.perf_counter(); relay=diag.mesh_snapshot(clone,graph)
                row['Body_relay_error']=cold.error(body_mesh['points'],relay['points'],metres)
                need(body_mesh['edges']==relay['edges'] and body_mesh['faces']==relay['faces'] and row['Body_relay_error']['maximum_m']<=2.e-6,
                     'Actual Body relay world geometry/topology changed')
                render_bounds=diag.framing(rig,installed,graph); bounds=dict(render_bounds)
                projected=[(point-bounds['waist']).dot(bounds['up']) for mesh in (final,target,body_mesh) for point in mesh['points']]
                bounds['lower'],bounds['upper']=min(projected)-1.e-4,max(projected)+1.e-4
                epsilon=max(1.e-7,1.e-6/metres)
                crossing=winding.full_surface_body_crossings(diag,final,body_mesh,bounds,args.triangle_pair_limit,epsilon)
                contact={'label':label,'strict_Body_crossing':crossing,'closed3':[],'accepted':False}
                for collider in colliders:
                    physics._closed_collider(collider)
                    native=winding.winding_closed_collider(centered,q,collider,graph,epsilon,report,label,home.frame_current,write)
                    contact['closed3'].append({'object':collider.name,'all3040':q.collision_metrics(final['points'],native,metres,range(3040))})
                contact['unresolved_counts']={name:len(crossing[name]) for name in ('coplanar_unresolved','degenerate_unresolved','boundary_unresolved')}
                contact['Unknown_if_incomplete']=(crossing['status']!='measured' or not crossing['full_surface_filter']['complete']
                    or any(contact['unresolved_counts'].values()))
                contact['measured_endpoint_zero']=_ENDPOINT_ZERO(contact)
                contact['output_scope']='Manual_preCloth_target_feasibility' if manual else 'Automatic_simulated_final_surface'
                row['contact']=contact; contacts.append(contact); report['contacts']=contacts
                row['geometry_quality']=live.geometry_quality(final,target,metres)
                row['timing']['complete_contact_and_quality_seconds']=time.perf_counter()-tick; write()
                if render:
                    budget(); folder=args.output/label; folder.mkdir(); tick=time.perf_counter()
                    row['render']=renderer(NS(output=folder,frame=home.frame_current),final,body_mesh,render_bounds)
                    row['timing']['render_seconds']=time.perf_counter()-tick; write()
                    need(row['render']['success'] is True,'Actual native final front/side render incomplete')
            previous=meshes
            return meshes,row
        def run_phase(phase):
            nonlocal previous
            apply_move(_RECIPE(phase,1)); reset=physics.reset_simulation(context,source)
            tuning.apply(context,[source],mode='AUTOMATIC')
            start=reset['start']; previous=None
            report.setdefault('public_resets',[]).append({'phase':phase,'result':reset,'frame':[home.frame_current,home.frame_subframe],
                'state':direct._state(source,installed),'cache':q.cache_state(cloth),'intent':'Reset this disposable own cache for the explicit recipe','accepted':False}); write()
            need(home.frame_current==start and home.frame_subframe==0. and not reset['is_baked']
                 and cloth.show_viewport and cloth.show_render and cloth.point_cache.frame_step==1 and start+29<=cloth.point_cache.frame_end,
                 'Explicit Reset/start-frame output or owned30 interval unavailable')
            rows=[]; seconds=[]
            for index in range(1,31):
                budget(); move=_RECIPE(phase,index); apply_move(move)
                tick=time.perf_counter(); home.frame_set(start+index-1); elapsed=time.perf_counter()-tick
                label=(('A_N1' if index==1 else 'A_L16' if index==16 else 'A_L30' if index==30 else 'A_'+str(index)) if phase=='A'
                       else ('B_T30' if index==30 else 'B_'+str(index)) if phase=='B'
                       else ('C_squat16' if index==16 else 'C_squat30' if index==30 else 'C_'+str(index)))
                meshes,row=sample(label,index,diagnose=label in _CONTACT_LABELS,render=index==30)
                row['actual_unkeyed_recipe']=move; row['timing']['frame_set_seconds']=elapsed; seconds.append(elapsed); rows.append(row); write()
                if index in (1,16,30): endpoints[(phase,index)]=meshes
            phase_rows[phase]=rows; phase_times[phase]=_TIMING(seconds)
            report['phase_frame_set_timing']=phase_times; write()
        run_phase('A')
        baseline_A=phase_rows['A']; baseline_end=endpoints[('A',30)]
        report['leg_input_response']=cold.error(endpoints[('A',1)]['input800']['points'],baseline_end['input800']['points'],metres)
        need(report['leg_input_response']['maximum_m']>5.e-5,'Real gradual left-leg input did not reach the actual skin')
        tuning.apply(context,[source],mode='MANUAL')
        manual_reference=baseline_A[-1]; manual_frame=[home.frame_current,home.frame_subframe]
        for step in range(1,9):
            budget(); hem.location=Vector(old_hem)+hem_delta*smooth(step/8.)
            context.view_layer.update()
            meshes,row=sample('Manual_T' if step==8 else 'Manual_'+str(step),30,manual=True,diagnose=step==8)
            row['same_frame_Manual_increment']=step
            need(row['frame']==manual_frame and row['Body_world_sha256']==manual_reference['Body_world_sha256']
                 and row['native_Body_controls']==manual_reference['native_Body_controls']
                 and row['native_Root_world']==manual_reference['native_Root_world'],'Manual Hem changed Body pose or the held frame')
            write()
        manual_target=meshes
        target_delta=cold.error(baseline_end['requested3040']['points'],manual_target['requested3040']['points'],metres)
        report['Manual_target_input']={'requested_change':target_delta,'Body_fixed':True,'actual_same_frame':manual_frame,
            'C_is_disabled_input_not_cached_output':True,'target_feasibility':row['contact'],'Manual_faithfulness_accepted':False}; write()
        need(target_delta['maximum_m']>5.e-5,'Actual gradual Hem edit did not change the native requested surface')
        run_phase('B')
        matched=_MATCHED(baseline_A,phase_rows['B']); report['paired_Body_input_proof']=matched; write()
        need(matched['same_actual_Body_trajectory_and_physical_time'],'Matched native Body trajectory/physical-time counterfactual failed')
        edited=endpoints[('B',30)]
        need(baseline_end['final3040']['edges']==edited['final3040']['edges'] and baseline_end['final3040']['faces']==edited['final3040']['faces'],
             'Actual final Manual counterfactual index/topology changed')
        output_delta=cold.error(baseline_end['final3040']['points'],edited['final3040']['points'],metres)
        report['Manual_matched_time_response']={'same_actual_Body_path_and_physical_indices':True,'physical_index':30,
            'actual_requested_delta':cold.error(baseline_end['requested3040']['points'],edited['requested3040']['points'],metres),
            'actual_final_delta':output_delta,'current_target_residual':cold.error(edited['requested3040']['points'],edited['final3040']['points'],metres),
            'scope':'Matched-time counterfactual isolates changed Hem input; collision/inertia may prevent target shape fidelity',
            'Manual_faithfulness_accepted':False,'accepted':False}; write()
        need(output_delta['maximum_m']>1.e-6,'Final native surface did not respond after explicit Reset/replay')
        run_phase('C')
        squat_rows=phase_rows['C']; first=squat_rows[0]; last=squat_rows[-1]
        knee_bends={}
        for side in ('L','R'):
            joints=[Vector(point) for point in last['native_leg_joints'][side]]
            need((joints[1]-joints[0]).length>0. and (joints[2]-joints[1]).length>0.,'Actual squat native leg segment unresolved')
            knee_bends[side]=math.degrees((joints[1]-joints[0]).angle(joints[2]-joints[1]))
        root_drop=(first['native_Root_world'][2][3]-last['native_Root_world'][2][3])*metres
        expected_drop=height*.15*metres
        hip_heights={side:{'first_world_Z_m':first['native_leg_joints'][side][0][2]*metres,
                           'last_world_Z_m':last['native_leg_joints'][side][0][2]*metres,
                           'actual_drop_m':(first['native_leg_joints'][side][0][2]-last['native_leg_joints'][side][0][2])*metres}
                     for side in ('L','R')}
        report['squat_actual_input']={'native_knee_bend_degrees':knee_bends,'Root_world_drop_m':root_drop,'requested_drop_m':expected_drop,
            'native_hip_height':hip_heights,'actual_Body_mesh_response':last['actual_Body_mesh_from_squat_N'],
            'Body_changed':first['Body_world_sha256']!=last['Body_world_sha256'],'foot_planted':False,'imported_clip':False,'accepted':False}; write()
        need(all(value>=90. for value in knee_bends.values()) and abs(root_drop-expected_drop)<=5.e-5
             and all(value['actual_drop_m']>5.e-5 for value in hip_heights.values())
             and last['actual_Body_mesh_from_squat_N']['maximum_m']>5.e-5
             and first['Body_world_sha256']!=last['Body_world_sha256'],'Controlled deep squat did not produce the declared actual native Body input')
        report['motion_steps_completed']=True
        report['full_surface_contact_gate']=_FINAL_CONTACT_GATE(contacts); write()
        need(report['full_surface_contact_gate']['all7_samples_collected']
             and report['full_surface_contact_gate']['Automatic_all6_complete_measured_zero'],
             'Automatic final full-surface contact has penetration/crossing or Unknown/budget-incomplete scope')
        report['native_motion_collection_completed']=True
'''


def prepared_namespace(expected_provider_sha, cold_path, cold_sha):
    need(expected_provider_sha==PROVIDER_SHA and Path(cold_path).resolve()==COLD.resolve() and cold_sha==COLD_SHA,
         'Only the reviewed current provider/fresh actual Cold allowed')
    air=load_air(); adapter=air.load_adapter()
    namespace,base,_run,main,_replacements=adapter.prepared_namespace(expected_provider_sha,cold_path,cold_sha)
    original=ast.parse(inspect.getsource(base.run_motion)).body[0]; changed=copy.deepcopy(original)
    next(node for node in changed.body if isinstance(node,ast.Try)).body=ast.parse(inspect.cleandoc(BODY)).body
    run_source=ast.unparse(ast.fix_missing_locations(changed))
    edits=[]
    def replace(a,b):
        nonlocal main
        need(main.count(a)==1,'Unique inherited main ABI differs: '+a[:50]); main=main.replace(a,b); edits.append((a,b))
    replace("choices=('abrupt_stop_turn',),default='abrupt_stop_turn'","choices=('progressive_reset_squat',),default='progressive_reset_squat'")
    replace('CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_SETTLING_TAIL52','CURRENT_ARTIST_DIRECT_PROGRESSIVE_POSE_RESET52')
    replace('Original stop60 unchanged, append fixed actual f60 pose/input61..134; Body12Key restore retained; not naturalness acceptance',
            'Fresh private air5 paired leg and Manual Reset replay30+30 plus controlled squat30; Body12 restore retained; no naturalness or fidelity acceptance')
    replace('args.soft_seconds <= 240.','args.soft_seconds <= 180.')
    replace("'allowed_upper_seconds':240.","'allowed_upper_seconds':180.")
    replace("'external_max_seconds':300.","'external_max_seconds':240.")
    marker='pins.update({_TAIL_BASE:_TAIL_BASE_SHA,_TAIL_STOP_REPORT:_TAIL_STOP_REPORT_SHA})'
    replace(marker,marker+'; pins.update({_QA_AIR:_QA_AIR_SHA,_AIR_PROOF:_AIR_PROOF_SHA})')
    namespace.update(__file__=str(Path(__file__).resolve()),__doc__=__doc__,copy=copy,smooth=smooth,
        _AIR=air,_QA_AIR=AIR,_QA_AIR_SHA=AIR_SHA,_AIR_PROOF=AIR_PROOF,_AIR_PROOF_SHA=AIR_PROOF_SHA,
        _ARTIST_RECEIPT_SHA=ARTIST_RECEIPT_SHA,_RECIPE=recipe,_MATCHED=matched_body_proof,
        _ENDPOINT_ZERO=endpoint_zero,_FINAL_CONTACT_GATE=final_contact_gate,
        _TIMING=timing_summary,_CONTACT_LABELS=CONTACT_LABELS)
    exec(compile(run_source+'\n'+main,str(Path(__file__).resolve()),'exec'),namespace)
    return namespace,base,original,changed,edits


def pure_checks():
    namespace,base,original,changed,edits=prepared_namespace(PROVIDER_SHA,COLD,COLD_SHA)
    old_try=next(node for node in original.body if isinstance(node,ast.Try)); new_try=next(node for node in changed.body if isinstance(node,ast.Try))
    need(ast.dump(ast.Module(body=old_try.finalbody,type_ignores=[]))==ast.dump(ast.Module(body=new_try.finalbody,type_ignores=[]))
         and ast.dump(ast.Module(body=original.body[:original.body.index(old_try)],type_ignores=[]))
             ==ast.dump(ast.Module(body=changed.body[:changed.body.index(new_try)],type_ignores=[])), 'Original Body12/raw capture/finally changed')
    need(namespace['main'].__globals__ is namespace and namespace['run_motion'].__globals__ is namespace
         and namespace['restore_body_coordinates'] is base.restore_body_coordinates
         and namespace['_MATCHED'] is matched_body_proof and namespace['_ENDPOINT_ZERO'] is endpoint_zero
         and namespace['_FINAL_CONTACT_GATE'] is final_contact_gate,'Real compiled globals/finalizer differs')
    need(not missing_compiled_globals(namespace['run_motion']) and not missing_compiled_globals(namespace['main']),
         'Actual compiled BODY/closures/main have unresolved global names')
    original_smooth=namespace.pop('smooth')
    try:
        need(missing_compiled_globals(namespace['run_motion'])==['smooth'],
             'Actual compiled Manual missing-smooth failure not detected')
    finally: namespace['smooth']=original_smooth
    need(namespace['smooth'] is smooth and not missing_compiled_globals(namespace['run_motion']),
         'Actual compiled global binding not restored')
    need(all(recipe('A',i)['leg']==recipe('B',i)['leg'] and recipe('A',i)['root_drop_fraction']==recipe('B',i)['root_drop_fraction']
             for i in range(1,31)) and recipe('B',16)['hem_fraction']==0. and recipe('B',24)['hem_fraction']==1.,'Matched recipe times/body differ')
    reference=[{'index':i,'frame':[i,0.],'Body_world_sha256':'a'*64,'Body_counts':[10,20],
                'native_Body_controls':{'native':'matrix'},'native_Root_world':['matrix']} for i in range(1,31)]
    need(matched_body_proof(reference,copy.deepcopy(reference))['same_actual_Body_trajectory_and_physical_time'],'Matched positive rejected')
    failures=0
    for field,value in (('Body_world_sha256','b'*64),('frame',[31,0.]),('index',31),('native_Body_controls',{}),('Body_counts',[9,20])):
        changed_rows=copy.deepcopy(reference); changed_rows[15][field]=value
        need(not matched_body_proof(reference,changed_rows)['same_actual_Body_trajectory_and_physical_time'],'Native Body/time mismatch admitted: '+field); failures+=1
    need(not matched_body_proof(reference,reference[:-1])['same_actual_Body_trajectory_and_physical_time'],'Missing native step admitted'); failures+=1
    good={'strict_Body_crossing':{'status':'measured','full_surface_filter':{'complete':True},'actual_crossing_pair_count':0},
          'unresolved_counts':dict.fromkeys(('coplanar_unresolved','degenerate_unresolved','boundary_unresolved'),0),
          'Unknown_if_incomplete':False,'closed3':[{'all3040':{'sampled_vertices':3040,'inside_vertices':0,'maximum_penetration_m':0.}} for _ in range(3)]}
    need(endpoint_zero(good),'Measured full endpoint zero rejected')
    for key,value in (('status','Unknown'),('actual_crossing_pair_count',1),('actual_crossing_pair_count',None)):
        bad=copy.deepcopy(good); bad['strict_Body_crossing'][key]=value
        need(not endpoint_zero(bad),'Unknown/crossing accepted'); failures+=1
    for key,value in (('sampled_vertices',2880),('inside_vertices',1),('maximum_penetration_m',.014),('maximum_penetration_m',float('nan'))):
        bad=copy.deepcopy(good); bad['closed3'][0]['all3040'][key]=value
        need(not endpoint_zero(bad),'Missing full surface/penetration accepted'); failures+=1
    bad=copy.deepcopy(good); bad['strict_Body_crossing']['full_surface_filter']['complete']=False
    need(not endpoint_zero(bad) and not endpoint_zero({}),'Missing/budget incomplete accepted'); failures+=2
    collected=[dict(copy.deepcopy(good),label=label) for label in CONTACT_LABELS]
    manual=collected[3]
    manual['strict_Body_crossing']['actual_crossing_pair_count']=5
    manual['closed3'][0]['all3040'].update(inside_vertices=2,maximum_penetration_m=.014)
    gate=final_contact_gate(collected)
    need(gate['Automatic_all6_complete_measured_zero'] and gate['Manual_target_feasibility']['status']=='measured_infeasible',
         'Penetrating Manual target was mixed into Automatic final collision acceptance')
    unknown=copy.deepcopy(collected); unknown[3]['Unknown_if_incomplete']=True
    need(final_contact_gate(unknown)['Automatic_all6_complete_measured_zero']
         and final_contact_gate(unknown)['Manual_target_feasibility']['status']=='Unknown','Manual Unknown mislabelled as Automatic output failure')
    for index in (0,1,2,4,5,6):
        for state in ('penetration','Unknown'):
            changed_contacts=copy.deepcopy(collected)
            if state=='penetration': changed_contacts[index]['closed3'][0]['all3040'].update(inside_vertices=1,maximum_penetration_m=.014)
            else: changed_contacts[index]['Unknown_if_incomplete']=True
            need(not final_contact_gate(changed_contacts)['Automatic_all6_complete_measured_zero'],
                 'Automatic penetration/Unknown waived by Manual classification'); failures+=1
    need(not final_contact_gate(collected[:3]+collected[4:])['all7_samples_collected'],'Missing Manual target sample accepted'); failures+=1
    need(timing_summary([.1,.2,.3])['nearest_rank_P95_seconds']==.3,'Nearest-rank timing contract differs')
    for phase in ('A','B','C'):
        for i in range(16 if phase!='B' else 24,31):
            need(recipe(phase,i)==recipe(phase,30),'Endpoint input not held constant')
    for function in ('body_inputs','collision_metrics'):
        tree=ast.parse((HERE/'validate_real_dress.py').read_text(encoding='utf-8-sig'))
        need(any(isinstance(n,ast.FunctionDef) and n.name==function for n in tree.body),'Real QA ABI missing')
    calls=[node for node in ast.walk(ast.parse(inspect.cleandoc(BODY))) if isinstance(node,ast.Call)]
    need(not any(isinstance(node.func,ast.Attribute) and node.func.attr=='keyframe_insert' for node in calls)
         and 'bpy.data.actions.new' not in BODY and "mode='MANUAL'" in BODY
         and 'physics.reset_simulation(context,source)' in BODY and 'range(3040)' in BODY,'Private no-key/publicReset/full-surface contract differs')
    air=namespace['_AIR']; prior=json.loads(AIR_PROOF.read_text(encoding='utf-8'))
    need(prior['native_motion_collection_completed'] is True and prior['errors']==[] and prior['air_damping_variant']['proof']['passed'] is True,
         'Actual Air5 completion missing')
    need(air.air_change_proof(prior['air_damping_variant']['before'],prior['air_damping_variant']['after'])['passed'],'Actual air-only proof differs')
    actual_pose=prior['Body_input_baseline']['pose']
    need(actual_pose['CTRL_master']['mode']=='XYZ' and all(actual_pose[name]['mode']=='QUATERNION'
         for name in ('thigh.L','thigh.R','shin.L','shin.R','foot.L','foot.R')),
         'Recorded current Artist modes cannot support this controlled input; no conversion permitted')
    actual_abi={
        'verify_direct_cold_install52_v4.py':{'error':(3,4)},
        'validate_real_dress.py':{'body_inputs':(2,2),'collision_metrics':(3,4),'pack':(1,1)},
        'diagnose_skin_transfer.py':{'mesh_snapshot':(2,2),'framing':(3,3)},
        'verify_live_direct_cloth52.py':{'precision_guard':(2,2),'geometry_quality':(3,3)},
        'verify_live_direct_cloth52_disposable_fixture_v6.py':{'uniform_evidence':(1,1),'matvec':(2,2)},
        'verify_live_direct_cloth52_movement_winding_collision.py':{'full_surface_body_crossings':(6,6),'winding_closed_collider':(9,9)},
        'verify_live_direct_cloth52_progressive_manual.py':{'two_view_renderer':(1,1)}}
    abi_count=0
    for filename,functions in actual_abi.items():
        tree=ast.parse((HERE/filename).read_text(encoding='utf-8-sig'))
        for name,expected in functions.items():
            function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
            need((len(function.args.args)-len(function.args.defaults),len(function.args.args))==expected,
                 'Actual native observer positional ABI differs: '+name)
            abi_count+=1
    # Execute the real frozen manifest/Artist preflight without importing bpy.
    readers=base.load('verify_direct_cold_install52_v4.py')
    spec=importlib.util.spec_from_file_location('progressive_pure_readers',readers.COMPARATOR)
    p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
    source=p.load(p.SOURCE,p.SOURCE_SHA,'progressive_pure_manifest'); disk=p.load(p.DISK,p.DISK_SHA,'progressive_pure_disk')
    need(source.current_manifest()==prior['source_before']==prior['source_after'],'Current source changed since actual Air5')
    need(disk.proof(Path(prior['artist_after']['path']),ARTIST_RECEIPT_SHA)['sha256']==ARTIST_RECEIPT_SHA,'Current typed Artist proof differs')
    print(json.dumps({'source_prepared':True,'native_executed':False,'full_current_manifest_and_Artist_exact':True,
        'Body12_prefix_finally_AST_exact':True,'real_compiled_namespace_and_restore_identity':True,
        'recursive_real_compiled_BODY_closures_main_globals_complete':True,'actual_missing_smooth_negative':True,
        'physical_steps':90,'Manual_held_increments':8,'full_surface_contact_samples':7,'front_side_images':6,
        'matched_Body_and_contact_negative_controls':failures,'actual_observer_ABI':abi_count,
        'recorded_current_Root_and_six_FK_modes_supported':True,'private_air5_only':True,'motion_and_ART_accepted':False}))


def main():
    air=load_air(); adapter=air.load_adapter(); dependencies,delegated=adapter.dependency_arguments(sys.argv)
    need(dependencies==(PROVIDER_SHA,COLD.resolve(),COLD_SHA),'Only reviewed current provider/actual Cold pins allowed')
    need(COLD.is_file() and sha(COLD)==COLD_SHA,'Actual complete Cold file differs')
    namespace,*_=prepared_namespace(*dependencies)
    original_argv=sys.argv
    try:
        sys.argv=delegated; return namespace['main']()
    finally:
        sys.argv=original_argv
        need(sha(AIR)==AIR_SHA and sha(AIR_PROOF)==AIR_PROOF_SHA and sha(COLD)==COLD_SHA,'Frozen proof/source changed during execution')


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
