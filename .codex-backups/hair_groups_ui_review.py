import sys
import json
from pathlib import Path
import bpy

ROOT=Path(r'D:/Blender/Projects/Character/X')
sys.path.insert(0,str(ROOT/'addons'))
sys.path.insert(0,str(ROOT/'tests'))
import character_designer as addon
from character_designer import hair_bones as ui
from character_designer import hair_bones_groups as groups
from test_hair_bones_groups_blender import fixture

addon.register()
obj,plans,layers=fixture()
state=bpy.context.window_manager.character_designer_hair_bones
state.source=obj
records=groups.read_groups(obj)
state.active_group=records[1]['id']
print('ENUM_BEFORE',state.active_group,records[1]['id'])
data=json.loads(obj[groups.GROUPS_KEY])
data['groups'].reverse()
groups._write(obj,data)
print('ENUM_AFTER_REORDER',state.active_group,records[1]['id'])
state.active_group=records[0]['id']
data=json.loads(obj[groups.GROUPS_KEY]);data['groups'].reverse();groups._write(obj,data)
print('ENUM_AFTER_REORDER_DIFFERENT',state.active_group,records[0]['id'])
state.active_group=groups.read_groups(obj)[0]['id']
gid=state.active_group
guide=groups.create_group_guide(bpy.context,gid)
guide.hide_viewport=True
before_obj=bpy.context.active_object
try:
    print('EDIT_HIDDEN_GUIDE',bpy.ops.character_designer.hair_edit_guide())
except RuntimeError as exc:
    print('EDIT_HIDDEN_GUIDE_EXCEPTION',exc)
print('EDIT_HIDDEN_GUIDE_STATE',bpy.context.mode,bpy.context.active_object.name if bpy.context.active_object else None)

doc=bpy.props.EnumProperty.__doc__
print('ENUM_DOC',doc[doc.find('WARNING'):doc.find('WARNING')+550] if 'WARNING' in doc else doc[-1800:])
