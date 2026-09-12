"""Apply only the validated existing-wrist input-frame flags.

Caller creates a backup and handles saving/reloading. No rebuild, keyframe,
pose operation, selection change, or save occurs here. Works in Object/Pose.
"""
import bpy, hashlib, json, traceback
from array import array
from pathlib import Path
from character_designer import limb_ik, forearm_twist

OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
REPORT=OUT/'wrist_local_axes_0555_apply_result.json'


def coordinates(collection):
    values=array('f',[0.0])*(3*len(collection))
    collection.foreach_get('co',values)
    return values.tobytes()


def mesh_digest():
    digest=hashlib.sha256()
    for mesh in sorted(bpy.data.meshes,key=lambda m:m.name):
        digest.update(mesh.name.encode())
        digest.update(coordinates(mesh.vertices))
        digest.update(repr([tuple(e.vertices) for e in mesh.edges]).encode())
        digest.update(repr([tuple(p.vertices) for p in mesh.polygons]).encode())
        digest.update(repr([[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]).encode())
        if mesh.shape_keys:
            for key in mesh.shape_keys.key_blocks:
                digest.update(repr((key.name,key.value,key.mute,key.vertex_group,key.relative_key.name)).encode())
                digest.update(coordinates(key.data))
    return digest.hexdigest()


def bone_structure(rig):
    return [(b.name,b.parent.name if b.parent else None,b.use_connect,b.use_deform,
             b.bbone_segments,tuple(tuple(row) for row in b.matrix_local)) for b in rig.data.bones]


def animation_fingerprint(rig):
    data=rig.animation_data
    if data is None:return None
    action=data.action
    return (action.as_pointer() if action else None,
            tuple((fc.data_path,fc.array_index,fc.driver.type,fc.driver.expression,
                   tuple((v.name,v.type,tuple((t.id.as_pointer() if t.id else None,t.data_path) for t in v.targets)) for v in fc.driver.variables)) for fc in data.drivers),
            tuple((track.name,tuple((s.name,s.action.as_pointer() if s.action else None,s.frame_start,s.frame_end) for s in track.strips)) for track in data.nla_tracks),
            tuple((fc.data_path,fc.array_index,tuple((tuple(k.co),k.interpolation) for k in fc.keyframe_points)) for fc in limb_ik._fcurves_for_action(action)) if action else ())


def apply():
    assert bpy.context.mode in {'OBJECT','POSE'},'Finish the current mesh/armature edit first'
    assert not any('TRANSFORM_OT' in getattr(op,'bl_idname','') for op in getattr(bpy.context.window,'modal_operators',())), 'Finish the active transform first'
    assert Path(bpy.data.filepath).name=='X.blend','Expected the X scene'
    evidence=json.loads((OUT/'wrist_actual_matrix_0555.json').read_text(encoding='utf8'))
    assert evidence['ok'] and len(evidence['cases'])==160
    rig=bpy.data.objects['CoshaRig']
    flags={p.name:p.use_transform_at_custom_shape for p in rig.pose.bones}
    report=dict(ok=False,saved=False)
    busy=forearm_twist._BUSY
    forearm_twist._BUSY=True
    try:
        bpy.context.view_layer.update()
        shape_hash=mesh_digest()
        rest=bone_structure(rig)
        animation=animation_fingerprint(rig)
        constraints=[(p.name,c.as_pointer(),c.name,c.type,c.mute,c.influence) for p in rig.pose.bones for c in p.constraints]
        before={p.name:(p.matrix.copy(),p.matrix_basis.copy(),p.custom_shape,p.custom_shape_transform,
                        p.use_transform_around_custom_shape) for p in rig.pose.bones}
        report['changed']=limb_ik.sync_wrist_local_axes(rig)
        bpy.context.view_layer.update()
        assert limb_ik.sync_wrist_local_axes(rig)==[]
        assert shape_hash==mesh_digest(),'Mesh, shape keys, or weights changed'
        assert rest==bone_structure(rig),'Bone rest data or hierarchy changed'
        assert animation==animation_fingerprint(rig),'Animation identity or paths changed'
        assert constraints==[(p.name,c.as_pointer(),c.name,c.type,c.mute,c.influence) for p in rig.pose.bones for c in p.constraints]
        pose_error=0.0
        for p in rig.pose.bones:
            matrix,basis,shape,frame,around=before[p.name]
            pose_error=max(pose_error,max(abs(matrix[i][j]-p.matrix[i][j]) for i in range(4) for j in range(4)))
            assert basis==p.matrix_basis
            assert (shape,frame,around)==(p.custom_shape,p.custom_shape_transform,p.use_transform_around_custom_shape)
        assert pose_error<3e-5
        assert all(rig.pose.bones['CTRL_hand_IK.'+s].use_transform_at_custom_shape for s in 'LR')
        report.update(ok=True,pose_error=pose_error,mesh_weights_shapes_unchanged=True,
                      rest_hierarchy_unchanged=True,animation_unchanged=True)
        for screen in bpy.data.screens:
            for area in screen.areas:area.tag_redraw()
        return report
    except Exception as exc:
        for name,value in flags.items():
            if name in rig.pose.bones:rig.pose.bones[name].use_transform_at_custom_shape=value
        report.update(error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        forearm_twist._BUSY=busy
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
        print('WRIST_EXISTING_AXES_ONLY',json.dumps(report),flush=True)


if __name__=='__main__':
    apply()
