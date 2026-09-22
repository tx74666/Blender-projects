import bpy, json, traceback
from pathlib import Path
from character_designer import mesh_mirror as mirror

C = bpy.context
area = C.area
obj = C.edit_object
report = {'object': obj.name}
staging = new = None
before = None
try:
    settings = C.scene.character_designer_mesh_mirror
    plan = mirror.build_plan(C, settings.reference, settings.tolerance)
    report['plan'] = dict(source_faces=len(plan.source_faces), target_faces=len(plan.target_faces),
                          seams=len(plan.seams), needs_choice=plan.needs_choice, kind=plan.region_kind,
                          reference=settings.reference.name if settings.reference else None)
    bpy.ops.object.mode_set(mode='OBJECT')
    before = mirror._fingerprint(obj)
    bpy.data.libraries.write(r'D:\Blender\Projects\Character\X\outputs\mirror_normals_source_20260921.blend',
                            {obj} | ({settings.reference} if settings.reference else set()))
    old = obj.data
    report['source'] = dict(vertices=len(old.vertices), faces=len(old.polygons),
        normals=len(old.corner_normals), keys=len(old.shape_keys.key_blocks) if old.shape_keys else 0,
        sharp_edges=sum(e.use_edge_sharp for e in old.edges))
    new, origins, selection, mapping = mirror._rebuild(plan)
    matrix = plan.reflection.to_3x3().inverted().transposed()
    def inspect():
        errors=[]
        for i, (reflected, source) in enumerate(mapping['CORNER']):
            wanted=old.corner_normals[source].vector.copy()
            if reflected: wanted=(matrix @ wanted).normalized()
            actual=new.corner_normals[i].vector.copy()
            error=(wanted-actual).length
            if error > .001:
                errors.append(dict(corner=i, source=source, reflected=reflected, error=error,
                    vertex=new.loops[i].vertex_index, source_vertex=old.loops[source].vertex_index,
                    wanted=list(wanted), actual=list(actual)))
        return dict(count=len(errors), max_error=max((e['error'] for e in errors), default=0),
                    reflected=sum(e['reflected'] for e in errors), worst=sorted(errors,key=lambda e:-e['error'])[:12])
    report['rebuilt']=inspect()
    staging=bpy.data.objects.new('.NormalDiagnostic',new)
    mirror._populate_shapes(staging, old, plan, origins)
    report['with_shapes']=inspect()
except Exception as exc:
    report['error']=str(exc); report['traceback']=traceback.format_exc()
finally:
    if staging: bpy.data.objects.remove(staging)
    if new and new.users==0: bpy.data.meshes.remove(new)
    if before: report['unchanged']=mirror._fingerprint(obj)==before
    if obj.mode=='OBJECT': bpy.ops.object.mode_set(mode='EDIT')
    Path(r'D:\Blender\Projects\Character\X\outputs\mirror_normals_inspect_20260921.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    area.type='VIEW_3D'
