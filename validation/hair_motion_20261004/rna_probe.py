import os, sys, importlib.util, json
from pathlib import Path
import bpy
root=Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path.insert(0,str(root/'addons'))
sys.path.insert(0,str(root/'tests'))
from test_hair_wiggle_adapter_blender import real_backend, fixture
backend=real_backend()
source,rig,registry,profiles=fixture()
head=rig.pose.bones['Head']
for label,owner in [('head',head),('rig',rig),('scene',bpy.context.scene)]:
    group=owner.wiggle
    print('RNA_PROBE',label,'before',list(owner.keys()),list(group.keys()))
head.wiggle.tail=True
head.wiggle.stiff=123.5
head.wiggle.velocity=(.1,.2,.3)
for label,owner in [('head',head),('rig',rig),('scene',bpy.context.scene)]:
    print('RNA_PROBE',label,'after',list(owner.keys()),repr(owner.get('wiggle')),list(owner.wiggle.keys()),owner.is_property_set('wiggle'))
print('ACTUAL',head.wiggle.tail,head.wiggle.stiff,tuple(head.wiggle.velocity))
backend['module'].unregister()
