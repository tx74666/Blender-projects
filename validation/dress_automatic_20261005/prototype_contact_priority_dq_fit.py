"""Unreleased pure NumPy contact-priority fit; source skin weights never change.

Exact raw800 native crossing triangle indices select objective priority only.
Targets remain the previously proved indexed C800. No nearest match, invented
Body direction, physics replay, bpy, source/Action/export changes or acceptance.
Uses SHA-frozen rigid-DQ formulas and preserves every previous QA artifact.
"""
from pathlib import Path
import hashlib
import json
import time
import traceback
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE/'prototype_rigid_dq_fit.py'
BASE_SHA = '50dad0a45be493ce36df1468db960e9610bf8c8586fbbc4c9b72704b05033bba'
PRIOR = HERE/'prototype_rigid_dq_fit_rig_chart_20261005.json'
PRIOR_SHA = 'e33a58ae6f968ee9013083cad8c700ba5fd169c12041a3196c2fc272884f85a1'
COLLISION = HERE/'native_fitted_dq_51_20261005_104920_233/result/native_fitted_dq.json'
COLLISION_SHA = '0007e1d424ecc02a0235ae4b0a1ef3d55958c454eaafce0b0494028c5ce3ca50'
OUTPUT = HERE/'prototype_contact_priority_dq_fit_20261005.json'
RESIDUAL_MULTIPLIER = 10.
MAX_STEPS = 40
MAX_SECONDS = 60.


def require(value,message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(path,expected):
    require(sha(path)==expected,'Frozen evidence hash differs: '+str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def load_math():
    require(sha(BASE)==BASE_SHA,'Frozen rigid-DQ source changed')
    scope={'__file__':str(BASE),'__name__':'_qa_contact_priority_frozen_math'}
    exec(compile(BASE.read_bytes(),str(BASE),'exec'),scope)
    return SimpleNamespace(**scope)


def subset_stats(points,target,indices,meters):
    indices=np.asarray(indices,dtype=int)
    if not len(indices):
        return {'vertices':0,'rms_mm':None,'max_mm':None,'maximum_raw_vertex_index':None}
    error=np.linalg.norm(points[indices]-target[indices],axis=1)*meters
    return {'vertices':len(indices),'rms_mm':float(np.sqrt(np.mean(error**2))*1000.),
            'max_mm':float(error.max()*1000.),'maximum_raw_vertex_index':int(indices[np.argmax(error)])}


def weighted_fit(b,model,q,t,target,scales,deadline):
    start=time.perf_counter()
    before=model.evaluate(q,t)
    loss=float(np.sum(((before-target)*scales[:,None])**2))
    initial,damping,history=loss,1.e-5,[]
    stop='maximum40_steps'
    for step in range(MAX_STEPS):
        if time.perf_counter()>=deadline:
            stop='global60_second_limit'
            break
        predicted,jac=model.jacobian(q,t)
        weighted_jac=jac*np.repeat(scales,3)[:,None]
        residual=((predicted-target)*scales[:,None]).ravel()
        hessian,gradient=weighted_jac.T@weighted_jac,weighted_jac.T@residual
        diagonal=np.maximum(np.diag(hessian),1.e-8)
        delta=np.linalg.solve(hessian+damping*np.diag(diagonal),-gradient).reshape(32,6)
        require(b.finite(delta),'Nonfinite priority GaussNewton step')
        ratio=max(1.,float(np.linalg.norm(delta[:,:3],axis=1).max())/.25,
                  float(np.linalg.norm(delta[:,3:],axis=1).max())/.025)
        delta/=ratio
        accepted=False
        previous=loss
        for alpha in (1.,.5,.25,.125,.0625):
            if time.perf_counter()>=deadline:
                break
            qn,tn=model.increment(q,t,alpha*delta)
            trial=float(np.sum(((model.evaluate(qn,tn)-target)*scales[:,None])**2))
            if trial<loss:
                q,t,loss,accepted=qn,tn,trial,True
                damping=max(1.e-9,damping*.35)
                break
        if not accepted:
            damping=min(1.e5,damping*10.)
        history.append({'step':step+1,'weighted_squared_rig_residual':loss,'accepted':accepted,'damping':damping})
        if accepted and previous-loss<max(1.e-14,previous*1.e-10):
            stop='weighted_least_squares_stagnation'
            break
        if not accepted and damping>=1.e5:
            stop='damping_limit'
            break
    require(loss<=initial+1.e-14,'Priority objective increased')
    return q,t,{'steps':len(history),'stop':stop,'elapsed_seconds':time.perf_counter()-start,
                'initial_weighted_squared_rig_residual':initial,'final_weighted_squared_rig_residual':loss,'history':history}


def weighted_derivative_proof(model,q,t,scales):
    _,jac=model.jacobian(q,t)
    rng=np.random.default_rng(551043)
    direction=rng.normal(size=(32,6))
    direction[:,3:]*=.05
    direction/=np.linalg.norm(direction)
    h=1.e-6
    qp,tp=model.increment(q,t,h*direction)
    qm,tm=model.increment(q,t,-h*direction)
    numerical=((model.evaluate(qp,tp)-model.evaluate(qm,tm))*scales[:,None]/(2.*h)).ravel()
    analytic=(jac*np.repeat(scales,3)[:,None])@direction.ravel()
    maximum=float(np.max(np.abs(analytic-numerical)))
    relative=float(np.linalg.norm(analytic-numerical)/max(np.linalg.norm(numerical),1.e-12))
    require(maximum<2.e-6 and relative<2.e-6,'Weighted residual/Jacobian central difference failed')
    return {'max_rig_coordinate_derivative_error':maximum,'relative_l2_error':relative,'central_step':h}


def main():
    start=time.perf_counter()
    report={'status':'failed','diagnostic_only':True,'production_effect_accepted':False,
            'collision_proved':False,'native_graph_or_export_compatibility_proved':False,
            'code_path':str(Path(__file__).resolve()),'code_sha256':sha(Path(__file__)),
            'frozen_math_code_path':str(BASE),'frozen_math_code_sha256':BASE_SHA,
            'native_collision_report_path':str(COLLISION),'native_collision_report_sha256':COLLISION_SHA,
            'priority_policy':{'contact_residual_multiplier':RESIDUAL_MULTIPLIER,
                               'contact_squared_objective_multiplier':RESIDUAL_MULTIPLIER**2,
                               'complement_residual_multiplier':1.,'source_vertex_group_weights_modified':False,
                               'all800_targets_modified':False,'mask_scope':'Exact sourceARM-only raw800 crossing triangle vertex IDs; final3040 not mapped'},
            'limits':{'max_steps_per_frame':MAX_STEPS,'global_seconds':MAX_SECONDS,'native_calibration_m':5.e-6},
            'inputs':{},'calibration':[],'frames':[],'errors':[]}
    try:
        require(not OUTPUT.exists(),'Refusing to overwrite an existing priority result')
        b=load_math()
        prior,collision=frozen(PRIOR,PRIOR_SHA),frozen(COLLISION,COLLISION_SHA)
        native,target=frozen(b.INPUT,b.INPUT_SHA),frozen(b.TARGET,b.TARGET_SHA)
        paths=((BASE,BASE_SHA),(PRIOR,PRIOR_SHA),(COLLISION,COLLISION_SHA),(b.INPUT,b.INPUT_SHA),(b.TARGET,b.TARGET_SHA))
        report['inputs']={str(p):expected for p,expected in paths}
        require(prior['native_calibration_passed'] and prior['input_hashes_after_exact']
                and prior['status']=='passed_math_only','Prior DQ calibration incomplete')
        require(collision['status']=='passed' and collision['original_graph_rollback_exact']
                and collision['artist_disk_exact'] and collision['code_exact'] and collision['sealed_input_exact']
                and collision['fit_sha256']==PRIOR_SHA and collision['native_capture_sha256']==b.INPUT_SHA
                and collision['frozen_targets_sha256']==b.TARGET_SHA,'Native collision mask provenance failed')
        require(native['status']=='passed' and native['artist_disk_exact'] and native['code_exact']
                and native['sealed_input_exact'] and not native['cloth_replayed'],'Native input proof failed')
        names=[g[1] for g in native['groups33']]
        require(len(names)==33 and names[32]=='SK_Dress_Waist'
                and [g[0] for g in native['groups33']]==list(range(33)),'Exact source33 group order differs')
        weights=native['native_weights800']
        require(all(item['group_name']==names[item['group_index']] for row in weights for item in row['weights']),
                'Original source weight index/name binding differs')
        report['native_inputs_sha256']=b.INPUT_SHA
        report['native_group_order33']=native['groups33']
        report['raw_native_weights800_sha256']=hashlib.sha256(json.dumps(weights,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        report['source_basis800_world_sha256']=hashlib.sha256(json.dumps(native['source_basis800_world'],separators=(',',':')).encode()).hexdigest()
        bind=np.array(target['frozen_record']['fit']['matrix_world'])
        report['source_bind_matrix_world']=bind.tolist()
        rest=np.array([native['rest_bones'][name]['matrix'] for name in names])
        nf={fr['frame']:fr for fr in native['frames']}
        tf={fr['frame']:fr for fr in target['frames']}
        pf={fr['frame']:fr for fr in prior['frames']}
        cf={fr['frame']:fr for fr in collision['frames']}
        require(set(nf)==set(tf)==set(pf)==set(cf)=={1,7,25,30},'Frozen four-frame provenance differs')
        prepared={}
        for frame in (1,7,25,30):
            fr=nf[frame]
            a,m=np.array(fr['rig_evaluated_matrix_world']),np.array(fr['source_evaluated_matrix_world'])
            chart=np.linalg.inv(a)@m@np.linalg.inv(bind)
            require(np.max(np.abs(chart-np.array(fr['bind_world_to_current_rig_rest_input'])))<2.e-6,'Native bind chart differs')
            model=b.DQModel(b.point_transform(chart,np.array(native['source_basis800_world'])),weights)
            pose=np.array([fr['native_bones'][name]['pose_matrix_rig'] for name in names])
            dnative=pose@np.linalg.inv(rest)
            native_rigid=b.rigid_proof(dnative)
            qn,tn=b.quaternion_matrix_states(dnative)
            native_pred=b.point_transform(a,model.evaluate(qn,tn))
            calibration=np.linalg.norm(native_pred-np.array(fr['raw_native_cold_physics_skin800_world']),axis=1)*native['scene_unit_scale_length']
            require(calibration.max()<=5.e-6,'Contact prototype native DQ calibration exceeded5um')
            require(cf[frame]['prediction_vs_native800']['max_m']<=5.e-6
                    and len(cf[frame]['native800_world'])==800,'Mask source is not proven same-index native800')
            crossings=cf[frame]['raw800_body_crossings']
            require(crossings['status']=='measured' and len(crossings['crossing_pairs'])==crossings['actual_crossing_pair_count'],
                    'Incomplete raw native crossing evidence')
            mask=set()
            for pair in crossings['crossing_pairs']:
                vertices=pair['dress_vertices']
                require(len(vertices)==3 and all(type(v) is int and 0<=v<800 for v in vertices),
                        'Collision mask has a non-raw800 native index')
                require(any(point['strict_crossing'] for point in pair['points']),'Mask pair lacks strict native crossing')
                mask.update(vertices)
            mask=np.array(sorted(mask),dtype=int)
            scales=np.ones(800)
            scales[mask]=RESIDUAL_MULTIPLIER
            rows=pf[frame]['fitted32_proper_rig_D']
            require([(row['group_index'],row['group_name']) for row in rows]==[(i,names[i]) for i in range(32)],'Prior fit32 binding differs')
            initial=np.array([row['rig_deformation_D'] for row in rows]+[dnative[32].tolist()])
            b.rigid_proof(initial)
            q,t=b.quaternion_matrix_states(initial)
            q[32],t[32]=qn[32],tn[32]
            report['calibration'].append({'frame':frame,'all800_max_error_m':float(calibration.max()),
                                         'native_rig_matrix_proof':native_rigid})
            prepared[frame]=(model,a,chart,q,t,qn,tn,mask,scales,dnative)
        report['native_calibration_passed']=True
        deadline=start+MAX_SECONDS
        for frame in (1,7,25,30):
            require(time.perf_counter()<deadline,'Global60 seconds exhausted before completing four contact fits')
            model,a,chart,q,t,qn,tn,mask,scales,dnative=prepared[frame]
            if frame==7:
                report['weighted_jacobian_central_difference']=weighted_derivative_proof(model,q,t,scales)
            meters=native['scene_unit_scale_length']
            wanted=np.array(tf[frame]['physical_world'])
            require(wanted.shape==(800,3) and b.finite(wanted),'Exact untouched indexed C800 target missing')
            initial_world=b.point_transform(a,model.evaluate(q,t))
            target_rig=b.point_transform(np.linalg.inv(a),wanted)
            q,t,details=weighted_fit(b,model,q,t,target_rig,scales,deadline)
            predicted=b.point_transform(a,model.evaluate(q,t))
            rigid=b.matrices_from_state(q,t)
            proper=b.rigid_proof(rigid)
            require(np.max(np.abs(np.linalg.det(rigid[:,:3,:3])-1.))<1.e-10,'Fit Rig rotations are not proper SO3')
            world=np.matmul(np.matmul(a[None,:,:],rigid),chart[None,:,:])
            world_proof=b.rigid_proof(world)
            complement=np.setdiff1d(np.arange(800),mask)
            fixed_intersection=np.intersect1d(mask,model.only_waist)
            report['frames'].append({'frame':frame,'contact_mask_raw_indices':mask.tolist(),
                'contact_mask_source_crossing_pair_count':cf[frame]['raw800_body_crossings']['actual_crossing_pair_count'],
                'contact_fixed_waist_indices':fixed_intersection.tolist(),
                'before_all800':b.stats(initial_world,wanted,model.only_waist,meters),
                'after_all800':b.stats(predicted,wanted,model.only_waist,meters),
                'before_contact':subset_stats(initial_world,wanted,mask,meters),'after_contact':subset_stats(predicted,wanted,mask,meters),
                'before_complement':subset_stats(initial_world,wanted,complement,meters),'after_complement':subset_stats(predicted,wanted,complement,meters),
                'fit':details,'proper_rig_rotation_proof':proper,'composed_world_rotation_proof':world_proof,
                'world_matrix_scope':'A*proper_Drig*Q preserves recorded float chart; not an exact1e-15 WORLD orthogonality claim',
                'fixed_Waist_quaternion_translation_exact':bool(np.array_equal(q[32],qn[32]) and np.array_equal(t[32],tn[32])),
                'native_input_chart_Q':chart.tolist(),'rig_matrix_world_A':a.tolist(),
                'fitted32_proper_world_D':[{'group_index':j,'group_name':names[j],'world_deformation_D':world[j].tolist()} for j in range(32)],
                'fitted32_proper_rig_D':[{'group_index':j,'group_name':names[j],'rig_deformation_D':rigid[j].tolist()} for j in range(32)],
                'predicted_raw800_world':predicted.tolist(),'fixed_native_waist_name':names[32],
                'fixed_native_waist_world_D':world[32].tolist(),'fixed_native_waist_raw_rig_float_matrix':dnative[32].tolist(),
                'collision_acceptance':False})
        require(all(sha(path)==expected for path,expected in paths),'A frozen input/code artifact changed during priority fit')
        report['input_hashes_after_exact']=True
        report['status']='passed_math_only'
    except Exception as exc:
        report['errors'].append(str(exc))
        report['traceback']=traceback.format_exc()
    report['elapsed_math_seconds']=time.perf_counter()-start
    require(not OUTPUT.exists(),'Refusing to overwrite a contact-priority report')
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'status':report['status'],'output':str(OUTPUT),'code_sha256':report['code_sha256'],
                      'elapsed_seconds':report['elapsed_math_seconds'],'errors':report['errors'],
                      'frames':[{'frame':f['frame'],'contact':len(f['contact_mask_raw_indices']),
                                 'before_all':f['before_all800'],'after_all':f['after_all800'],
                                 'before_contact':f['before_contact'],'after_contact':f['after_contact'],
                                 'after_complement':f['after_complement'],'steps':f['fit']['steps']} for f in report['frames']]},ensure_ascii=False),flush=True)
    require(report['status']=='passed_math_only','Priority DQ fit incomplete; inspect retained diagnostic result')


if __name__=='__main__':
    main()
