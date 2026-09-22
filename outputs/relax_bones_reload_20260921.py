"""Live reload verification; no bone/mesh operations or blend save."""
import hashlib
import json
from pathlib import Path
import bpy
import character_designer as previous
from character_designer import mesh_mirror

area = bpy.context.area
obj = bpy.data.objects['Cosha']

def asset_state():
    rigs = []
    for rig in bpy.data.objects:
        if rig.type != 'ARMATURE': continue
        collection = rig.data.edit_bones if rig.mode == 'EDIT' else rig.data.bones
        bones = [(b.name, tuple(b.head if rig.mode == 'EDIT' else b.head_local),
                  tuple(b.tail if rig.mode == 'EDIT' else b.tail_local),
                  b.roll if rig.mode == 'EDIT' else tuple(tuple(r) for r in b.matrix_local),
                  b.parent.name if b.parent else '', b.use_connect, b.use_deform,
                  (b.select, b.select_head, b.select_tail) if rig.mode == 'EDIT' else rig.pose.bones[b.name].select)
                 for b in collection]
        rigs.append((rig.name, rig.mode, rig.data.use_mirror_x,
                     collection.active.name if collection.active else None, bones,
                     [(b.name, tuple(tuple(r) for r in b.matrix_basis)) for b in rig.pose.bones]))
    return dict(mesh=mesh_mirror._fingerprint(obj),
                rigs=hashlib.sha256(repr(rigs).encode()).hexdigest(),
                active=bpy.context.object.name if bpy.context.object else None,
                mode=bpy.context.mode, selected=[o.name for o in bpy.context.selected_objects])

before = asset_state()
previous._reload_addon_deferred()

def verify():
    try:
        import character_designer as current
        from character_designer import finger_chain, finger_bank
        after = asset_state()
        report = dict(version=current.bl_info['version'], before=before, after=after, unchanged=before == after)
        try:
            plan = finger_chain._selected_relax_plan(bpy.context)
            report['relax_readonly_plan'] = [p['names'] for p in plan['chains']]
            report['skipped_mirrors'] = plan['skipped_mirrors']
        except ValueError as exc:
            report['relax_readonly_plan_message'] = str(exc)
        owner = finger_bank.active_object(bpy.context)
        if owner:
            report['middle'] = [dict(name=s.name, configured=finger_bank.configured(s), error=s.error)
                                for s in owner.character_designer_finger_bank.slots if s.name.startswith('MIDDLE.')]
        Path('D:/Blender/Projects/Character/X/outputs/relax_bones_live_20260921.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('RELAX_BONES_RELOAD_VERIFIED', report)
        assert before == after and current.bl_info['version'] == (0, 61, 51)
    finally:
        area.type = 'VIEW_3D'
    return None

bpy.app.timers.register(verify, first_interval=.3)
