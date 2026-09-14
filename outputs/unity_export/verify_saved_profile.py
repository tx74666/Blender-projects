"""Read saved files and compare original authored geometry/rig after UI setup."""
import bpy
from pathlib import Path
import json
import hashlib
import sys

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
character_designer.register()
root = Path(r'D:\Blender\Projects\Character\X\outputs\unity_export')

def state():
    h = hashlib.sha256()
    def add(value): h.update(repr(value).encode('utf8'))
    for obj in sorted(bpy.data.objects, key=lambda item:item.name):
        add((obj.name,obj.type,obj.parent.name if obj.parent else None,obj.parent_type,obj.parent_bone))
        if obj.type == 'MESH':
            add([(tuple(v.co),[(g.group,g.weight) for g in v.groups]) for v in obj.data.vertices])
            add([tuple(p.vertices) for p in obj.data.polygons])
            add([(m.name,m.type,m.show_viewport) for m in obj.modifiers])
            if obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    add((key.name,key.relative_key.name,[tuple(v.co) for v in key.data]))
        if obj.type == 'ARMATURE':
            for bone in obj.data.bones:
                add((bone.name,bone.parent.name if bone.parent else None,list(map(tuple,bone.matrix_local)),bone.use_deform))
            for pb in obj.pose.bones:
                add((pb.name,list(map(tuple,pb.matrix_basis)),
                     [(c.name,c.type,c.influence,c.mute) for c in pb.constraints],
                     pb.custom_shape.name if pb.custom_shape else None))
    return h.hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(root / 'X_before_unity_export_0570.blend'), load_ui=False, use_scripts=False)
before=state()
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\X.blend', load_ui=False, use_scripts=False)
after=state()
config=bpy.data.objects['CoshaRig'].character_designer_unity_export
assert config.directory == r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha'
assert config.filename == 'Cosha' and config.asset_id
assert sorted(e.object.name for e in config.extras if e.enabled)==['Dress','Hair','Jacket']
result={'saved_profile':True, 'authored_geometry_rig_unchanged':before==after,
        'before_digest':before,'after_digest':after,'target':config.directory,
        'last_status':config.last_status,'report':config.last_report}
(root/'saved_profile_check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
assert before==after, result
print('SAVED_PROFILE_AND_SOURCE_PRESERVATION_PASS',json.dumps(result))
