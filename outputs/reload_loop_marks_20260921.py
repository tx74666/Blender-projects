"""Reload the validated add-on without applying joints or saving the scene."""
import hashlib
import json
from pathlib import Path
import bpy
import bmesh
import character_designer as previous
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


assert obj and obj.type == 'MESH' and bpy.context.mode == 'EDIT_MESH'
before = assets()
previous._reload_addon_deferred()


def verify():
    report = {}
    try:
        import character_designer as current
        from character_designer import finger_loop_marks_ui as ui
        report['version'] = current.bl_info['version']
        assert current.bl_info['version'] == (0, 61, 54)
        report['operator'] = bpy.ops.character_designer.finger_loop_marks.get_rna_type().identifier
        report['assets_unchanged'] = assets() == before
        assert report['assets_unchanged'], 'Reload changed artist data or selection'
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
    return None


bpy.app.timers.register(verify, first_interval=.3)
