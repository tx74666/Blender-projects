import bpy,sys,os,json,types
from pathlib import Path
assert os.getpid()==14500 and Path(bpy.data.filepath).resolve()==Path(r'D:/Blender/Projects/Character/X/X.blend').resolve()
fn=bpy.types.CHARACTERDESIGNER_PT_main.draw
g=fn.__globals__
mods=[]
for key,value in g.items():
 if isinstance(value,types.ModuleType) and (getattr(value,'__name__','').startswith('character_designer')):
  mods.append({'key':key,'name':value.__name__,'file':getattr(value,'__file__',None),'same_as_sys':sys.modules.get(value.__name__) is value})
classes=[{'name':c.__name__,'registered':bool(getattr(c,'is_registered',False)),'actual_same':getattr(bpy.types,c.__name__,None) is c,'module':c.__module__} for c in g.get('CLASSES',())]
functions={name:{'module':getattr(g.get(name),'__module__',None),'code_file':getattr(getattr(g.get(name),'__code__',None),'co_filename',None),'globals_file':getattr(g.get(name),'__globals__',{}).get('__file__')} for name in ('register','unregister','register_rigging_runtime','register_composition_runtime','unregister_rigging_runtime')}
r={'root_namespace_file':g.get('__file__'),'root_namespace_name':g.get('__name__'),'root_version':g.get('bl_info',{}).get('version'),'enabled':g.get('__addon_enabled__'),'classes':classes,'root_modules':mods,'functions':functions,'dirty':bpy.data.is_dirty,'datafilepath':bpy.data.filepath,'read_only':True}
with Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_runtime_registration_globals_01/report.json').open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
print(json.dumps({'root_version':r['root_version'],'class_count':len(classes)}))
