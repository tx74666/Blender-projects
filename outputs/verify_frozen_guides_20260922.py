"""Reload local build and audit frozen display on the unsaved artist scene."""
import hashlib
import json
import time
import traceback
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import bpy
import bmesh
import character_designer as previous
from character_designer import mesh_mirror

C = bpy.context
area, obj = C.area, C.object
output = Path('D:/Blender/Projects/Character/X/outputs/frozen_guides_live_20260922.json')
report = {}


def artist_state():
    mesh = mesh_mirror._fingerprint(obj)
    live = None
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        live = ([tuple(v.co) for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces],
                [[item.index for item in seq if item.select] for seq in (bm.verts, bm.edges, bm.faces)],
                {name: [tuple(v[bm.verts.layers.shape.get(name)]) for v in bm.verts]
                 for name in bm.verts.layers.shape.keys()})
    rigs = [(rig.name, [(bone.name, tuple(tuple(row) for row in bone.matrix_local))
                        for bone in rig.data.bones]) for rig in bpy.data.objects if rig.type == 'ARMATURE']
    state = obj.character_designer_finger_bank
    records = [(s.name, s.guide.record, s.guide.bend_record, s.guide.confirmed, s.bones) for s in state.slots]
    return dict(mesh=mesh, live=hashlib.sha256(repr(live).encode()).hexdigest(),
                rigs=hashlib.sha256(repr(rigs).encode()).hexdigest(), mode=C.mode,
                records=records, marks=obj.get('character_designer_finger_loop_marks', ''),
                active=state.active, selected=tuple(state.visible_digits))


try:
    assert obj and obj.type == 'MESH' and C.mode in {'EDIT_MESH', 'OBJECT'}
    before = artist_state()
    state = obj.character_designer_finger_bank
    report['previous_version'] = previous.bl_info['version']
    report['previous_errors'] = {slot.name: slot.error for slot in state.slots if slot.error}
    previous._reload_addon_deferred()
    import character_designer as current
    from character_designer import finger_definition as definition, finger_bank as bank
    from character_designer import finger_definition_ui as guides, finger_bone_tools as bones
    from character_designer import finger_loop_marks_ui as marks, finger_flex, forearm_twist
    assert current.bl_info['version'] == (0, 61, 58)
    current._validate_registration_integrity()
    report['version'] = current.bl_info['version']
    report['finger_geometry_handlers'] = [fn.__name__ for fn in bpy.app.handlers.depsgraph_update_post
        if getattr(fn, '__module__', '') in (guides.__name__, bones.__name__, marks.__name__)]
    assert not report['finger_geometry_handlers']
    report['hair_preview_active'] = bool(current._settings(C).preview_active)
    report['forearm_session_active'] = bool(getattr(forearm_twist, '_SESSION', None))
    report['legacy_flex_visible'] = bool(finger_flex._visible)
    checks = []
    with ExitStack() as stack:
        for owner, name in ((definition, '_snapshot'), (definition, '_topology'),
                            (definition, 'frame'), (definition, '_validate_mesh'),
                            (bank, 'dirty'), (bank, 'adapt_topology')):
            checks.append(stack.enter_context(patch.object(owner, name,
                side_effect=AssertionError('Frozen display read geometry: '+name))))
        guides.redraw()
        started = time.perf_counter()
        for _ in range(200):
            assert guides.cached_frame(C)[0]
            assert guides.display_frames(C)
            marks.visible(C)
        report['display_cpu_ms_per_iteration'] = (time.perf_counter()-started)*1000/200
        report['geometry_calls'] = sum(check.call_count for check in checks)
        assert report['geometry_calls'] == 0
    state = obj.character_designer_finger_bank
    report['current_errors'] = {slot.name: slot.error for slot in state.slots if slot.error}
    report['artist_state_unchanged'] = artist_state() == before
    assert report['artist_state_unchanged']
    report['saved_blend'] = False
except Exception:
    report['error'] = traceback.format_exc()
finally:
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('FROZEN_GUIDES_LIVE', report)
    area.type = 'VIEW_3D'
