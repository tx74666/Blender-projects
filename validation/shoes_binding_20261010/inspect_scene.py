import bpy
import json
from pathlib import Path
from character_designer import quick_bind, unity_export, character_setup
assert bpy.data.filepath == r'D:\Blender\Projects\Character\X\X.blend'
rig = bpy.data.objects['CoshaRig']
obj = bpy.data.objects['Shoes']
config = rig.character_designer_unity_export
record = quick_bind._read_backup(obj)
modifier = quick_bind._backup_modifier(obj, record)
saved = set(record['names'])
current = {b.name for b in rig.data.bones if b.use_deform}
report = {'scene': bpy.context.scene.name, 'mode': bpy.context.mode,
          'parent': getattr(obj.parent, 'name', None), 'modifier': modifier.name,
          'viewport': modifier.show_viewport, 'render': modifier.show_render,
          'vertex_groups': modifier.use_vertex_groups, 'envelopes': modifier.use_bone_envelopes,
          'mask': modifier.vertex_group, 'removed_binding': quick_bind.has_removed_binding(obj),
          'locked_groups': [g.name for g in obj.vertex_groups if g.name in current and g.lock_weight],
          'saved_bones_missing_now': sorted(saved-current), 'new_deform_bones': sorted(current-saved),
          'saved_modifier_valid': True,
          'old_backup_topology_matches': quick_bind._topology_signature(obj) == record['topology'],
          'overrides': [{'object': getattr(e.object, 'name', None), 'enabled': e.enabled} for e in config.extras],
          'bound_meshes': [o.name for o in unity_export.bound_meshes(bpy.context, rig)],
          'setup_body': getattr(character_setup.settings(bpy.context).body, 'name', None),
          'meshes_sharing_data': obj.data.users,
          'mirror_groups_enabled': [m.use_mirror_vertex_groups for m in obj.modifiers if m.type == 'MIRROR']}
folder = Path(r'D:\Blender\Projects\Character\X\validation\shoes_binding_20261010')
folder.mkdir(parents=True, exist_ok=True)
(folder/'inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
