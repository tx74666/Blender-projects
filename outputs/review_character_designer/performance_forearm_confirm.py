import bpy, sys, time, json, statistics
from pathlib import Path
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
path=r'D:\Blender\Projects\Character\X\outputs\rig\fixtures\X_forearm_ranges_0555_preview.blend'
bpy.ops.wm.open_mainfile(filepath=path,load_ui=False)
import character_designer
from character_designer import forearm_twist as ft
character_designer.register()
scene=bpy.context.scene
graph=bpy.context.evaluated_depsgraph_get()
counts={}
for name in ('_topology','_topology_digest','mirror_ring_pairs','corrected_vertex'):
    original=getattr(ft,name)
    def counted(*a,_fn=original,_name=name,**kw):
        counts[_name]=counts.get(_name,0)+1
        return _fn(*a,**kw)
    setattr(ft,name,counted)
def bench():
    for _ in range(3):ft.update_runtime(scene,graph)
    counts.clear()
    samples=[]
    for _ in range(7):
        start=time.perf_counter();ft.update_runtime(scene,graph);samples.append((time.perf_counter()-start)*1000)
    return {'samples_ms':samples,'median_ms':statistics.median(samples),'call_counts':dict(counts),'errors':dict(ft._ERRORS)}
report={'fixture':path,'blender':bpy.app.version_string,'warmup':3,'samples':7,'enabled':bench()}
for obj in scene.objects:
    if obj.type=='MESH' and ft.RECORD_KEY in obj:
        records=ft._records(obj)
        for r in records.values():r['enabled']=False
        ft._write_records(obj,records)
report['disabled']=bench()
out=Path(r'D:\Blender\Projects\Character\X\outputs\review_character_designer\performance_forearm_after.json')
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
