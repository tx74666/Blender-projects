import bpy, sys, time, json, statistics, cProfile, pstats, io
from pathlib import Path
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
input_path = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else r'D:\Blender\Projects\Character\X\X.blend'
bpy.ops.wm.open_mainfile(filepath=input_path, load_ui=False)
import character_designer
from character_designer import forearm_twist as ft
from character_designer import bone_display_sync as display

report = {'blender': bpy.app.version_string, 'input': input_path, 'scene_objects': len(bpy.context.scene.objects), 'meshes': []}
def timed(fn, n=9):
    samples=[]
    for _ in range(n):
        start=time.perf_counter(); fn(); samples.append((time.perf_counter()-start)*1000)
    return {'median_ms': statistics.median(samples), 'min_ms': min(samples), 'max_ms':max(samples)}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH': continue
    report['meshes'].append({'name':obj.name, 'vertices':len(obj.data.vertices),'edges':len(obj.data.edges),
      'faces':len(obj.data.polygons),'keys':len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0,
      'forearm_records':list(ft._records(obj))})
    if len(obj.data.vertices)>1000:
        report['meshes'][-1]['topology_hash']=timed(lambda:ft._topology(obj.data))
character_designer.register()
graph=bpy.context.evaluated_depsgraph_get()
report['errors']=dict(ft._ERRORS)
report['registered_idle_runtime']=timed(lambda:ft.update_runtime(bpy.context.scene,graph),7)
report['display_sync_idle']=timed(display.sync_pending,9)
prof=cProfile.Profile(); prof.enable()
for _ in range(5): ft.update_runtime(bpy.context.scene,graph)
prof.disable(); s=io.StringIO(); pstats.Stats(prof,stream=s).sort_stats('cumtime').print_stats(25)
report['forearm_profile']=s.getvalue()
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and ft.RECORD_KEY in obj:
        records=ft._records(obj)
        for record in records.values():record['enabled']=False
        ft._write_records(obj,records)
ft.update_runtime(bpy.context.scene,graph)
report['all_disabled_runtime']=timed(lambda:ft.update_runtime(bpy.context.scene,graph),7)
report['disabled_errors']=dict(ft._ERRORS)
out=Path(r'D:\Blender\Projects\Character\X\outputs\review_character_designer')/('performance_'+Path(input_path).stem+'.json')
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
