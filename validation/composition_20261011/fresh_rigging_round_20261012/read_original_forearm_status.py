import bpy,json,os,sys
from pathlib import Path
assert os.getpid()==27676 and Path(bpy.data.filepath).resolve()==Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
package=sys.modules['character_designer']; assert tuple(package.bl_info['version'])==(0,77,24)
ft=sys.modules['character_designer.forearm_twist']; out=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_forearm_status_readonly_01")
assert out.is_dir() and not any(out.iterdir())
report={'pid':os.getpid(),'runtime':[0,77,24],'read_only':True,'scene':bpy.context.scene.name,'frame':bpy.context.scene.frame_current,'busy':bool(ft._BUSY),'errors':dict(ft._ERRORS),'active_calibration_preview':bool(ft._SESSION),'meshes':{}}
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and ft.RECORD_KEY in obj:
        records=ft._records(obj)
        report['meshes'][obj.name]={'preview_marker':ft.PREVIEW_KEY in obj,'targets':{side:r.get('target') for side,r in records.items()}}
with (out/'original_forearm_status.json').open('x',encoding='utf-8') as stream:stream.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'read_only':True,'report':str(out/'original_forearm_status.json'),'mesh_count':len(report['meshes'])}))
