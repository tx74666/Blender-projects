"""QA-only verification of fitted transforms with original native DQ weights.

Only the sealed waist-attachment QA scene is opened. Original Armature data is
retained untouched; a disposable copy permits 24 generated DEF connection flags
to be disabled. 32 independent Empty targets and late WORLD Copy Transforms
drive the existing DEF names. No explicit Cloth replay, reset, bake, artist file
or scene save; loading/restoring flags can still cause cold native evaluation.
The four physical targets come from frozen evidence, not a cold-cache replay.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import traceback

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import experimental_direct_cloth_render as direct
diag, qa, skirt, require = direct.diag,direct.qa,direct.skirt,direct.require
EVIDENCE = HERE/'waist_body_attachment_51_20261005_094107_823/result/experimental_actual_surface.json'
EVIDENCE_SHA = 'a6618bea6487ccada08a6c52c852a788a6c277f1e8b62d9fc0a6cce42ad1e861'
CAPTURE = HERE/'fit_inputs_51_20261005_102341_056/result/native_fit_inputs.json'
CAPTURE_SHA = '2ad843be7853801c6054c829488f269518d15d9b5334757f792e45277e20e19c'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_content(rig):
    return {pb.name:[direct.strict_rna(c) for c in pb.constraints] for pb in rig.pose.bones}


def drivers_content(rig):
    """Complete writable RNA plus nested native FCurve/driver settings.

    strict_rna keeps string and enum properties even when is_array is absent.
    Collection fields require explicit snapshots; order is preserved throughout.
    """
    strict = direct.strict_rna

    def modifier_content(modifier):
        result = {'rna': strict(modifier)}
        # Envelope control points are the native FModifier collection. Refuse
        # omission of any additional native collection exposed by a subtype.
        result['collections'] = {
            prop.identifier: [strict(member) for member in getattr(modifier, prop.identifier)]
            for prop in modifier.bl_rna.properties if prop.type == 'COLLECTION'}
        return result

    if rig.animation_data is None:
        return []
    return [{
        'path': curve.data_path,
        'index': curve.array_index,
        'curve': strict(curve),
        'group': ({'name': curve.group.name, 'rna': strict(curve.group)}
                  if curve.group is not None else None),
        'keyframes': [strict(point) for point in curve.keyframe_points],
        'sampled_points': [strict(point) for point in curve.sampled_points],
        'modifiers': [modifier_content(modifier) for modifier in curve.modifiers],
        'driver': strict(curve.driver),
        'variables': [{
            'rna': strict(variable),
            'targets': [strict(target) for target in variable.targets]}
            for variable in curve.driver.variables]}
        for curve in rig.animation_data.drivers]


def rest_copy_proof(before,after,names):
    require(list(before) == list(after),'Armature copy/rebuild changed bone order/names')
    maximum,length_delta = 0.,0.
    changed = []
    for name,a in before.items():
        b = after[name]
        expected = copy.deepcopy(a)
        if name in names:
            expected['connect'] = False
        require({k:v for k,v in expected.items() if k not in ('matrix','length')} ==
                {k:v for k,v in b.items() if k not in ('matrix','length')}, 'Unexpected Rest fields: '+name)
        error = max(abs(x-y) for ar,br in zip(a['matrix'],b['matrix']) for x,y in zip(ar,br))
        length = abs(a['length']-b['length'])
        maximum,length_delta = max(maximum,error),max(length_delta,length)
        if error or length:
            changed.append({'name':name,'matrix_max_delta':error,'length_delta':length})
    # This is a disposable data-copy numeric check, never a relaxed artist Rest
    # guarantee. The original native data buffer is restored exactly in finally.
    require(maximum < 1.e-6 and length_delta < 1.e-6,'Edit roundtrip altered disposable Rest beyond numeric guard')
    return {'changed_connected_only_names':names,'matrix_max_delta':maximum,
        'length_max_delta':length_delta,'numeric_rest_changes':changed,
        'original_data_buffer_untouched':True,'working_rest_bit_exact_except_connect':not changed,
        'production_rest_preservation_proved':False}


def stats(a,b,ids,meters):
    errors = [(Vector(a[i])-Vector(b[i])).length*meters for i in ids]
    return {'vertices':len(ids),'rms_m':math.sqrt(sum(e*e for e in errors)/len(errors)),
            'max_m':max(errors),'mean_m':sum(errors)/len(errors)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fit',type=Path,required=True)
    parser.add_argument('--fit-sha',required=True)
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.output,args.fit=args.output.resolve(),args.fit.resolve()
    require(bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath,'Factory background only')
    require(args.output.is_relative_to(HERE) and args.output!=HERE and not args.output.exists(),'Fresh QA output required')
    require(args.fit.is_relative_to(HERE) and file_hash(args.fit)==args.fit_sha,'Frozen fitted matrices changed')
    require(file_hash(EVIDENCE)==EVIDENCE_SHA and file_hash(CAPTURE)==CAPTURE_SHA,'Frozen native input evidence changed')
    evidence=json.loads(EVIDENCE.read_text('utf-8'))
    capture=json.loads(CAPTURE.read_text('utf-8'))
    fit=json.loads(args.fit.read_text('utf-8'))
    require(fit['native_calibration_passed'] and fit['native_inputs_sha256']==CAPTURE_SHA,
            'DQ calibration/native input proof did not pass')
    require(fit['input_hashes_after_exact'] and file_hash(Path(fit['code_path']))==fit['code_sha256'],
            'DQ producer code/input hashes changed')
    require(capture['status']=='passed' and capture['artist_disk_exact'] and capture['code_exact'],'Native capture did not pass')
    sealed=Path(evidence['saved_candidate']).resolve()
    require(sealed.is_relative_to(HERE) and sealed.name.startswith('Cosha_Dress_QA_') and
            qa.file_state(sealed)==evidence['candidate_file'],'Refuse artist/changed QA input')
    artist=HERE.parents[1]/'X.blend'
    before_artist=qa.file_state(artist)
    before_code=diag.source_manifest()
    args.output.mkdir()
    report={'status':'starting','artist_operation':False,'scene_saved':False,
        'cloth_replayed':False,'full_workflow_accepted':False,'production_effect_accepted':False,
        'fit_path':str(args.fit),'fit_sha256':args.fit_sha,'native_capture_sha256':CAPTURE_SHA,
        'frozen_targets_sha256':EVIDENCE_SHA,'frames':[],'errors':[],
        'limitations':['Four frozen Cloth targets only; no dynamic fitting/physics replay or canonical operations.',
                       'Generated connection flag change is limited to disposable Armature data; Original/animations/export are not validated.']}
    rig=None; old_data=None; working=None; probe=None; added=[]; helpers=[]; flags=[]; protected=None
    original_graph=None; saved_frame=None; original_source_hash=None
    try:
        diag.character_designer.register()
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(sealed),load_ui=False),'QA open failed')
        record=evidence['frozen_record']
        source,rig=bpy.data.objects[record['source']],bpy.data.objects[record['rig']]
        require(skirt.read_record(source)==record,'Authoritative record differs')
        saved_frame=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
        protected=qa.Protection()
        original_source_hash=direct.source_signature(source)
        original_graph=graph_content(rig)
        original_rest=qa.rest_content(rig)
        original_drivers=qa.digest(drivers_content(rig))
        original_channels={pb.name:diag.channels(pb) for pb in rig.pose.bones}
        manual_channels={n:diag.channels(rig.pose.bones[n]) for c in record['chains'] for n in c['manual']}
        all_names=[n for chain in record['chains'] for n in chain['def']]
        disconnected=[n for chain in record['chains'] for n in chain['def'][1:]]
        require(len(all_names)==32 and len(disconnected)==24,'Expected exact generated 8x4 graph')
        for obj in (bpy.data.objects[evidence['actual_cloth']['object']],bpy.data.objects[record['physics']['proxy']]):
            for modifier in obj.modifiers:
                if modifier.type=='CLOTH':
                    flags.append((modifier,modifier.show_viewport,modifier.show_render))
                    modifier.show_viewport=modifier.show_render=False
        require(flags,'Owned Cloth missing')
        if bpy.context.object and bpy.context.object.mode!='OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.hide_set(False); rig.select_set(True); bpy.context.view_layer.objects.active=rig
        old_data=rig.data
        working=old_data.copy()
        working.name='QA Disposable Generated Dress Connection Data'
        rig.data=working
        require(qa.rest_content(rig)==original_rest and graph_content(rig)==original_graph,'Native data copy changed Rest/graph')
        require('FINISHED' in bpy.ops.object.mode_set(mode='EDIT'),'Cannot edit disposable Armature data')
        for name in disconnected:
            require(rig.data.edit_bones[name].use_connect,'Expected connected generated child')
            rig.data.edit_bones[name].use_connect=False
        require('FINISHED' in bpy.ops.object.mode_set(mode='OBJECT'),'Cannot restore object mode')
        report['working_rest_copy_proof']=rest_copy_proof(original_rest,qa.rest_content(rig),disconnected)
        require(graph_content(rig)==original_graph,'Edit roundtrip changed original constraints')
        for index,name in enumerate(all_names):
            target=bpy.data.objects.new(f'QA Fitted Dress Target {index+1:02d}',None)
            bpy.context.scene.collection.objects.link(target)
            helpers.append(target)
            pb=rig.pose.bones[name]
            constraint=pb.constraints.new('COPY_TRANSFORMS')
            constraint.name='QA Fitted Complete World Transform'
            constraint.target=target
            constraint.owner_space=constraint.target_space='WORLD'
            constraint.mix_mode='REPLACE'
            constraint.remove_target_shear=False
            constraint.influence=1.
            added.append((name,constraint))
            constraint.active=False
            for old,saved in zip(pb.constraints,original_graph[name]):
                old.active=saved['active']
        report['new_constraints_native']=[{'bone':name,'constraint':direct.strict_rna(c),
            'target_name':c.target.name,'target_pointer':c.target.as_pointer(),
            'target_parent':qa.id_name(c.target.parent)} for name,c in added]
        require(all(not c.mute and c.enabled and c.influence==1. and c.type=='COPY_TRANSFORMS'
                    and c.mix_mode=='REPLACE' and not c.remove_target_shear
                    and c.owner_space==c.target_space=='WORLD' and not c.subtarget
                    and c.target==helper and c.target.parent is None and not c.active
                    for (name,c),helper in zip(added,helpers)), 'Native generated complete transform contract differs')
        probe=source.copy(); probe.name='QA Fitted DQ Raw Skin'
        bpy.context.scene.collection.objects.link(probe)
        arms=[m for m in probe.modifiers if m.type=='ARMATURE']
        require(len(arms)==1 and arms[0].object==rig and arms[0].use_deform_preserve_volume,'Expected original native DQ ARM')
        for modifier in tuple(probe.modifiers):
            if modifier!=arms[0]:
                require(modifier.type=='SUBSURF','Unsupported source modifier')
                probe.modifiers.remove(modifier)
        body=bpy.data.objects[evidence['body_clone']['original']]
        meters=bpy.context.scene.unit_settings.scale_length
        waist_group=source.vertex_groups[record['controls']['waist']].index
        fixed=[v.index for v in source.data.vertices if any(g.group==waist_group and g.weight==1. for g in v.groups)]
        free=[i for i in range(800) if i not in set(fixed)]
        require(len(fixed)==80 and len(free)==720,'Exact fixed/free source scope changed')
        bind_source=Matrix(record['fit']['matrix_world'])
        by_frame={f['frame']:f for f in fit['frames']}
        require(set(by_frame)=={1,7,25,30},'Expected exact frozen four frame set')
        for frozen in evidence['frames']:
            frame=frozen['frame']; fitted=by_frame[frame]
            rows=fitted['fitted32_proper_world_D']
            require(len(rows)==32 and {r['group_name'] for r in rows}==set(all_names),'Fit names differ from native 32 DEF')
            require(all(source.vertex_groups[r['group_name']].index==r['group_index'] for r in rows),
                    'Native fitted group indices differ')
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get()
            evaluated=rig.evaluated_get(graph)
            source_world=source.evaluated_get(graph).matrix_world.copy()
            q=evaluated.matrix_world.inverted()@source_world@bind_source.inverted()
            inverse_q=q.inverted()
            targets={r['group_name']:Matrix(r['world_deformation_D']) for r in rows}
            assignment_error=0.
            for name,target in zip(all_names,helpers):
                intended=targets[name]@inverse_q@rig.data.bones[name].matrix_local
                target.matrix_world=intended
                assignment_error=max(assignment_error,max(abs(x-y) for ar,br in zip(intended,target.matrix_world) for x,y in zip(ar,br)))
            require(assignment_error<5.e-6,'Empty TRS assignment changed desired world transform')
            for target in helpers:
                target.update_tag()
            rig.update_tag(); bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get()
            evaluated=rig.evaluated_get(graph)
            matrix_error=max(max(abs(x-y) for ar,br in zip(evaluated.matrix_world@evaluated.pose.bones[name].matrix,target.matrix_world)
                                  for x,y in zip(ar,br)) for name,target in zip(all_names,helpers))
            require(matrix_error<5.e-6,'Full world pose target transfer failed')
            native=diag.mesh_snapshot(probe,graph); final=diag.mesh_snapshot(source,graph)
            require(len(native['points'])==800 and len(final['points'])==3040,'Native topology/count changed')
            predicted=fitted['predicted_raw800_world']
            prediction=stats(native['points'],predicted,list(range(800)),meters)
            require(prediction['max_m']<5.e-6,'Mathematical DQ prediction differs from original native ARM')
            body_mesh=diag.mesh_snapshot(body,graph)
            witnesses=frozen['evaluated_body_triangle_evidence']['vertices']
            body_error=max((body_mesh['points'][w['evaluated_vertex_index']]-Vector(w['world'])).length*meters for w in witnesses)
            require(body_error<5.e-6,'Disposable Rest roundtrip changed Body witness beyond 5um')
            native['free_indices']=free
            final['free_indices']=direct.base.free_indices(final,source.vertex_groups[record['controls']['waist']])
            bounds=diag.framing(rig,record,graph)
            epsilon=max(1.e-8,record['fit']['height_world']*1.e-6)
            raw_cross=diag.triangle_crossings(native,body_mesh,bounds,2000,epsilon)
            final_cross=diag.triangle_crossings(final,body_mesh,bounds,2000,epsilon)
            layers=direct.mesh_layers(source,graph)
            require(qa.digest(layers)==frozen['direct_cloth_output']['final3040']['same_final_layers_sha256'],
                    'Fitting changed nonposition final layers/native weights')
            item={'frame':frame,'full_world_pose_target_max_delta':matrix_error,
                'world_empty_assignment_max_delta':assignment_error,
                'prediction_vs_native800':prediction,'body_14_witness_max_delta_m':body_error,
                'native800_vs_frozen_cloth':stats(native['points'],frozen['physical_world'],list(range(800)),meters),
                'native720_vs_frozen_cloth':stats(native['points'],frozen['physical_world'],free,meters),
                'fixed80_vs_frozen_cloth':stats(native['points'],frozen['physical_world'],fixed,meters),
                'raw800_body_crossings':raw_cross,'final3040_body_crossings':final_cross,
                'final_layers_sha256':qa.digest(layers),
                'native800_world':[diag.vector(p) for p in native['points']]}
            report['frames'].append(item)
            if args.render and frame==25:
                render=args.output/'native_fitted_render'; render.mkdir()
                item['render']=diag.native_render(SimpleNamespace(frame=frame,output=render),final,body_mesh,bounds)
                require(item['render']['success'],'Native snapshot rendering failed')
        require({n:diag.channels(rig.pose.bones[n]) for n in manual_channels}==manual_channels,'Fitting changed manual channels')
        require(direct.source_signature(source)==original_source_hash,'Fitting changed source weights/keys/modifiers/metadata')
        report['status']='passed'
    except BaseException:
        report['status']='failed'; report['errors'].append(traceback.format_exc())
    finally:
        def cleanup(label,operation):
            try:
                operation()
            except BaseException:
                report['status']='failed'; report['errors'].append(label+'\n'+traceback.format_exc())
        if probe is not None:
            cleanup('remove owned raw probe',lambda:bpy.data.objects.remove(probe,do_unlink=True))
        if rig is not None:
            if rig.mode!='OBJECT' and bpy.context.object==rig:
                cleanup('leave disposable Edit Mode',lambda:bpy.ops.object.mode_set(mode='OBJECT'))
            for name,constraint in added:
                cleanup('remove owned constraint '+name,lambda n=name,c=constraint:rig.pose.bones[n].constraints.remove(c))
            for name,values in (original_graph or {}).items():
                for index,saved in enumerate(values):
                    cleanup('restore constraint active '+name,
                            lambda n=name,i=index,s=saved:setattr(rig.pose.bones[n].constraints[i],'active',s['active']))
            if old_data is not None:
                # This priority restoration is independent of every other
                # cleanup item, including constraint/probe removal failures.
                cleanup('restore original native Armature buffer',lambda:setattr(rig,'data',old_data))
        for helper in helpers:
            cleanup('remove owned target '+helper.name,lambda h=helper:bpy.data.objects.remove(h,do_unlink=True))
        if working is not None:
            def remove_working():
                require(working.users==0,'Disposable Armature data still referenced')
                bpy.data.armatures.remove(working)
            cleanup('remove disposable Armature data',remove_working)
        for modifier,viewport,render in flags:
            cleanup('restore owned Cloth viewport',lambda m=modifier,v=viewport:setattr(m,'show_viewport',v))
            cleanup('restore owned Cloth render',lambda m=modifier,r=render:setattr(m,'show_render',r))
        if saved_frame is not None:
            cleanup('restore QA frame',lambda:bpy.context.scene.frame_set(saved_frame[0],subframe=saved_frame[1]))
            cleanup('update restored graph',lambda:bpy.context.view_layer.update())
        if protected is not None:
            def verify_restored():
                report['protected_after']=protected.verify()
                require(report['protected_after']['success'],'Native verification rollback changed protected assets')
                require(graph_content(rig)==original_graph,'Rollback changed native original constraints')
                require(qa.digest(drivers_content(rig))==original_drivers,'Rollback changed native original drivers')
                require({pb.name:diag.channels(pb) for pb in rig.pose.bones}==original_channels,
                        'Rollback changed native original pose inputs')
                require(direct.source_signature(source)==original_source_hash,'Rollback changed source signature')
                report['original_graph_rollback_exact']=True
                report['original_armature_data_identity_restored']=rig.data==old_data
            cleanup('verify restored original graph/assets',verify_restored)
        report['artist_disk_exact']=qa.file_state(artist)==before_artist
        report['code_exact']=diag.source_manifest()==before_code
        report['sealed_input_exact']=qa.file_state(sealed)==evidence['candidate_file']
        if not (report['artist_disk_exact'] and report['code_exact'] and report['sealed_input_exact']):
            report['status']='failed'; report['errors'].append('Protected file state changed')
        (args.output/'native_fitted_dq.json').write_text(json.dumps(diag.json_content(report),ensure_ascii=False,allow_nan=False,indent=2),'utf-8')
    require(report['status']=='passed','Native fitted DQ verification failed; inspect preserved report')


if __name__=='__main__':
    main()
