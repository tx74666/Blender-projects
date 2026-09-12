"""Preserve the current unsaved work before widget collection organization."""
import bpy,json
from pathlib import Path
from datetime import datetime
OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
assert bpy.data.filepath==r'D:\Blender\Projects\Character\X\X.blend'
assert bpy.context.mode in {'OBJECT','POSE','EDIT_MESH'}
path=OUT/'backups'/('X_before_widgets_0543_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
assert bpy.ops.wm.save_as_mainfile(filepath=str(path),copy=True)=={'FINISHED'}
report={'filepath':bpy.data.filepath,'backup':str(path),'mode':bpy.context.mode,
 'active':bpy.context.object.name if bpy.context.object else None,
 'collections':[{'name':c.name,'props':{k:str(v) for k,v in c.items()},'objects':list(c.objects.keys()),
 'children':list(c.children.keys()),'users':c.users,'parents':[p.name for p in bpy.data.collections if c.name in p.children],
 'scenes':[s.name for s in bpy.data.scenes if c.name in s.collection.children]} for c in bpy.data.collections if 'widget' in c.name.lower()]}
(OUT/'widgets_0543_live_input.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if bpy.context.area.type=='CONSOLE':bpy.context.area.type='VIEW_3D'
print('WIDGET_INPUT_SAVED',str(path))
