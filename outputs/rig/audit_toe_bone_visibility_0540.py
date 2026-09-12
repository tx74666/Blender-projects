"""Read-only saved-X investigation of visible non-selectable body bones."""
import bpy
import json
import sys
from pathlib import Path
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import bone_collections as groups, foot_controls as foot, limb_ik as limb
path = Path(r'D:\Blender\Projects\Character\X')
bpy.ops.wm.open_mainfile(filepath=str(path / 'X.blend'), use_scripts=False)
rig = bpy.data.objects['CoshaRig']
body = groups.body_collection(rig)
internal = rig.data.collections_all.get(groups.INTERNAL_NAME)
def visible(b):
    return not b.hide and (not b.collections or any(c.is_visible_effectively for c in b.collections))
def state(b):
    pb = rig.pose.bones[b.name]
    return dict(name=b.name, hide=b.hide, hide_select=b.hide_select, visible=visible(b),
                collections=[c.name for c in b.collections], deform=b.use_deform,
                shape=pb.custom_shape.name if pb.custom_shape else None,
                properties=dict(b.items()))
mechanisms = [name for record in foot.records(rig).values() for role,name in record['bones'].items()
              if role not in {'TOE_BEND', 'FOOT_ROLL'}]
result = dict(roots=list(rig.data.collections.keys()),
              collection_properties=[p.identifier for p in body.bl_rna.properties] if body else [],
              body_members=list(body.bones.keys()) if body else [],
              internal_members=list(internal.bones.keys()) if internal else [],
              toe_mechanisms=[state(rig.data.bones[n]) for n in mechanisms],
              gray_visible=[state(b) for b in rig.data.bones if visible(b) and b.hide_select],
              foot={k:sorted(v) if isinstance(v,set) else {n:sorted(s) for n,s in v.items()}
                    for k,v in foot.collection_members(rig).items()})
try:
    inventory=limb._validate_inventory(rig)
    generated={b.name for b in inventory['bones']}|foot.collection_members(rig)['generated']
    native=groups._native_body_names(rig,generated,set())
    expected=groups._animation_names(rig,inventory,native)
    result['unexpected_body_mechanisms']=sorted(set(mechanisms)&expected)
except Exception as exc: result['inventory_error']=str(exc)
(path/'outputs/rig/toe_bone_visibility_0540_audit.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf8')
print('TOE_VISIBILITY',json.dumps({k:v for k,v in result.items() if k not in {'body_members','internal_members','foot'}},default=str),flush=True)
