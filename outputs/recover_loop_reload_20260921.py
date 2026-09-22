"""Remove the verified orphaned add-on registration, then enable the fixed build."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
import addon_utils
import bpy
import bmesh
import character_designer as old
from character_designer import mesh_mirror

area = bpy.context.area
obj = bpy.context.object
output = Path('D:/Blender/Projects/Character/X/outputs/loop_marks_live_20260921.json')


def assets():
    bm = bmesh.from_edit_mesh(obj.data)
    live = ([tuple(v.co) for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces],
            [[item.index for item in seq if item.select] for seq in (bm.verts, bm.edges, bm.faces)],
            {name: [tuple(v[bm.verts.layers.shape.get(name)]) for v in bm.verts]
             for name in bm.verts.layers.shape.keys()})
    rigs = [(rig.name, rig.mode, [(b.name, tuple(tuple(row) for row in b.matrix_local),
                                  b.parent.name if b.parent else '') for b in rig.data.bones])
            for rig in bpy.data.objects if rig.type == 'ARMATURE']
    return dict(mesh=mesh_mirror._fingerprint(obj), live=hashlib.sha256(repr(live).encode()).hexdigest(),
                rigs=hashlib.sha256(repr(rigs).encode()).hexdigest(), object=obj.name, mode=bpy.context.mode)


report = {}
assert obj and obj.type == 'MESH' and bpy.context.mode == 'EDIT_MESH'
before = assets()
try:
    actual = old._registered_rna_class(old.CHARACTERDESIGNER_OT_refresh_addon)
    assert actual is not None
    namespace = actual.execute.__globals__
    report['orphan_version'] = namespace['bl_info']['version']
    assert namespace['bl_info']['version'] == (0, 61, 54)
    assert all(namespace['_registered_rna_class'](cls) is cls for cls in namespace['CLASSES'])
    namespace['unregister']()
    assert all(namespace['_registered_rna_class'](cls) is None for cls in namespace['CLASSES'])
    assert not hasattr(bpy.types.Scene, 'character_designer_setup')
    for name in list(sys.modules):
        if name == 'character_designer' or name.startswith('character_designer.'):
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    current = addon_utils.enable('character_designer', default_set=False, refresh_handled=True)
    assert current is not None
    report['version'] = current.bl_info['version']
    assert current.bl_info['version'] == (0, 61, 55)
    current._validate_registration_integrity()
    from character_designer import finger_loop_marks_ui as ui
    ui.refresh(bpy.context)
    report['operator'] = bpy.ops.character_designer.finger_loop_marks.get_rna_type().identifier
    report['assets_unchanged'] = assets() == before
    assert report['assets_unchanged']
    report['marker_geometry_handlers'] = [f.__name__ for f in bpy.app.handlers.depsgraph_update_post
                                         if getattr(f, '__module__', '') == ui.__name__]
    assert not report['marker_geometry_handlers']
    report['marked_bones'] = False
    report['saved_blend'] = False
except Exception:
    import traceback
    report['error'] = traceback.format_exc()
finally:
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('LOOP_MARKS_LIVE', report)
    area.type = 'VIEW_3D'
