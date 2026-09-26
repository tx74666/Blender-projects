import bpy
import json
from datetime import datetime
from pathlib import Path

areas=[a for a in bpy.context.screen.areas if a.type=='VIEW_3D']
assert len(areas)==2, 'Layout changed; leave it untouched.'
small=min(areas,key=lambda a:a.width*a.height)
large=max(areas,key=lambda a:a.width*a.height)
assert small.spaces.active.shading.type=='MATERIAL'
assert large.spaces.active.shading.type=='MATERIAL'
before=[{'x':a.x,'y':a.y,'width':a.width,'height':a.height,'shading':a.spaces.active.shading.type} for a in areas]
small.spaces.active.shading.type='SOLID'
report={'time':datetime.now().isoformat(),'before':before,
        'after':[{'x':a.x,'y':a.y,'width':a.width,'height':a.height,'shading':a.spaces.active.shading.type} for a in areas],
        'scene_saved':False,'undo_changed':False}
(Path(r'D:\Blender\Projects\Character\X\outputs\memory_health')/'secondary_view_optimization.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Secondary bone view: SOLID; main view retains MATERIAL. Render and scene data unchanged.')
