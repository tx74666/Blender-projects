"""Isolated four-frame native QA of O = S + (C - H0), not a released workflow.

S is an independent author-mesh copy using the existing native manual/PHYS Rig
and its copied Shape Keys. H has a separate Rig, Armature data, Action, eight
manual Wire curves and fixed Basis mesh. H0 preserves Body and physical inputs,
but uses neutral Controls REPLACE instead of the validated current DEF local
correction, and neutralizes the exact generated manual channels. C is the sealed, indexed
four-frame Cloth evidence; no Cloth replay, bake, artist scene save or export.
S-H0 includes the existing DEF correction and added manual/Key deltas. C has
waist-only/body-attachment inputs, not that correction. With a correction the
guard requires O-C = S-H0; only without a correction are S=H0 and O=C required.
Ambiguous neutral input is rejected, rather than guessed from final DEF pose.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
DEPENDENCIES = {
    'experimental_direct_cloth_render.py': '835d7f8caba4220f7aef2d74857d25a4c0c08a31a56dc9c5a7daf8b87fb28a2f',
    'experimental_waist_body_attachment.py': 'f4bb7711327d1ac7d6295073476c97a6ef9a2e2a85fc016ca0c6253c663c0278',
    'capture_native_fit_inputs.py': '38601f52dafc1b922cd894889bacc1af27dbaa6deeaaaa65d27495ea8ce418a2',
}
for filename, expected in DEPENDENCIES.items():
    if hashlib.sha256((HERE/filename).read_bytes()).hexdigest() != expected:
        raise RuntimeError('Frozen QA dependency changed: '+filename)
sys.path.insert(0, str(HERE))
import experimental_direct_cloth_render as direct
import capture_native_fit_inputs as capture

diag, qa, skirt, require = direct.diag, direct.qa, direct.skirt, direct.require
strict = direct.strict_rna
CORRECTIONS = 'character_designer_skirt_pose_corrections_v1'
ORIGINAL = 'character_designer_body_original_mode_v1'
LIMIT_METRES = 2.e-6
NODES = {'Input':'NodeGroupInput','Output':'NodeGroupOutput',
         'Position':'GeometryNodeInputPosition','Index':'GeometryNodeInputIndex',
         'Cloth':'GeometryNodeObjectInfo','Reference':'GeometryNodeObjectInfo',
         'Cloth Index':'GeometryNodeSampleIndex','Reference Index':'GeometryNodeSampleIndex',
         'Difference':'ShaderNodeVectorMath','Overlay':'ShaderNodeVectorMath',
         'Set Position':'GeometryNodeSetPosition'}


def graph_content(rig):
    return {bone.name:[strict(constraint) for constraint in bone.constraints] for bone in rig.pose.bones}


def driver_curves(rig):
    return list(rig.animation_data.drivers) if rig.animation_data else []


def drivers_content(rig):
    return [{'curve':strict(curve),'keys':[strict(point) for point in curve.keyframe_points],
             'samples':[strict(point) for point in curve.sampled_points],
             'modifiers':[{'rna':strict(modifier),'collections':{
                 prop.identifier:[strict(item) for item in getattr(modifier,prop.identifier)]
                 for prop in modifier.bl_rna.properties if prop.type=='COLLECTION'}} for modifier in curve.modifiers],
             'driver':strict(curve.driver),'variables':[{'rna':strict(variable),
                 'targets':[strict(target) for target in variable.targets]}
                 for variable in curve.driver.variables]} for curve in driver_curves(rig)]


def action_curves(action):
    if action is None:
        return []
    result=[]
    for layer in getattr(action,'layers',()):
        for strip in layer.strips:
            for bag in getattr(strip,'channelbags',()):
                result.extend(bag.fcurves)
    if getattr(action,'is_action_legacy',False) and hasattr(action,'fcurves'):
        result.extend(action.fcurves)
    return result


def curve_storage(obj):
    return {'data':strict(obj.data),'modifiers':[strict(modifier) for modifier in obj.modifiers],
        'splines':[{'rna':strict(spline),'points':[strict(point) for point in spline.points],
            'bezier_points':[strict(point) for point in spline.bezier_points]} for spline in obj.data.splines]}


def no_animation(owner, label):
    animation=owner.animation_data
    require(animation is None or (animation.action is None and not animation.nla_tracks and not animation.drivers),
            label+' animation/driver is outside this fixed fixture')


def owned_names(record):
    controls=record['controls']
    names=[controls[level] for level in ('waist','mid','hem')]
    names += [name for entry in controls['chains'] for name in entry.values()]
    names += [name for chain in record['chains'] for name in chain['manual']]
    return names


def identity_channels(bone):
    matrix=bone.matrix_basis
    return max(abs(matrix[row][col]-(1. if row==col else 0.)) for row in range(4) for col in range(4))<1.e-7


def def_basis_content(rig,record):
    return {name:{'channels':diag.skirt_original_mode._channels(rig.pose.bones[name]),
                  'basis':diag.matrix(rig.pose.bones[name].matrix_basis)}
            for chain in record['chains'] for name in chain['def']}


def correction_preflight(source,rig,record,report):
    # The saved entry is the old dormant basis for Clear, not the current delta.
    # Do not substitute it for current S. Current native DEF channels are copied
    # into H0 unchanged but are dormant there under neutral Controls REPLACE.
    canonical=diag.skirt_original_mode
    correction=canonical._corrections(source,record)
    relations=canonical._relations(rig,source,record)
    require(len(relations)==32,'Exact32 canonical Dress relations required')
    current=def_basis_content(rig,record)
    require(all(math.isfinite(number) for value in current.values()
                for values in value['channels']['channels'].values() for number in values)
            and all(math.isfinite(number) for value in current.values() for row in value['basis'] for number in row),
            'Existing DEF correction channels/basis are nonfinite')
    raw=source.get(CORRECTIONS)
    report['existing_DEF_correction']={'present':raw is not None,
        'raw_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest() if raw is not None else None,
        'parsed_sha256':qa.digest(correction),'owner':correction['owner'],
        'corrected_bone_names':sorted(correction['bones']),'current_native_DEF_basis_sha256':qa.digest(current),
        'saved_channels_are_clear_baseline_not_current_delta':True,
        'source_current_basis_and_correction_record_preserved':True,
        'H0_keeps_copied_raw_DEF_channels_dormant_under_REPLACE':True,
        'H0_metadata_does_not_claim_an_active_correction':True,
        'baseline_scope':'S-H0 contains existing correction plus additional manual/Key deltas',
        'reason':'Frozen Cloth C does not contain32 DEF correction; H0 must exclude its effect rather than cancelling it from S'}
    return correction


def neutral_preflight(source,rig,record,report):
    require(ORIGINAL not in rig,'Neutral ambiguous: active Body Original session is present')
    correction=correction_preflight(source,rig,record,report)
    names=owned_names(record)
    require(len(set(names))==len(names), 'Generated manual names are not unique')
    require(all(name in rig.pose.bones for name in names), 'Exact saved manual bones are missing')
    prefixes=tuple(rig.pose.bones[name].path_from_id()+'.' for name in names)
    animation=rig.animation_data
    require(animation is None or not animation.nla_tracks, 'Reference Body NLA synchronization is not proved')
    blocked=[{'path':curve.data_path,'index':curve.array_index,'kind':kind}
             for kind,curves in (('Action',action_curves(animation.action if animation else None)),
                                 ('Driver',driver_curves(rig))) for curve in curves if curve.data_path.startswith(prefixes)]
    report['neutral_preflight']={'manual_names':names,'blocked_paths':blocked,
        'definition':'Generated manual identity basis and saved fitted curves; same Body/PHYS inputs with independent DEF Controls REPLACE; never evaluated final DEF as H0'}
    require(not blocked, 'Neutral ambiguous: generated manual channels have animation/driver: '+str(blocked))
    require(all(identity_channels(rig.pose.bones[name]) for name in names),
            'Neutral ambiguous: author manual channels are not identity at saved frame')
    require([modifier.type for modifier in source.modifiers]==['ARMATURE','SUBSURF']
            and source.modifiers[0].object==rig and source.modifiers[0].use_deform_preserve_volume,
            'Expected original native DQ Armature then Subsurf')
    require(len(source.data.vertices)==800 and len(source.vertex_groups)==33, 'Exact indexed800/33 groups fixture required')
    for owner,label in ((source,'Source object'),(source.data,'Source mesh'),(source.data.shape_keys,'Source Keys')):
        if owner is not None:
            no_animation(owner,label)
    require(not source.constraints and not source.show_only_shape_key,'Unsupported source constraints/key-only display')
    keys=source.data.shape_keys
    require(keys is None or (keys.use_relative and all(key==keys.reference_key or key.mute or key.value==0.
            for key in keys.key_blocks)), 'Neutral ambiguous: active/absolute artist Shape Key')
    for chain in record['chains']:
        for name,manual_name,physics_name in zip(chain['def'],chain['manual'],chain['phys']):
            constraints=list(rig.pose.bones[name].constraints)
            require(len(constraints)==2, 'Neutral ambiguous: DEF has an extra correction/constraint: '+name)
            manual,physics=constraints
            require(manual.type=='COPY_TRANSFORMS' and manual.name=='Skirt manual pose' and manual.target==rig
                    and manual.subtarget==manual_name and manual.owner_space==manual.target_space=='LOCAL'
                    and manual.mix_mode==('BEFORE_FULL' if name in correction['bones'] else 'REPLACE')
                    and not manual.mute and manual.influence==1.,
                    'Neutral ambiguous: manual native contract changed: '+name)
            require(physics.type=='COPY_ROTATION' and physics.name=='Skirt physics delta' and physics.target==rig
                    and physics.subtarget==physics_name and physics.owner_space==physics.target_space=='LOCAL'
                    and physics.mix_mode=='BEFORE' and not physics.mute,
                    'Neutral ambiguous: physics native contract changed: '+name)
        wire=bpy.data.objects[chain['curve']]
        expected_parent=('BONE',record['shared']['anchor']) if skirt.is_shared(record) else ('OBJECT','')
        require(wire.type=='CURVE' and not wire.constraints and wire.parent==rig
                and (wire.parent_type,wire.parent_bone)==expected_parent,
                'Exact independent reference manual Wire parent required')
        no_animation(wire,'Manual wire'); no_animation(wire.data,'Manual curve data')
        require(wire.data.shape_keys is None,'Manual Wire Shape Key neutral source is not proved')
        require(len(wire.modifiers)==3 and all(modifier.type=='HOOK' and modifier.object==rig
                for modifier in wire.modifiers), 'Unknown manual curve input: '+wire.name)
    return names


class Owned:
    def __init__(self):
        self.objects=[]; self.meshes=[]; self.curves=[]; self.armatures=[]; self.actions=[]; self.groups=[]; self.keys=[]

    def object_copy(self,source,name):
        result=source.copy(); self.objects.append(result)
        result.name=name; bpy.context.scene.collection.objects.link(result)
        return result

    def cleanup(self,report):
        for collection,items in ((bpy.data.objects,self.objects),(bpy.data.node_groups,self.groups),
                (bpy.data.meshes,self.meshes),(bpy.data.curves,self.curves),
                (bpy.data.armatures,self.armatures),(bpy.data.actions,self.actions)):
            for item in reversed(items):
                try:
                    require(collection.get(item.name)==item,'Owned cleanup pointer no longer identifies its ID')
                    if collection!=bpy.data.objects:
                        require(item.users==0,'Owned QA data acquired an external user: '+item.name)
                    collection.remove(item,do_unlink=True)
                except BaseException:
                    report['errors'].append('Owned cleanup: '+traceback.format_exc())
        for name,pointer in self.keys:
            try:
                key=bpy.data.shape_keys.get(name)
                if key is not None:
                    require(key.as_pointer()==pointer and key.users==0,'Owned Key pointer/users changed')
                    bpy.data.batch_remove(ids=(key,))
            except BaseException:
                report['errors'].append('Owned Key cleanup: '+traceback.format_exc())


def clear_metadata(obj):
    for key in list(obj.keys()):
        del obj[key]
    obj['CD_QA_IndependentNativeOverlay']=True


def clone_reference(rig,source,record,names,owned,report):
    original_DEF_basis=def_basis_content(rig,record)
    reference=owned.object_copy(rig,'QA Neutral Physical Reference Rig')
    reference.data=rig.data.copy(); owned.armatures.append(reference.data)
    reference.data.name='QA Neutral Physical Reference Armature Data'
    require(reference.data!=rig.data and qa.rest_content(reference)==qa.rest_content(rig), 'Reference native Rest copy differs')
    for key in list(reference.keys()):
        if key in (skirt.OWNER_KEY,skirt.RECORD_KEY,skirt.RIG_KEY,ORIGINAL):
            del reference[key]
    reference['CD_QA_NeutralPhysicalReference']=True
    for curve in driver_curves(rig):
        for variable in curve.driver.variables:
            for target in variable.targets:
                if target.id==rig and variable.type=='SINGLE_PROP':
                    try:
                        original_value=qa.custom_content(rig.path_resolve(target.data_path))
                        reference_value=qa.custom_content(reference.path_resolve(target.data_path))
                    except Exception as exc:
                        raise RuntimeError('Reference input path is not independently available: '+target.data_path) from exc
                    require(reference_value==original_value,'Reference copied custom driver input differs: '+target.data_path)
    wires={}
    for chain in record['chains']:
        original=bpy.data.objects[chain['curve']]
        wire=owned.object_copy(original,'QA Neutral '+original.name)
        wire.data=original.data.copy(); owned.curves.append(wire.data)
        clear_metadata(wire)
        wire.parent=reference
        wire.parent_type,wire.parent_bone=original.parent_type,original.parent_bone
        wire.matrix_parent_inverse=original.matrix_parent_inverse.copy()
        wire.matrix_basis=original.matrix_basis.copy()
        require(wire.parent==reference and (wire.parent_type,wire.parent_bone)==(original.parent_type,original.parent_bone)
                and diag.matrix(wire.matrix_parent_inverse)==diag.matrix(original.matrix_parent_inverse)
                and diag.matrix(wire.matrix_basis)==diag.matrix(original.matrix_basis),
                'Reference Wire changed outside its exact parent Rig ID')
        for old,new in zip(original.modifiers,wire.modifiers):
            inverse,center=old.matrix_inverse.copy(),old.center.copy()
            new.object=reference
            # The native Hook setter recalculates inverse. Rest/units are the
            # same in this clone, so retain the exact old inverse and center.
            new.matrix_inverse,new.center=inverse,center
            expected=strict(old); expected['object']=qa.id_name(reference)
            require(strict(new)==expected,'Reference Hook changed more than exact Rig ID')
        wires[original]=wire
    redirects=[]
    for original_bone,reference_bone in zip(rig.pose.bones,reference.pose.bones):
        require(original_bone.name==reference_bone.name and original_bone.as_pointer()!=reference_bone.as_pointer(),
                'Reference pose list is not independent')
        require(len(original_bone.constraints)==len(reference_bone.constraints),'Reference constraint count changed')
        for original_constraint,constraint in zip(original_bone.constraints,reference_bone.constraints):
            require(original_constraint.as_pointer()!=constraint.as_pointer(), 'Reference constraint is shared')
            expected=strict(original_constraint)
            for prop in original_constraint.bl_rna.properties:
                if prop.type=='POINTER' and not prop.is_readonly:
                    original_target=getattr(original_constraint,prop.identifier)
                    copied_target=getattr(constraint,prop.identifier)
                    if original_target==rig or original_target in wires:
                        replacement=reference if original_target==rig else wires[original_target]
                        require(copied_target==original_target or copied_target==replacement,
                                'Native copied constraint pointer has an undeclared replacement')
                        setattr(constraint,prop.identifier,replacement)
                        expected[prop.identifier]=qa.id_name(replacement)
                        redirects.append((reference_bone.name,constraint.name,prop.identifier,qa.id_name(replacement)))
                    else:
                        require(copied_target==original_target,'Native copied constraint changed an external pointer')
            require(strict(constraint)==expected, 'Reference constraint changed outside declared target redirect')
    require(len(rig.constraints)==len(reference.constraints),'Reference object constraint count changed')
    for old,new in zip(rig.constraints,reference.constraints):
        expected=strict(old)
        for prop in old.bl_rna.properties:
            if prop.type=='POINTER' and not prop.is_readonly:
                original_target=getattr(old,prop.identifier); copied_target=getattr(new,prop.identifier)
                if original_target==rig or original_target in wires:
                    replacement=reference if original_target==rig else wires[original_target]
                    require(copied_target==original_target or copied_target==replacement,
                            'Native copied object constraint pointer has an undeclared replacement')
                    setattr(new,prop.identifier,replacement); expected[prop.identifier]=qa.id_name(replacement)
                else:
                    require(copied_target==original_target,'Native copied object constraint changed an external pointer')
        require(strict(new)==expected,'Reference object constraint changed outside self target')
    if rig.animation_data and rig.animation_data.action:
        action=rig.animation_data.action.copy(); owned.actions.append(action)
        action.use_fake_user=False
        original_action=qa.action_content(rig.animation_data.action); copied_action=qa.action_content(action)
        for content in (original_action,copied_action):
            for key in ('name','name_full','use_fake_user'):
                content['rna'].pop(key,None)
        require(action!=rig.animation_data.action and copied_action==original_action,
                'Independent Body Action copy changed values')
        report['reference_action_copy']={'original':rig.animation_data.action.name,'owned_copy':action.name,
            'original_use_fake_user':rig.animation_data.action.use_fake_user,'owned_use_fake_user':action.use_fake_user,
            'allowed_copy_metadata_differences':['name','name_full','use_fake_user'],
            'reason':'Native Action.copy omits fake-user; the independent QA Action must have no fake/external user at cleanup'}
        reference.animation_data.action=action
        # Keep the native copied slot relationship; fail rather than infer slots.
        if hasattr(rig.animation_data,'action_slot'):
            handle=rig.animation_data.action_slot_handle
            slots=[slot for slot in action.slots if slot.handle==handle]
            require(len(slots)==1,'Reference copied Body Action slot is ambiguous')
            reference.animation_data.action_slot=slots[0]
    original_drivers=driver_curves(rig); copied_drivers=driver_curves(reference)
    require(len(original_drivers)==len(copied_drivers),'Reference driver count differs')
    driver_redirects=[]
    expected_drivers=copy.deepcopy(drivers_content(rig))
    for index,(old,new) in enumerate(zip(original_drivers,copied_drivers)):
        require(old.as_pointer()!=new.as_pointer(),'Reference driver FCurve is shared')
        for variable_index,(old_variable,new_variable) in enumerate(zip(old.driver.variables,new.driver.variables)):
            for target_index,(old_target,new_target) in enumerate(zip(old_variable.targets,new_variable.targets)):
                if old_target.id==rig:
                    require(new_target.id==rig or new_target.id==reference,
                            'Reference copied driver self-ID has an undeclared replacement')
                    new_target.id=reference
                    expected_drivers[index]['variables'][variable_index]['targets'][target_index]['id']=qa.id_name(reference)
                    driver_redirects.append({'path':new.data_path,'variable':new_variable.name,'target_path':new_target.data_path})
    require(drivers_content(reference)==expected_drivers,'Reference native driver changed outside exact self-ID redirects')
    neutral_graph=copy.deepcopy(graph_content(reference))
    correction=diag.skirt_original_mode._corrections(source,record)
    controls_differences=[]
    for chain in record['chains']:
        for name in chain['def']:
            constraint=reference.pose.bones[name].constraints[0]
            require(constraint.type=='COPY_TRANSFORMS' and constraint.name=='Skirt manual pose',
                    'H0 neutral Controls exact manual constraint is missing')
            expected_mode='BEFORE_FULL' if name in correction['bones'] else 'REPLACE'
            require(constraint.mix_mode==expected_mode,'H0 copied correction contract differs')
            if name in correction['bones']:
                constraint.mix_mode='REPLACE'
                neutral_graph[name][0]['mix_mode']='REPLACE'
                controls_differences.append({'bone':name,'constraint':constraint.name,
                    'field':'mix_mode','before':'BEFORE_FULL','after':'REPLACE'})
    require(graph_content(reference)==neutral_graph,'H0 graph changed outside declared Controls mixing fields')
    for name in names:
        bone=reference.pose.bones[name]
        bone.location=(0.,0.,0.); bone.rotation_euler=(0.,0.,0.); bone.rotation_quaternion=(1.,0.,0.,0.)
        bone.rotation_axis_angle=(0.,0.,1.,0.); bone.scale=(1.,1.,1.)
    require(def_basis_content(reference,record)==original_DEF_basis,
            'Reference did not preserve current native DEF correction channels/basis exactly')
    # Shared custom mode/influence values remain copied; exact generated PHYS
    # constraints continue to read the same frozen QA tracker, not S/manual.
    physical_original,physical_reference=graph_content(rig),graph_content(reference)
    for chain in record['chains']:
        for name in chain['phys']:
            require(physical_reference[name]==physical_original[name], 'Reference PHYS target changed')
    reference.update_tag(); bpy.context.view_layer.update()
    report['reference_definition']={'rig':reference.name,'armature':reference.data.name,'wire_count':len(wires),
        'constraint_redirects':redirects,'driver_self_ID_redirects':driver_redirects,
        'manual_neutral_names':names,'fixedBasis_only':True,'uses_current_final_DEF_as_reference':False,
        'preserved_dormant_native_DEF_basis_sha256':qa.digest(original_DEF_basis),
        'declared_neutral_Controls_graph_differences':controls_differences,
        'historical_clear_channels_restored':False,
        'neutral_definition':'H0 excludes existing local correction through exact Controls REPLACE, keeps same physical/Body inputs'}
    return reference


def mesh_copy(source,name,owned,fixed_basis=False):
    obj=owned.object_copy(source,name); obj.data=source.data.copy(); owned.meshes.append(obj.data)
    require(obj.data!=source.data,'QA author/reference Mesh is shared with artist')
    require(obj.data.shape_keys is None or obj.data.shape_keys!=source.data.shape_keys,'QA Key data is shared with artist')
    require(qa.raw_mesh_content(obj)==qa.raw_mesh_content(source),'Native mesh/Keys/UV/weights copy identity failed')
    if obj.data.shape_keys:
        owned.keys.append((obj.data.shape_keys.name,obj.data.shape_keys.as_pointer()))
    clear_metadata(obj)
    if CORRECTIONS in source and not fixed_basis:
        obj[CORRECTIONS]=source[CORRECTIONS]
    require(obj.get(CORRECTIONS)==(None if fixed_basis else source.get(CORRECTIONS)),
            'QA author correction record or H0 neutral metadata differs')
    if fixed_basis:
        basis=[point.co.copy() for point in source.data.shape_keys.reference_key.data] if source.data.shape_keys else [v.co.copy() for v in source.data.vertices]
        obj.shape_key_clear()
        for vertex,position in zip(obj.data.vertices,basis):
            vertex.co=position
        require(obj.data.shape_keys is None,'H must be fixed Basis, without live author Key values')
    return obj


def raw_probe(source,name,owned):
    probe=owned.object_copy(source,name); clear_metadata(probe)
    require([modifier.type for modifier in probe.modifiers] in (['ARMATURE','SUBSURF'],['ARMATURE','NODES','SUBSURF']),
            'Raw native probe stack is not the declared source/overlay stack')
    probe.modifiers.remove(probe.modifiers[-1])
    probe.modifiers[0].is_active=True
    if len(probe.modifiers)>1:
        probe.modifiers[1].is_active=False
    return probe


def make_group(carrier,reference,owned):
    group=bpy.data.node_groups.new('QA Native Manual Key Cloth Delta Overlay','GeometryNodeTree'); owned.groups.append(group)
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    for name,kind in NODES.items():
        node=group.nodes.new(kind); node.name=name; node.mute=False
    group.nodes['Output'].is_active_output=True
    for name,target in (('Cloth',carrier),('Reference',reference)):
        node=group.nodes[name]; node.transform_space='RELATIVE'
        node.inputs['Object'].default_value=target; node.inputs['As Instance'].default_value=False
    for name in ('Cloth Index','Reference Index'):
        node=group.nodes[name]; node.data_type='FLOAT_VECTOR'; node.domain='POINT'; node.clamp=False
    group.nodes['Difference'].operation='SUBTRACT'; group.nodes['Overlay'].operation='ADD'
    group.nodes['Set Position'].inputs['Selection'].default_value=True
    group.nodes['Set Position'].inputs['Offset'].default_value=(0.,0.,0.)
    links=[('Input','Geometry','Set Position','Geometry'),('Cloth','Geometry','Cloth Index','Geometry'),
        ('Reference','Geometry','Reference Index','Geometry'),('Position','Position','Cloth Index','Value'),
        ('Position','Position','Reference Index','Value'),('Index','Index','Cloth Index','Index'),
        ('Index','Index','Reference Index','Index'),('Cloth Index','Value','Difference',0),
        ('Reference Index','Value','Difference',1),('Position','Position','Overlay',0),
        ('Difference','Vector','Overlay',1),('Overlay','Vector','Set Position','Position'),
        ('Set Position','Geometry','Output','Geometry')]
    for source,output,target,input_socket in links:
        group.links.new(group.nodes[source].outputs[output],group.nodes[target].inputs[input_socket])
    require(len(group.nodes)==11 and len(group.links)==13 and all(link.is_valid for link in group.links),
            'Declared native exact-index overlay graph was not constructed')
    return group


def error(left,right,meters):
    require(len(left)==len(right),'Exact raw index correspondence changed')
    return max((Vector(a)-Vector(b)).length*meters for a,b in zip(left,right))


def point_delta(after,before):
    return [a-b for a,b in zip(after,before)]


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]); args.output=args.output.resolve()
    require(bpy.app.background and '--factory-startup' in sys.argv and '--disable-autoexec' in sys.argv
            and '--disable-depsgraph-on-file-load' in sys.argv
            and not bpy.data.filepath,'Factory empty background only')
    require(args.output.is_relative_to(HERE) and args.output!=HERE and not args.output.exists(),'Fresh isolated output only')
    require(hashlib.sha256(capture.EVIDENCE.read_bytes()).hexdigest()==capture.EVIDENCE_SHA,'Frozen f4 evidence changed')
    evidence=json.loads(capture.EVIDENCE.read_text('utf-8')); sealed=Path(evidence['saved_candidate']).resolve()
    require(sealed.is_relative_to(HERE) and sealed.name.startswith('Cosha_Dress_QA_')
            and qa.file_state(sealed)==evidence['candidate_file'],'Refuse artist or changed sealed input')
    artist=HERE.parents[1]/'X.blend'; artist_before=qa.file_state(artist); code_before=diag.source_manifest()
    args.output.mkdir(); owned=Owned(); flags=[]; saved_frame=None; protection=None; rig=None
    report={'status':'starting','artist_operation':False,'scene_saved':False,'cloth_replayed':False,
        'production_effect_accepted':False,'manual_Keys_Original_modes_export_workflow_accepted':False,
        'existing_correction_production_workflow_accepted':False,
        'test_scope':'Existing local correction and additional manual/Key deltas relative to independent neutral Controls H0',
        'formula':'O = S + (C - H0), native relative exact-index vector fields before original Subsurf',
        'frames':[],'errors':[],'dependency_sha256':DEPENDENCIES,'frozen_evidence_sha256':capture.EVIDENCE_SHA,
        'required_file_load_flag':'--disable-depsgraph-on-file-load',
        'file_load_depsgraph_disable_requested':True,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':['Four recorded Cloth snapshots; no new solver, 60-frame replay, bake, mode lifecycle or export.',
            'Manual and asymmetric Key tests are isolated QA inputs, not existing production animation preservation.',
            'C is frozen waist-only Armature/body-attachment Cloth, without current32 DEF corrections. H0 uses independent Controls REPLACE so S-H0 carries the old correction.',
            'Old corrections and new manual/Key deltas can cause new contacts: collisions are measured, not accepted as a released workflow.',
            'Neutral Wire stored shape is the validated saved fixture; long-term edited Wire baseline migration is not proved.',
            'Native field/layer/constraint evidence must pass; no nearest fallback or current DEF neutral guess.']}
    source_hash=None; graph_before=None; drivers_before=None; channels_before=None
    try:
        diag.character_designer.register()
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(sealed),load_ui=False),'Sealed QA open failed')
        record=evidence['frozen_record']; source,rig=bpy.data.objects[record['source']],bpy.data.objects[record['rig']]
        require(skirt.read_record(source)==record,'Authoritative generated record differs')
        saved_frame=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
        protection=qa.Protection(); source_hash=direct.source_signature(source)
        graph_before=graph_content(rig); drivers_before=drivers_content(rig)
        channels_before={bone.name:diag.channels(bone) for bone in rig.pose.bones}
        for obj in (bpy.data.objects[evidence['actual_cloth']['object']],bpy.data.objects[record['physics']['proxy']]):
            for modifier in obj.modifiers:
                if modifier.type=='CLOTH':
                    flags.append((modifier,modifier.show_viewport,modifier.show_render))
                    modifier.show_viewport=modifier.show_render=False
        require(flags,'Expected exact owned Cloth inputs')
        names=neutral_preflight(source,rig,record,report)
        reference_rig=clone_reference(rig,source,record,names,owned,report)
        author=mesh_copy(source,'QA Overlay Author S',owned)
        reference=mesh_copy(source,'QA Fixed Basis Physical H',owned,fixed_basis=True)
        reference.modifiers[0].object=reference_rig
        if reference.parent==rig:
            reference.parent=reference_rig
        reference.modifiers.remove(reference.modifiers[-1]); reference.modifiers[0].is_active=True
        author_raw=raw_probe(author,'QA Raw Author S800',owned)
        carrier_mesh=bpy.data.meshes.new('QA Frozen Indexed Cloth800 Mesh'); owned.meshes.append(carrier_mesh)
        carrier_mesh.from_pydata([tuple(vertex.co) for vertex in source.data.vertices],[],[])
        carrier=bpy.data.objects.new('QA Frozen Indexed Cloth C',carrier_mesh); owned.objects.append(carrier)
        bpy.context.scene.collection.objects.link(carrier); clear_metadata(carrier)
        group=make_group(carrier,reference,owned)
        output=owned.object_copy(author,'QA Native Delta Overlay Output'); clear_metadata(output)
        copied_modifiers=[strict(modifier) for modifier in author.modifiers]
        modifier=output.modifiers.new('QA Native Exact Index Cloth Delta','NODES'); modifier.node_group=group
        output.modifiers.move(2,1)
        for index,saved in ((0,copied_modifiers[0]),(2,copied_modifiers[1])):
            output.modifiers[index].is_active=saved['is_active']
        modifier.is_active=False
        output_raw=raw_probe(output,'QA Raw Delta Overlay800',owned)
        expected_nodes=qa.digest(direct.node_contract(group))
        reference_graph=graph_content(reference_rig); reference_drivers=drivers_content(reference_rig)
        reference_rest=qa.rest_content(reference_rig)
        reference_DEF_basis=def_basis_content(reference_rig,record)
        correction_raw=source.get(CORRECTIONS)
        # Full evaluated curve positions change with Body input. Stored curve
        # data and exact Hook RNA are checked separately, not frozen to frame60.
        wire_storage={obj.name:curve_storage(obj)
            for obj in owned.objects if obj.type=='CURVE'}
        body=bpy.data.objects[evidence['body_clone']['original']]; meters=bpy.context.scene.unit_settings.scale_length
        fixed=[vertex.index for vertex in source.data.vertices if any(entry.group==source.vertex_groups[record['controls']['waist']].index
            and entry.weight==1. for entry in vertex.groups)]; free=[index for index in range(800) if index not in set(fixed)]
        require(len(fixed)==80 and len(free)==720,'Native source fixed/free index scope differs')

        def read_outputs():
            rig.update_tag(); reference_rig.update_tag(); bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get()
            snapshots={name:diag.mesh_snapshot(obj,graph) for name,obj in (
                ('S',author_raw),('H',reference),('O',output_raw),('Sfinal',author),('Ofinal',output))}
            require(all(len(snapshots[name]['points'])==800 for name in ('S','H','O'))
                    and all(len(snapshots[name]['points'])==3040 for name in ('Sfinal','Ofinal')),
                    'Native layer counts/indices changed')
            require(qa.digest(direct.node_contract(group))==expected_nodes,'Native overlay graph/defaults changed')
            require(graph_content(reference_rig)==reference_graph and drivers_content(reference_rig)==reference_drivers
                    and qa.rest_content(reference_rig)==reference_rest,'Independent physical reference graph/Rest changed')
            require(def_basis_content(reference_rig,record)==reference_DEF_basis
                    and reference.get(CORRECTIONS) is None and author.get(CORRECTIONS)==correction_raw,
                    'Independent H0/dormant DEF basis or exact author correction metadata changed')
            require([strict(output.modifiers[index]) for index in (0,2)]==copied_modifiers,
                    'Overlay changed copied native Armature/Subsurf RNA')
            source_matrix=source.evaluated_get(graph).matrix_world
            for obj in (author,author_raw,output,output_raw,reference,carrier):
                require(max(abs(a-b) for ar,br in zip(source_matrix,obj.evaluated_get(graph).matrix_world)
                    for a,b in zip(ar,br))<1.e-6,'Native relative overlay object chart drifted: '+obj.name)
            for obj in owned.objects:
                if obj.type=='CURVE':
                    require(curve_storage(obj)==wire_storage[obj.name],'Independent neutral Wire stored data/Hook changed')
            require(direct.source_signature(source)==source_hash and graph_content(rig)==graph_before,
                    'Overlay changed original source/Rig graph')
            require(direct.mesh_layers(author,graph)==direct.mesh_layers(output,graph),
                    'Native overlay lost original final topology/UV/weights/nonposition layers')
            return snapshots,graph

        for frozen in evidence['frames']:
            frame=frozen['frame']; require(frame in (1,7,25,30),'Unexpected frozen measurement frame')
            bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get(); source_world=source.evaluated_get(graph).matrix_world.copy()
            carrier.matrix_world=source_world
            inverse=source_world.inverted()
            require(len(frozen['physical_world'])==800,'Frozen raw Cloth index target count differs')
            for vertex,point in zip(carrier.data.vertices,frozen['physical_world']):
                vertex.co=inverse@Vector(point)
            carrier.data.update(); carrier.update_tag()
            snapshots,graph=read_outputs()
            neutral_error=error(snapshots['S']['points'],snapshots['H']['points'],meters)
            cloth_error=error(snapshots['O']['points'],frozen['physical_world'],meters)
            correction_delta_error=error(point_delta(snapshots['O']['points'],[Vector(p) for p in frozen['physical_world']]),
                                         point_delta(snapshots['S']['points'],snapshots['H']['points']),meters)
            require(correction_delta_error<=LIMIT_METRES,
                    'Native O-C differs from S-H0 beyond2um; existing correction transfer is not accepted')
            has_correction=bool(report['existing_DEF_correction']['corrected_bone_names'])
            if not has_correction:
                require(neutral_error<=LIMIT_METRES and cloth_error<=LIMIT_METRES,
                        'No-correction S/H0 or native O/frozen C exceeds2um')
            body_mesh=diag.mesh_snapshot(body,graph); bounds=diag.framing(rig,record,graph)
            witnesses=frozen['evaluated_body_triangle_evidence']['vertices']
            require(len(witnesses)==14,'Exact frozen evaluated Body14 witness scope changed')
            body_error=max((body_mesh['points'][witness['evaluated_vertex_index']]-Vector(witness['world'])).length*meters
                for witness in witnesses)
            require(body_error<5.e-6,'Original Body input differs from sealed f4 Body14 witnesses beyond 5um')
            epsilon=max(1.e-8,record['fit']['height_world']*1.e-6)
            snapshots['O']['free_indices']=free
            snapshots['Ofinal']['free_indices']=direct.base.free_indices(snapshots['Ofinal'],source.vertex_groups[record['controls']['waist']])
            item={'frame':frame,'S_H0_existing_correction_max_m':neutral_error,'O_C_existing_correction_max_m':cloth_error,
                'existing_correction_delta_preservation_error_m':correction_delta_error,
                'no_correction_neutral_S_H0_and_O_C_required':not has_correction,
                'body_14_witness_max_delta_m':body_error,
                'raw800_body_crossings':diag.triangle_crossings(snapshots['O'],body_mesh,bounds,2000,epsilon),
                'final3040_body_crossings':diag.triangle_crossings(snapshots['Ofinal'],body_mesh,bounds,2000,epsilon),
                'S800_world':[diag.vector(p) for p in snapshots['S']['points']],
                'H800_world':[diag.vector(p) for p in snapshots['H']['points']],
                'O800_world':[diag.vector(p) for p in snapshots['O']['points']]}
            report['frames'].append(item)
            if frame==25:
                baseline=snapshots
                bone=rig.pose.bones[record['controls']['hem']]; saved=diag.channels(bone)
                require(bone.rotation_mode=='XYZ','QA manual input requires generated XYZ master')
                try:
                    bone.rotation_euler.x+=0.14
                    after,_=read_outputs()
                    delta_error=error(point_delta(after['O']['points'],baseline['O']['points']),
                                      point_delta(after['S']['points'],baseline['S']['points']),meters)
                    final_delta_error=error(point_delta(after['Ofinal']['points'],baseline['Ofinal']['points']),
                                            point_delta(after['Sfinal']['points'],baseline['Sfinal']['points']),meters)
                    h_error=error(after['H']['points'],baseline['H']['points'],meters)
                    visible=error(after['O']['points'],baseline['O']['points'],meters)
                    require(delta_error<=LIMIT_METRES and final_delta_error<=LIMIT_METRES and h_error<=LIMIT_METRES
                            and visible>1.e-4,'Manual response/independent H proof failed')
                    item['manual_test']={'bone':bone.name,'rotate_X_rad':0.14,'raw_delta_error_m':delta_error,
                        'final_delta_error_m':final_delta_error,'H_changed_max_m':h_error,'visible_output_max_m':visible}
                finally:
                    for key,values in saved.items():
                        if key!='custom':
                            setattr(bone,key,values)
                    rig.update_tag(); bpy.context.view_layer.update()
                restored,_=read_outputs()
                require(error(restored['O']['points'],baseline['O']['points'],meters)<=LIMIT_METRES,'Manual restore jumped')
                if author.data.shape_keys is None:
                    author.shape_key_add(name='Basis',from_mix=False)
                    owned.keys.append((author.data.shape_keys.name,author.data.shape_keys.as_pointer()))
                key=author.shape_key_add(name='QA Asymmetric Local Shape',from_mix=False)
                basis=author.data.shape_keys.reference_key
                selected=[index for index in record['fit']['rings'][6] if basis.data[index].co.x>0.]
                require(selected and len(selected)<80,'Asymmetric QA region was not defined')
                for index in selected:
                    key.data[index].co.z+=0.008
                key.relative_key=basis; key.value=0.
                key_baseline,_=read_outputs()
                require(error(key_baseline['O']['points'],baseline['O']['points'],meters)<=LIMIT_METRES,
                        'Independent zero-valued QA Key altered neutral input')
                try:
                    key.value=0.75; author.data.update()
                    after,_=read_outputs()
                    delta_error=error(point_delta(after['O']['points'],key_baseline['O']['points']),
                                      point_delta(after['S']['points'],key_baseline['S']['points']),meters)
                    final_delta_error=error(point_delta(after['Ofinal']['points'],key_baseline['Ofinal']['points']),
                                            point_delta(after['Sfinal']['points'],key_baseline['Sfinal']['points']),meters)
                    h_error=error(after['H']['points'],key_baseline['H']['points'],meters)
                    visible=error(after['O']['points'],key_baseline['O']['points'],meters)
                    require(delta_error<=LIMIT_METRES and final_delta_error<=LIMIT_METRES and h_error<=LIMIT_METRES
                            and visible>1.e-4,'Asymmetric Key response/independent H proof failed')
                    item['shape_test']={'key':key.name,'raw_indices':selected,'local_Z_delta':0.008,'value':0.75,
                        'raw_delta_error_m':delta_error,'final_delta_error_m':final_delta_error,
                        'H_changed_max_m':h_error,'visible_output_max_m':visible,'artist_Keys_changed':False}
                finally:
                    key.value=0.; author.data.update(); bpy.context.view_layer.update()
        require({item['frame'] for item in report['frames']}=={1,7,25,30},'Four-frame proof incomplete')
        if report['existing_DEF_correction']['corrected_bone_names']:
            require(max(item['S_H0_existing_correction_max_m'] for item in report['frames'])>LIMIT_METRES,
                    'Existing correction produced no measurable visual delta; its preservation proof is inconclusive')
        report['existing_correction_visual_delta_proved_in_isolated_QA']=bool(report['existing_DEF_correction']['corrected_bone_names'])
        report['node_graph']=direct.node_contract(group)
        report['status']='passed_isolated_overlay'
    except BaseException:
        report['status']='failed'; report['errors'].append(traceback.format_exc())
    finally:
        try:
            owned.cleanup(report)
            if saved_frame is not None:
                try:
                    if flags:
                        bpy.context.scene.frame_set(saved_frame[0],subframe=saved_frame[1]); bpy.context.view_layer.update()
                    require(graph_content(rig)==graph_before and drivers_content(rig)==drivers_before,'Original native graph/driver rollback differs')
                    require({bone.name:diag.channels(bone) for bone in rig.pose.bones}==channels_before,'Original pose input rollback differs')
                    require(direct.source_signature(source)==source_hash,'Original source/Keys/UV/weights rollback differs')
                    report['protected_after']=protection.verify()
                    require(report['protected_after']['success'],'Original asset/Rest/Action protection failed')
                except BaseException:
                    report['errors'].append('Original state restore/protection: '+traceback.format_exc())
        finally:
            for modifier,viewport,render in flags:
                try:
                    modifier.show_viewport,modifier.show_render=viewport,render
                except BaseException:
                    report['errors'].append('Cloth flags restore: '+traceback.format_exc())
        report['artist_disk_exact']=qa.file_state(artist)==artist_before
        report['code_exact']=diag.source_manifest()==code_before
        report['sealed_input_exact']=qa.file_state(sealed)==evidence['candidate_file']
        if report['errors'] or not all(report[key] for key in ('artist_disk_exact','code_exact','sealed_input_exact')):
            report['status']='failed'
        (args.output/'prototype_native_dress_overlay.json').write_text(json.dumps(diag.json_content(report),ensure_ascii=False,
            indent=2,allow_nan=False),'utf-8')
    require(report['status']=='passed_isolated_overlay','Native isolated overlay failed; retained report is authoritative')


if __name__=='__main__':
    main()
