"""Run once from the live Blender Console; reload code without editing assets."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import character_designer as previous
from character_designer import mesh_mirror

area = bpy.context.area
obj = bpy.data.objects['Cosha']
assert obj.mode == 'OBJECT', 'This check expects the observed Object Mode.'
retired = {'finger_joint', 'finger_joint_plan', 'finger_layout', 'finger_layout_ui',
           'finger_ring_slide', 'finger_subdivision', 'finger_workflow',
           'finger_workflow_rebase', 'finger_workflow_ui', 'finger_preview_proof'}

def asset_state():
    bones = tuple((rig.name, tuple((b.name, tuple(b.head_local), tuple(b.tail_local),
                  tuple(tuple(r) for r in b.matrix_local), b.parent.name if b.parent else '',
                  b.use_connect) for b in rig.data.bones),
                  tuple((b.name, tuple(tuple(r) for r in b.matrix_basis)) for b in rig.pose.bones))
                  for rig in bpy.data.objects if rig.type == 'ARMATURE')
    return dict(mesh=mesh_mirror._fingerprint(obj),
                bones=hashlib.sha256(repr(bones).encode()).hexdigest(),
                data=obj.data.name, counts=[len(obj.data.vertices), len(obj.data.edges), len(obj.data.polygons)],
                shape_keys=[k.name for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else [],
                mode=obj.mode)

before = asset_state()
old_callbacks = [fn for name, module in list(sys.modules.items())
                 if name.startswith('character_designer.') and name.rsplit('.', 1)[-1] in retired
                 for fn in vars(module).values() if callable(fn) and getattr(fn, '__module__', '') == name]
old_version = previous.bl_info['version']
previous._reload_addon_deferred()

def verify():
    try:
        import character_designer as current
        after = asset_state()
        lingering = [name for name in sys.modules if name.startswith('character_designer.') and name.rsplit('.', 1)[-1] in retired]
        timers = [fn.__name__ for fn in old_callbacks if bpy.app.timers.is_registered(fn)]
        handlers = [fn.__name__ for name in dir(bpy.app.handlers)
                    for fn in (getattr(bpy.app.handlers, name) if isinstance(getattr(bpy.app.handlers, name), list) else [])
                    if getattr(fn, '__module__', '').rsplit('.', 1)[-1] in retired]
        report = dict(before_version=old_version, version=current.bl_info['version'], before=before, after=after,
                      assets_unchanged=before == after, obsolete_modules=lingering, obsolete_timers=timers,
                      obsolete_handlers=handlers, obsolete_workflow_rna=hasattr(bpy.types.Object, 'character_designer_finger_workflow'),
                      obsolete_layout_rna=hasattr(bpy.types.Scene, 'character_designer_finger_layout'),
                      obsolete_joint_rna=hasattr(bpy.types.WindowManager, 'character_designer_finger_joint'))
        Path('D:/Blender/Projects/Character/X/outputs/retire_finger_topology_live_20260921.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('FINGER_TOPOLOGY_RETIRED', report)
        assert before == after and current.bl_info['version'] == (0, 61, 50)
        assert not lingering and not timers and not handlers
        assert not any(report[k] for k in ('obsolete_workflow_rna', 'obsolete_layout_rna', 'obsolete_joint_rna'))
    finally:
        area.type = 'VIEW_3D'
    return None

bpy.app.timers.register(verify, first_interval=.3)
