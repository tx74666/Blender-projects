"""Pure NumPy, unreleased rigid-DQ fit over sealed native inputs; no bpy.

Only writes its one JSON report. No scale/shear fit, collision inference, scene,
Action, runtime, export or native graph mutation. Blender 5.1 primary formulas:
math_rotation_c.cc mat4_to_dquat/add_weighted_dq_dq/mul_v3m3_dq.
The rigid scale_weight==0 path is used; float matrix orthogonality is checked,
and all 800 predictions must first match native cold DQ within five micrometres.
"""
from pathlib import Path
import hashlib
import json
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'fit_inputs_51_20261005_102341_056/result/native_fit_inputs.json'
INPUT_SHA = '2ad843be7853801c6054c829488f269518d15d9b5334757f792e45277e20e19c'
TARGET = HERE / 'waist_body_attachment_51_20261005_094107_823/result/experimental_actual_surface.json'
TARGET_SHA = 'a6618bea6487ccada08a6c52c852a788a6c277f1e8b62d9fc0a6cce42ad1e861'
INITIAL = HERE / 'math_free_weighted_lbs_waist_20261005.json'
INITIAL_SHA = '6c7d7646d22b5092c90377eac94eb3bc31d830369392466538bbd1ec63d2e2d0'
OUTPUT = HERE / 'prototype_rigid_dq_fit_20261005.json'
PRIMARY = 'https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/blenlib/intern/math_rotation_c.cc'
ORTH_LIMIT = 5.e-5
SCALE_LIMIT = 1.e-4
CALIBRATION_METRES = 5.e-6
MAX_STEPS = 40
MAX_SECONDS = 60.


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_frozen(path, expected):
    require(sha(path) == expected, 'Frozen input hash differs: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def finite(value):
    return bool(np.isfinite(value).all())


def point_transform(matrix, points):
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def qmul(a, b):
    """Hamilton product, scalar first, compatible with Blender float[4]."""
    aw, av = a[..., :1], a[..., 1:]
    bw, bv = b[..., :1], b[..., 1:]
    return np.concatenate((aw*bw - np.sum(av*bv, axis=-1, keepdims=True),
                           aw*bv + bw*av + np.cross(av, bv)), axis=-1)


def conjugate(q):
    return q * np.array([1., -1., -1., -1.])


def pure(points):
    return np.concatenate((np.zeros(points.shape[:-1] + (1,)), points), axis=-1)


def matrix_quaternion(matrix):
    """Unit quaternion from positive, near-rigid native rotation.

    Column normalization follows Blender mat4_to_quat's mat3 normalization.
    No SVD fit of a scale/shear matrix is silently accepted.
    """
    r = matrix[:3, :3].copy()
    r /= np.linalg.norm(r, axis=0)
    trace = np.trace(r)
    if trace > 0:
        s = np.sqrt(trace + 1.) * 2.
        q = np.array([.25*s, (r[2,1]-r[1,2])/s,
                      (r[0,2]-r[2,0])/s, (r[1,0]-r[0,1])/s])
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i+1) % 3, (i+2) % 3
        s = np.sqrt(max(0., 1. + r[i,i] - r[j,j] - r[k,k])) * 2.
        require(s > 1.e-12, 'Degenerate quaternion conversion')
        q = np.zeros(4)
        q[0], q[i+1] = (r[k,j]-r[j,k])/s, .25*s
        q[j+1], q[k+1] = (r[j,i]+r[i,j])/s, (r[k,i]+r[i,k])/s
    q /= np.linalg.norm(q)
    return q


def rotations(q):
    w, x, y, z = q.T
    result = np.empty((len(q), 3, 3))
    result[:,0,0] = 1.-2.*(y*y+z*z)
    result[:,0,1] = 2.*(x*y-w*z)
    result[:,0,2] = 2.*(x*z+w*y)
    result[:,1,0] = 2.*(x*y+w*z)
    result[:,1,1] = 1.-2.*(x*x+z*z)
    result[:,1,2] = 2.*(y*z-w*x)
    result[:,2,0] = 2.*(x*z-w*y)
    result[:,2,1] = 2.*(y*z+w*x)
    result[:,2,2] = 1.-2.*(x*x+y*y)
    return result


def rigid_proof(matrices):
    require(matrices.shape == (33,4,4) and finite(matrices), 'Need finite33 ordered matrices')
    r = matrices[:, :3, :3]
    gram = np.matmul(r.transpose(0,2,1), r)
    det = np.linalg.det(r)
    scale = np.linalg.norm(r, axis=1)
    result = {'orthogonality_max': float(np.max(np.abs(gram-np.eye(3)))),
              'axis_scale_delta_max': float(np.max(np.abs(scale-1.))),
              'determinant_min': float(det.min()), 'determinant_max': float(det.max()),
              'affine_last_row_max': float(np.max(np.abs(matrices[:,3,:]-[0.,0.,0.,1.])))}
    require(result['orthogonality_max'] <= ORTH_LIMIT and result['axis_scale_delta_max'] <= SCALE_LIMIT
            and det.min() > 0. and result['affine_last_row_max'] <= 1.e-10,
            'Native scale/shear/reflection exceeds explicit rigid-only scope')
    return result


class DQModel:
    def __init__(self, points, weights_rows):
        self.points = np.asarray(points, dtype=float)
        require(self.points.shape == (800,3) and finite(self.points), 'Expected finite indexed800 Basis')
        require([v['raw_vertex_index'] for v in weights_rows] == list(range(800)), 'Weights must retain exact raw800 order')
        count = max(len(v['weights']) for v in weights_rows)
        self.order = np.zeros((800,count), dtype=int)
        self.ordered_weight = np.zeros((800,count))
        self.weights = np.zeros((800,33))
        for i, row in enumerate(weights_rows):
            seen = set()
            for slot, item in enumerate(row['weights']):
                j, weight = item['group_index'], item['weight']
                require(0 <= j < 33 and j not in seen and weight > 0., 'Invalid duplicate/indexed native weight')
                seen.add(j)
                self.order[i,slot], self.ordered_weight[i,slot] = j, weight
                self.weights[i,j] = weight
        require(finite(self.weights) and np.max(np.abs(self.weights.sum(axis=1)-1.)) < 1.e-6,
                'All800 must retain fully assigned native positive normalized weights')
        self.centres = np.array([np.average(self.points,axis=0,weights=self.weights[:,j]) for j in range(32)])
        self.only_waist = np.flatnonzero(self.weights[:,32] == 1.)
        require(len(self.only_waist) == 80, 'Expected exact80 only-Waist vertices')

    def evaluate(self, q, t, details=False):
        """Native order, running-accumulator sign rule, no scale component."""
        d = .5*qmul(pure(t),q)
        qb, db, signed = np.zeros((800,4)), np.zeros((800,4)), np.zeros((800,33))
        for slot in range(self.order.shape[1]):
            indices, weight = self.order[:,slot], self.ordered_weight[:,slot]
            sign = np.where(np.sum(q[indices]*qb,axis=1) < 0., -1., 1.)
            weight = weight*sign
            qb += weight[:,None]*q[indices]
            db += weight[:,None]*d[indices]
            signed[np.arange(800),indices] += weight
        n2 = np.sum(qb*qb,axis=1)
        require(n2.min() > 1.e-10, 'Degenerate blended real quaternion')
        cq = conjugate(qb)
        numerator = qmul(qmul(qb,pure(self.points)),cq) + 2.*qmul(db,cq)
        predicted = numerator[:,1:]/n2[:,None]
        require(finite(predicted), 'Nonfinite DQ output')
        return (predicted,qb,db,signed,n2) if details else predicted

    def jacobian(self,q,t):
        predicted,qb,db,signed,n2 = self.evaluate(q,t,True)
        jac = np.zeros((800,3,192))
        r = rotations(q)
        basis = np.eye(3)
        for j in range(32):
            active = np.flatnonzero(self.weights[:,j] > 0.)
            eq = pure(basis)
            dq_rotation = .5*qmul(eq,q[j])
            rc = r[j]@self.centres[j]
            dt_rotation = np.cross(np.broadcast_to(rc,(3,3)),basis)
            dd_rotation = .5*(qmul(pure(dt_rotation),q[j])+qmul(pure(t[j]),dq_rotation))
            dq = np.vstack((dq_rotation,np.zeros((3,4))))
            dd = np.vstack((dd_rotation,.5*qmul(eq,q[j])))
            sq = signed[active,j,None,None]
            dqb, ddb = sq*dq[None,:,:], sq*dd[None,:,:]
            q0,d0 = qb[active,None,:], db[active,None,:]
            cq, dcq = conjugate(q0), conjugate(dqb)
            x = pure(self.points[active,None,:])
            dn = (qmul(qmul(dqb,x),cq)+qmul(qmul(q0,x),dcq)
                  +2.*qmul(ddb,cq)+2.*qmul(d0,dcq))[:,:,1:]
            norm_derivative = 2.*np.sum(q0*dqb,axis=-1)
            dy = (dn-predicted[active,None,:]*norm_derivative[:,:,None])/n2[active,None,None]
            jac[active,:,j*6:(j+1)*6] = dy.transpose(0,2,1)
        require(finite(jac), 'Nonfinite DQ Jacobian')
        return predicted,jac.reshape(2400,192)

    def increment(self,q,t,delta):
        delta = np.asarray(delta).reshape(32,6)
        qn,tn = q.copy(),t.copy()
        omega = delta[:,:3]
        angle = np.linalg.norm(omega,axis=1)
        factor = np.empty(32)
        small = angle < 1.e-10
        factor[small] = .5-angle[small]**2/48.
        factor[~small] = np.sin(.5*angle[~small])/angle[~small]
        dq = np.concatenate((np.cos(.5*angle)[:,None],omega*factor[:,None]),axis=1)
        old_r = rotations(q)
        qn[:32] = qmul(dq,q[:32])
        qn[:32] /= np.linalg.norm(qn[:32],axis=1)[:,None]
        new_r = rotations(qn)
        heads = np.einsum('nij,nj->ni',old_r[:32],self.centres)+t[:32]
        tn[:32] = heads+delta[:,3:]-np.einsum('nij,nj->ni',new_r[:32],self.centres)
        require(np.array_equal(qn[32],q[32]) and np.array_equal(tn[32],t[32]) and finite(tn), 'Fixed native Waist or finite state changed')
        return qn,tn


def stats(predicted,target,waist,meters):
    error = np.linalg.norm(predicted-target,axis=1)*meters
    free = np.setdiff1d(np.arange(800),waist)
    return {'all800_rms_mm':float(np.sqrt(np.mean(error*error))*1000.),
            'all800_max_mm':float(error.max()*1000.), 'maximum_raw_vertex_index':int(np.argmax(error)),
            'free720_rms_mm':float(np.sqrt(np.mean(error[free]**2))*1000.),
            'free720_max_mm':float(error[free].max()*1000.),
            'waist80_rms_mm':float(np.sqrt(np.mean(error[waist]**2))*1000.),
            'waist80_max_mm':float(error[waist].max()*1000.)}


def quaternion_matrix_states(matrices):
    return np.array([matrix_quaternion(m) for m in matrices]),matrices[:,:3,3].copy()


def derivative_proof(model,q,t):
    _,jac = model.jacobian(q,t)
    rng = np.random.default_rng(44051)
    checks = []
    for number in range(3):
        direction = rng.normal(size=(32,6))
        direction[:,3:] *= .05
        direction /= np.linalg.norm(direction)
        h = 1.e-6
        qp,tp = model.increment(q,t,h*direction)
        qm,tm = model.increment(q,t,-h*direction)
        numerical = ((model.evaluate(qp,tp)-model.evaluate(qm,tm))/(2.*h)).ravel()
        analytic = jac@direction.ravel()
        error = float(np.max(np.abs(analytic-numerical)))
        relative = float(np.linalg.norm(analytic-numerical)/max(np.linalg.norm(numerical),1.e-12))
        require(error < 2.e-7 and relative < 2.e-6, 'Analytic DQ derivative failed meaningful central difference')
        checks.append({'direction':number,'max_world_error':error,'relative_l2_error':relative,'central_step':h})
    return checks


def fit(model,q,t,target,deadline):
    start = time.perf_counter()
    initial = model.evaluate(q,t)
    loss = float(np.sum((initial-target)**2))
    initial_loss, damping, history = loss,1.e-5,[]
    stop = 'maximum_steps'
    for step in range(MAX_STEPS):
        if time.perf_counter() >= deadline:
            stop = 'global60_second_limit'
            break
        predicted,jac = model.jacobian(q,t)
        residual = (predicted-target).ravel()
        hessian, gradient = jac.T@jac,jac.T@residual
        diagonal = np.maximum(np.diag(hessian),1.e-8)
        delta = np.linalg.solve(hessian + damping*np.diag(diagonal),-gradient).reshape(32,6)
        require(finite(delta), 'Nonfinite GaussNewton step')
        ratio = max(1.,float(np.linalg.norm(delta[:,:3],axis=1).max())/.25,
                    float(np.linalg.norm(delta[:,3:],axis=1).max())/.025)
        delta /= ratio
        accepted = False
        previous = loss
        for alpha in (1.,.5,.25,.125,.0625):
            if time.perf_counter() >= deadline:
                break
            qn,tn = model.increment(q,t,alpha*delta)
            trial = float(np.sum((model.evaluate(qn,tn)-target)**2))
            if trial < loss:
                q,t,loss,accepted = qn,tn,trial,True
                damping = max(1.e-9,damping*.35)
                break
        if not accepted:
            damping = min(1.e5,damping*10.)
        history.append({'step':step+1,'squared_world_residual':loss,'accepted':accepted,'damping':damping})
        if accepted and previous-loss < max(1.e-14,previous*1.e-10):
            stop = 'least_squares_stagnation'
            break
        if not accepted and damping >= 1.e5:
            stop = 'damping_limit'
            break
    require(loss <= initial_loss+1.e-14,'Fitting increased least squares residual')
    return q,t,{'steps':len(history),'stop':stop,'elapsed_seconds':time.perf_counter()-start,
                'initial_squared_world_residual':initial_loss,'final_squared_world_residual':loss,'history':history}


def matrices_from_state(q,t):
    result = np.repeat(np.eye(4)[None,:,:],33,axis=0)
    result[:,:3,:3],result[:,:3,3] = rotations(q),t
    return result


def main():
    start = time.perf_counter()
    report = {'status':'failed','diagnostic_only':True,'production_effect_accepted':False,
              'native_graph_or_export_compatibility_proved':False,'collision_proved':False,
              'model':'rigid DQ,32 free proper R+t and one fixed native Waist; no scale/shear',
              'primary_source':PRIMARY,'primary_functions':['mat4_to_dquat','add_weighted_dq_dq','mul_v3m3_dq'],
              'limits':{'orthogonality':ORTH_LIMIT,'axis_scale_delta':SCALE_LIMIT,
                        'native_calibration_m':CALIBRATION_METRES,'steps_per_frame':MAX_STEPS,'global_seconds':MAX_SECONDS},
              'code_path':str(Path(__file__).resolve()),'code_sha256':sha(Path(__file__)),
              'numpy_version':np.__version__,'inputs':{},'calibration':[],'frames':[],'errors':[]}
    try:
        require(not OUTPUT.exists(),'Refusing to overwrite a prior QA report')
        native,target,initial = read_frozen(INPUT,INPUT_SHA),read_frozen(TARGET,TARGET_SHA),read_frozen(INITIAL,INITIAL_SHA)
        paths = ((INPUT,INPUT_SHA),(TARGET,TARGET_SHA),(INITIAL,INITIAL_SHA))
        report['inputs'] = {str(p):expected for p,expected in paths}
        require(native['status'] == 'passed' and native['cloth_replayed'] is False
                and native['artist_disk_exact'] and native['code_exact'] and native['sealed_input_exact'], 'Sealed native input proof failed')
        require(target['success'] and not target['production_effect_accepted'], 'Expected unreleased successful target evidence')
        groups = native['groups33']
        require([g[0] for g in groups] == list(range(33)) and groups[32][1] == 'SK_Dress_Waist', 'Exact33 group order changed')
        names = [g[1] for g in groups]
        require(len(set(names)) == 33 and set(names) == set(native['rest_bones']), 'Exact33 Rest identities differ')
        for row in native['native_weights800']:
            require(all(x['group_name'] == names[x['group_index']] for x in row['weights']), 'Group name/index identity mismatch')
        require(native['native_armature_parameters']['use_deform_preserve_volume']
                and native['native_armature_parameters']['use_vertex_groups']
                and not native['native_armature_parameters']['use_bone_envelopes']
                and not native['native_armature_parameters']['use_multi_modifier'], 'Native source DQ contract differs')
        model = DQModel(native['source_basis800_world'],native['native_weights800'])
        meters = native['scene_unit_scale_length']
        require(meters > 0.,'Invalid unit scale')
        bind = np.array(target['frozen_record']['fit']['matrix_world'])
        report['source_bind_matrix_world'] = bind.tolist()
        report['native_inputs_sha256'] = INPUT_SHA
        report['native_group_order33'] = groups
        rest = np.array([native['rest_bones'][name]['matrix'] for name in names])
        native_frames = {fr['frame']:fr for fr in native['frames']}
        target_frames = {fr['frame']:fr for fr in target['frames']}
        initializer_frames = {fr['frame']:fr for fr in initial['frames']}
        require(set(native_frames) == set(target_frames) == set(initializer_frames) == {1,7,25,30}, 'Four frame identities differ')
        relative_reference = None
        calibrated = {}
        for frame in (1,7,25,30):
            fr = native_frames[frame]
            a,m = np.array(fr['rig_evaluated_matrix_world']),np.array(fr['source_evaluated_matrix_world'])
            relative = np.linalg.inv(a)@m
            if relative_reference is None:
                relative_reference = relative
            drift = float(np.max(np.abs(relative-relative_reference)))
            require(drift < 2.e-6,'Source relative Rig transform changed; cannot reuse bind chart')
            chart = relative@np.linalg.inv(bind)
            captured_chart = np.array(fr['bind_world_to_current_rig_rest_input'])
            chart_delta = float(np.max(np.abs(chart-captured_chart)))
            require(chart_delta < 2.e-6,'Current SourceM/RigM bind chart mismatch')
            pose = np.array([fr['native_bones'][name]['pose_matrix_rig'] for name in names])
            for j,name in enumerate(names):
                require(np.array_equal(rest[j],np.array(fr['native_bones'][name]['rest_matrix_rig'])), 'Rest changed between frames')
            deformation = np.matmul(np.matmul(np.matmul(a[None,:,:],pose),np.linalg.inv(rest)),chart[None,:,:])
            orth = rigid_proof(deformation)
            q,t = quaternion_matrix_states(deformation)
            predicted = model.evaluate(q,t)
            raw = np.array(fr['raw_native_cold_physics_skin800_world'])
            difference = np.linalg.norm(predicted-raw,axis=1)*meters
            maximum = float(difference.max())
            proof = {'frame':frame,'all800_max_error_m':maximum,'all800_rms_error_m':float(np.sqrt(np.mean(difference**2))),
                     'maximum_raw_vertex_index':int(np.argmax(difference)),'matrix_proof':orth,
                     'source_relative_rig_max_delta':drift,'captured_bind_chart_max_delta':chart_delta,
                     'matrix_equation':'Dworld=Acurrent*Ppose*inverse(Brest)*inverse(Acurrent)*MsourceCurrent*inverse(MsourceBind)',
                     'not_source_world_before_scene60':True}
            report['calibration'].append(proof)
            if maximum > CALIBRATION_METRES:
                i = int(np.argmax(difference))
                proof['first_mismatch'] = {'raw_vertex_index':i,'predicted_world':predicted[i].tolist(),'native_world':raw[i].tolist(),
                                           'native_weights':native['native_weights800'][i]}
            require(maximum <= CALIBRATION_METRES, 'Rigid DQ calibration exceeds5um; no fitting or DQ exact claim')
            calibrated[frame] = (q,t,deformation)
        report['native_calibration_passed'] = True
        deadline = start+MAX_SECONDS
        for frame in (1,7,25,30):
            require(time.perf_counter() < deadline,'Global60 seconds exhausted before completing four fits')
            q_native,t_native,deformation = calibrated[frame]
            rows = initializer_frames[frame]['fitted32_proper_world_D']
            require([(v['group_index'],v['group_name']) for v in rows] == [(j,names[j]) for j in range(32)],'Initializer32 order differs')
            matrices = np.array([v['world_deformation_D'] for v in rows]+[deformation[32].tolist()])
            init_proof = rigid_proof(matrices)
            q,t = quaternion_matrix_states(matrices)
            q[32],t[32] = q_native[32],t_native[32]
            if frame == 1:
                report['analytic_jacobian_central_direction_checks'] = derivative_proof(model,q,t)
            wanted = np.asarray(target_frames[frame]['physical_world'],dtype=float)
            require(wanted.shape == (800,3) and finite(wanted),'Exact indexed Cloth800 target missing')
            before = stats(model.evaluate(q,t),wanted,model.only_waist,meters)
            q,t,fit_details = fit(model,q,t,wanted,deadline)
            final = model.evaluate(q,t)
            out_matrices = matrices_from_state(q,t)
            output_proof = rigid_proof(out_matrices)
            require(np.linalg.det(out_matrices[:,:3,:3]).min() > 1.-1.e-10,'Output SO3 proper determinant failed')
            report['frames'].append({'frame':frame,'initializer_rigid_proof':init_proof,'initializer_DQ_vs_Cloth':before,
                'fitted_DQ_vs_Cloth':stats(final,wanted,model.only_waist,meters),'fit':fit_details,
                'fixed_Waist_quaternion_translation_exact':bool(np.array_equal(q[32],q_native[32]) and np.array_equal(t[32],t_native[32])),
                'proper_rotation_proof':output_proof,'target_correspondence':'same raw800 indices; no nearest matching',
                'fitted32_proper_world_D':[{'group_index':j,'group_name':names[j],'world_deformation_D':out_matrices[j].tolist()} for j in range(32)],
                'predicted_raw800_world':final.tolist(),
                'fixed_native_waist_name':names[32],
                'fixed_native_waist_world_D':out_matrices[32].tolist(),
                'fixed_native_waist_raw_float_matrix':deformation[32].tolist()})
        require(all(sha(path) == expected for path,expected in paths),'Input changed during pure math')
        report['input_hashes_after_exact'] = True
        report['status'] = 'passed_math_only'
    except Exception as exc:
        report['errors'].append(str(exc))
        report['traceback'] = traceback.format_exc()
    report['elapsed_math_seconds'] = time.perf_counter()-start
    require(not OUTPUT.exists(),'Refusing to replace a previous QA result')
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'status':report['status'],'output':str(OUTPUT),'code_sha256':report['code_sha256'],
                      'elapsed_seconds':report['elapsed_math_seconds'],'errors':report['errors'],
                      'calibration':[{'frame':x['frame'],'max_m':x['all800_max_error_m']} for x in report['calibration']],
                      'fits':[{'frame':x['frame'],'before':x['initializer_DQ_vs_Cloth'],'after':x['fitted_DQ_vs_Cloth'],
                               'steps':x['fit']['steps'],'stop':x['fit']['stop']} for x in report['frames']]},ensure_ascii=False),flush=True)
    require(report['status'] == 'passed_math_only','Pure DQ QA did not complete; inspect its one retained report')


if __name__ == '__main__':
    main()
