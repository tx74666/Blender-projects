import bpy, json, traceback
from pathlib import Path
from unittest.mock import patch
from mathutils import Vector
import character_designer
from character_designer import finger_loop_marks as marks, finger_chain as chain
from character_designer import finger_bank as bank, finger_targets as targets
from character_designer import finger_internal as internal, mesh_mirror

def main():
    area = bpy.context.area
    obj = bank.active_object(bpy.context)
    rig = bpy.context.scene.character_designer_setup.rig
    before = mesh_mirror._fingerprint(obj)
    bones_before = [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
    result = dict(version=character_designer.bl_info['version'], object=obj.name,
                  active=obj.character_designer_finger_bank.active, mode=bpy.context.mode)
    def inspect(obj, rig, reference, nodes, bm):
        body = reference['body']
        volume = internal.Volume(bm, body)
        to_mesh = obj.matrix_world.inverted() @ rig.matrix_world
        points = [to_mesh @ Vector(p) for p in nodes]
        margin = max(body['length']*1e-6, min(body['radius']*.02, body['length']*.001))
        result.update(body=body, basis=reference['basis'], points=[list(p) for p in points], margin=margin,
                      mesh_vertices=[list(v.co) for v in bm.verts],
                      mesh_faces=[[v.index for v in f.verts] for f in bm.faces],
                      hint=marks._reference(obj, result['active'], None),
                      records=marks.records(obj, result['active']))
        result['segments'] = []
        for a,b in zip(points,points[1:]):
            samples=[]
            for i in range(21):
                p=a.lerp(b,i/20)
                samples.append(dict(t=i/20,inside=volume.inside(p),distance=volume.distance(p)))
            result['segments'].append(dict(certified=volume.certify((a,b),margin*.5),samples=samples))
    def no_write(context, plan):
        result['bone_names'] = plan['chains'][0]['names']
        from character_designer.finger_bones import _head, _tail
        source = targets.resolve(obj, rig, result['active'], targets.index(rig), live_mark_reference=result)
        result['original_nodes'] = [list(obj.matrix_world.inverted() @ rig.matrix_world @ p) for p in chain._nodes(source)]
        return dict(chains=1,keys=plan['keys'],changed=0)
    try:
        with patch.object(marks,'_certify',side_effect=inspect), patch.object(chain,'_run',side_effect=no_write):
            marks.align(bpy.context)
    except Exception:
        result['error']=traceback.format_exc()
    finally:
        result['unchanged'] = before==mesh_mirror._fingerprint(obj) and bones_before==[(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
        Path('D:/Blender/Projects/Character/X/outputs/mark_alignment_diagnostic_20260922.json').write_text(json.dumps(result),encoding='utf-8')
        area.type='VIEW_3D'
main()
