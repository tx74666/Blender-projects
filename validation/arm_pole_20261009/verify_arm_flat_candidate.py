"""Full real-character regression, on a protected .blend only."""
import bpy
import ast
import importlib.util
import json
import math
import os
import sys
import hashlib
import traceback
from pathlib import Path
from mathutils import Matrix, Vector

assert bpy.app.background
BASE = Path(__file__).resolve().parent
OUT = BASE.parent / 'arm_flat_fix_20261009'
OUT.mkdir(exist_ok=True)
SOURCE = Path(os.environ.get('ARM_FLAT_SOURCE', str(OUT / 'candidate')))
CHECKPOINT = Path(os.environ.get('ARM_FLAT_CHECKPOINT', str(BASE / 'X_before_arm_pole_seed_repair.blend')))
ARTIST = BASE.parent.parent / 'X.blend'
sys.path.insert(0, str(SOURCE))
import character_designer
character_designer.register()
from character_designer import control_pose_assets as poses, control_pose_mirror as mirror
from character_designer import limb_ik, limb_ik_fk as match, body_original_mode as original

spec = importlib.util.spec_from_file_location('real_protection_helpers', str(BASE.parent / 'arm_flat_mirror_20261008' / 'isolated_character_validation.py'))
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
proof.poses = poses
proof.match = match
proof.limb_ik = limb_ik
old = json.loads((BASE.parent / 'arm_flat_mirror_20261008' / 'live_before.json').read_text(encoding='utf-8'))
seeds = {'ARM/'+side: {n+'.'+side: {'rotation_mode':'QUATERNION', 'matrix_basis':old['bones'][n+'.'+side]['basis']}
                       for n in ('upper_arm', 'forearm', 'hand')} for side in ('L','R')}
(OUT / 'stable_ik_seed.json').write_text(json.dumps(seeds, indent=2), encoding='utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before_files = {str(p):sha(p) for p in (ARTIST,CHECKPOINT)}
report = {'runtime': character_designer.bl_info['version'], 'source':str(SOURCE),
          'checkpoint':str(CHECKPOINT), 'cases':[], 'passed':False}

def update(): match._update(bpy.context, rig)
def read(side):
    a,b,c = [rig.pose.bones[n+'.'+side].matrix.translation.copy() for n in ('upper_arm','forearm','hand')]
    axis = (c-a).normalized()
    radial = b-a-axis*(b-a).dot(axis)
    back = Vector((0,1,0)); back -= axis*back.dot(axis)
    return {'posterior_dot':radial.normalized().dot(back.normalized()),
            'radial_ratio':radial.length/(c-a).length, 'direction':list(radial.normalized())}
def snapshot(): return {p.name:(p.rotation_mode,p.matrix_basis.copy(),p.get('ik_fk')) for p in rig.pose.bones}
def restore(state):
    for n,(mode,basis,value) in state.items():
        p=rig.pose.bones[n]; p.rotation_mode=mode; p.matrix_basis=basis
        if value is not None:p['ik_fk']=value
    update()

try:
    for label,flipped,side,mode,tagged in (('normal_ik',False,'L','IK',True),('mirrored_ik',True,'R','IK',True),
                                        ('normal_fk',False,'L','FK',True),('mirrored_fk',True,'R','FK',True),
                                        ('untagged_ik_exact',False,'L','IK',False),
                                        ('tagged_original_exact',False,'L','ORIGINAL',True),
                                        ('both_arms_atomic',False,'L','IK',True)):
        assert bpy.ops.wm.open_mainfile(filepath=str(CHECKPOINT),load_ui=False,use_scripts=False)=={'FINISHED'}
        rig=bpy.data.objects['CoshaRig']; proof.rig=rig
        bpy.context.view_layer.objects.active=rig; rig.select_set(True)
        limb_ik._mode_set(bpy.context,rig,'POSE')
        bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
        assert not original.active(rig)
        asset=bpy.data.actions['Arm Flat']; metadata=poses.asset_metadata(asset)
        if tagged:
            metadata.update(stable_ik_bend=True,stable_ik_seed=seeds)
            asset[poses.ASSET_METADATA]=json.dumps(metadata,separators=(',',':'))
        entry=limb_ik._validate_inventory(rig)['rigs'][('ARM',side)]
        if mode=='FK':match.switch_limb(bpy.context,rig,('ARM',side),'FK',keyframe=False,sync_display=False)
        if mode=='ORIGINAL':original.enter(bpy.context,rig)
        values=poses.channels(asset,rig)
        authored=mirror.mirrored_channels(rig,values,metadata=metadata) if flipped else values
        if label=='both_arms_atomic':
            authored=dict(authored)
            authored.update(mirror.mirrored_channels(rig,values,metadata=metadata))
        wanted=poses.desired_pose(rig,authored,metadata)
        protected=proof.protected_state(rig)
        poles=proof.poles(rig); raw_before=proof.raw_state(rig)
        result=poses.apply_channels(bpy.context,rig,authored,metadata=metadata)
        update()
        raw_after=proof.raw_state(rig)
        raw_diff={n:proof.raw_error(raw_before[n],raw_after[n]) for n in raw_before
                  if proof.raw_error(raw_before[n],raw_after[n])>=2e-5}
        (OUT/'current_raw_diagnostic.json').write_text(json.dumps({'case':label,'differences':raw_diff,
            'before':{n:raw_before[n] for n in raw_diff},'after':{n:raw_after[n] for n in raw_diff}},indent=2),encoding='utf-8')
        case={'label':label,'side':side,'mode':mode,'tagged':tagged,'result':result,'drag':[]}
        errors={n:{'position':(rig.pose.bones[n].matrix.translation-wanted[n].translation).length,
                   'rotation':match._pose_errors(rig,{n:wanted[n]})[1],
                   'matrix':poses._difference(rig.pose.bones[n].matrix,wanted[n])}
                for n in entry['chain']}
        case['errors']=errors
        report['cases'].append(case)
        assert proof.protected_state(rig)==protected, 'Rest/weights/mesh/Shape Keys/asset curves changed'
        assert proof.poles(rig)==poles
        if mode=='ORIGINAL':assert original.active(rig)
        else:assert match.mode_for_rig(rig,entry)==mode
        fingers=[n for n in raw_before if n.startswith(('f_','thumb.'))]
        assert all(proof.raw_error(raw_before[n],raw_after[n])<2e-5 for n in fingers)
        case['fingers_checked']=len(fingers)
        if mode in {'FK','ORIGINAL'} or not tagged:
            assert max(e['matrix'] for e in errors.values())<4e-4
        else:
            reach=(wanted[entry['chain'][2]].translation-wanted[entry['chain'][0]].translation).length
            assert max(e['position'] for e in errors.values())<reach*.02
            assert max(e['rotation'] for e in errors.values())<math.radians(3)
            assert errors[entry['chain'][2]]['position']<1e-5
            for n,item in seeds['ARM/'+side].items():
                assert poses._difference(rig.pose.bones[n].matrix_basis,Matrix(item['matrix_basis']))<2e-6
            applied=snapshot()
            for clear in (False,True):
                for fraction in (.02,.15,.30):
                    restore(applied)
                    if clear:
                        for prefix in ('CTRL_hand_IK.','CTRL_elbow_pole.'):
                            p=rig.pose.bones[prefix+side]; p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0)
                        update()
                    a=rig.pose.bones[entry['chain'][0]].matrix.translation
                    c=rig.pose.bones[entry['chain'][2]].matrix.translation
                    target=rig.pose.bones[entry['target'].name]; m=target.matrix.copy()
                    m.translation+=(a-c)*fraction;target.matrix=m;update()
                    geometry=read(side)
                    case['drag'].append(dict(clear_controls=clear,retract=fraction,**geometry))
                    assert geometry['radial_ratio']>.02 and geometry['posterior_dot']>.97
            restore(applied)
        case['passed']=True
        print('ARM_FLAT_REAL_PASS',label,flush=True)
    assert {str(p):sha(p) for p in (ARTIST,CHECKPOINT)}==before_files
    report['passed']=True
except Exception:
    report['error']=traceback.format_exc()
    raise
finally:
    report['files_unchanged']={str(p):sha(p)==before_files[str(p)] for p in (ARTIST,CHECKPOINT)}
    (OUT / 'real_candidate_verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
