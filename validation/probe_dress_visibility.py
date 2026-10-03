"""Read the saved scene's Dress display only; never save or mutate it."""
import json
import sys
from pathlib import Path
import bpy

bpy.ops.wm.open_mainfile(filepath='D:/Blender/Projects/Character/X/X.blend')
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import bone_display as display, body_original_mode as original

layer = bpy.context.view_layer
main = bpy.data.objects['CoshaRig']
groups = original._native_groups(bpy.context, main)

def visible_bones(rig):
    return [b.name for b in rig.data.bones
            if not getattr(rig.pose.bones[b.name], 'hide', b.hide)
            and (not b.collections or any(c.is_visible_effectively for c in b.collections))]

def layer_tree(node):
    return {'name': node.name, 'hide': node.hide_viewport, 'exclude': node.exclude,
            'global_hide': node.collection.hide_viewport,
            'children': [layer_tree(c) for c in node.children]}

result = {
    'scene': bpy.data.filepath,
    'original_session': original.active(main),
    'groups': {role: [{'rig': rig.name, 'target_count': len(names),
                      'blue': original._targets_visible({rig: names})}
                     for rig, names in targets.items()]
               for role, targets in groups.items()},
    'armatures': [{'name': rig.name, 'mode': rig.mode,
                   'hide_viewport': rig.hide_viewport,
                   'hide_get': rig.hide_get(view_layer=layer),
                   'visible_get': rig.visible_get(view_layer=layer),
                   'hide_select': rig.hide_select, 'show_in_front': rig.show_in_front,
                   'selected': rig.select_get(view_layer=layer),
                   'in_view_layer': rig.name in layer.objects,
                   'parent': rig.parent.name if rig.parent else None,
                   'collections': [c.name for c in rig.users_collection],
                   'bone_count': len(rig.data.bones),
                   'visible_bones': visible_bones(rig),
                   'bone_collections': [{'name': c.name, 'visible': c.is_visible,
                                        'effective': c.is_visible_effectively,
                                        'solo': c.is_solo} for c in rig.data.collections_all]}
                  for rig in bpy.context.scene.objects if rig.type == 'ARMATURE'],
    'layer_tree': layer_tree(layer.layer_collection),
}
out = Path('D:/Blender/Projects/Character/X/validation/dress_visibility_0710_saved_state.json')
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print('DRESS_SAVED_STATE', json.dumps(result['groups']), flush=True)
for arm in result['armatures']:
    print('ARMATURE_OBJECT_STATE', json.dumps({k: v for k, v in arm.items()
          if k not in {'visible_bones', 'bone_collections'}}), flush=True)
