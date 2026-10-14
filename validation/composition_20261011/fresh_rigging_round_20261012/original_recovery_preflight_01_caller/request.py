import bpy,sys,json,os
from pathlib import Path
assert os.getpid()==14500 and bpy.data.filepath==r'D:\Blender\Projects\Character\X\X.blend'
o=sys.modules['x_original_registration_recovery_07736'].observed_namespace
g=o['root_globals']
assert bpy.types.CHARACTERDESIGNER_PT_main.draw.__globals__ is g
sk=g['skirt_wiggle']
result={'pid':os.getpid(),'dirty':bool(bpy.data.is_dirty),'skirt_registered':sk._REGISTERED,'skirt_sessions_count':len(sk._SESSIONS),'skirt_state_key':sk.STATE_KEY,'objects_with_skirt_state':[{'name':v.name,'pointer':v.as_pointer(),'state':o['plain'](v[sk.STATE_KEY])} for v in bpy.data.objects if sk.STATE_KEY in v],'read_only':True,'Scene_or_runtime_registration_mutated':False}
p=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_recovery_preflight_01.json')
with p.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
