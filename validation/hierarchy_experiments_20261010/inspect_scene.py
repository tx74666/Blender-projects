"""Read the current artist hierarchy and Outliner display controls."""
import bpy
import json
from mathutils import Matrix
from pathlib import Path

assert Path(bpy.data.filepath) == Path('D:/Blender/Projects/Character/X/X.blend')
assert bpy.context.scene.name == 'Scene' and not bpy.app.background
rig = bpy.data.objects['CoshaRig']
report = {'mode': bpy.context.mode, 'frame': bpy.context.scene.frame_current, 'objects': {}}
for name in ('Jacket', 'Shoes'):
    obj = bpy.data.objects[name]
    effective = rig.matrix_world @ obj.matrix_parent_inverse
    identity = Matrix.Identity(4)
    report['objects'][name] = {
        'parent': obj.parent.name if obj.parent else None, 'parent_type': obj.parent_type,
        'effective_parent_identity_error': max(abs(a-b) for ra,rb in zip(effective,identity) for a,b in zip(ra,rb)),
        'world': [list(row) for row in obj.matrix_world],
        'constraints': [{'name': c.name, 'muted': c.mute, 'influence': c.influence} for c in obj.constraints],
        'parent_metadata': [k for k in obj.keys() if k.startswith('character_designer_quick_binding_parent') or k == 'character_designer_quick_binding_previous_parent'],
        'armatures': [{'name': m.name, 'rig': m.object.name if m.object else None,
                       'viewport': m.show_viewport, 'render': m.show_render} for m in obj.modifiers if m.type == 'ARMATURE'],
    }
report['other_objects'] = [{'name': o.name, 'type': o.type, 'parent': o.parent.name if o.parent else None,
                            'parent_type': o.parent_type, 'parent_bone': o.parent_bone}
                           for o in bpy.context.scene.objects if o.type not in {'MESH','ARMATURE','EMPTY','LIGHT','CAMERA'}]
report['outliners'] = [{'children': a.spaces.active.use_filter_children,
                        'others': a.spaces.active.use_filter_object_others,
                        'display_mode': a.spaces.active.display_mode}
                       for a in bpy.context.screen.areas if a.type == 'OUTLINER']
folder = Path('D:/Blender/Projects/Character/X/validation/hierarchy_experiments_20261010')
(folder/'inspection.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
