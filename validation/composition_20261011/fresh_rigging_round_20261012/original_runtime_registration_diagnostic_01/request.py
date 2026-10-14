import bpy,sys,os,json,hashlib,traceback
from pathlib import Path
assert os.getpid()==14500 and Path(bpy.data.filepath).resolve()==Path(r'D:/Blender/Projects/Character/X/X.blend').resolve()
mods={}
for n,m in list(sys.modules.items()):
 if n=='character_designer' or n.startswith('character_designer.'):
  mods[n]={'path':getattr(m,'__file__',None),'enabled':getattr(m,'__addon_enabled__',None),'version':getattr(m,'bl_info',{}).get('version')}
classes=[]
for n in dir(bpy.types):
 try:
  cls=getattr(bpy.types,n)
  mod=getattr(cls,'__module__','')
  if isinstance(mod,str) and ('character_designer' in mod): classes.append({'name':n,'module':mod,'registered':bool(getattr(cls,'is_registered',False))})
 except Exception:pass
report={'pid':os.getpid(),'filepath':bpy.data.filepath,'dirty':bpy.data.is_dirty,'modules':mods,'registered_classes':classes,'scene_cd_properties':[p.identifier for p in bpy.types.Scene.bl_rna.properties if 'character_designer' in p.identifier],'wm_cd_properties':[p.identifier for p in bpy.types.WindowManager.bl_rna.properties if 'character_designer' in p.identifier],'sys_path':sys.path,'script_execution_no_register_or_scene_writes':True}
p=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_runtime_registration_diagnostic_01/report.json')
with p.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'report':str(p),'module_count':len(mods),'class_count':len(classes)}))
