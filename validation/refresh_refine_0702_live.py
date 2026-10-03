"""Refresh the add-on and inspect the existing selection without model writes."""
import bpy
import json
import sys
from pathlib import Path

console_area = bpy.context.area
try:
    previous = sys.modules['character_designer']
    old_repair = sys.modules['character_designer.refine_symmetry']
    obj = bpy.context.edit_object
    before = old_repair.fingerprint(obj)
    ids_before = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.scenes))
    mirror_before = (obj.data.use_mirror_x, obj.data.use_mirror_y,
                     obj.data.use_mirror_z, obj.data.use_mirror_topology)
    previous._reload_addon_deferred()
    current = sys.modules['character_designer']
    current._validate_registration_integrity()
    assert current.bl_info['version'] == (0, 70, 2)
    assert not current.ADDON_REFRESH_LAST_ERROR, current.ADDON_REFRESH_LAST_ERROR
    repair = sys.modules['character_designer.refine_symmetry']
    ui = sys.modules['character_designer.refine_symmetry_ui']
    settings = bpy.context.scene.character_designer_refine_symmetry
    settings.axis = 'X'
    settings.mode = 'LEFT_TO_RIGHT'
    settings.selected_only = True
    settings.show_advanced = False
    report = repair.analyze(obj, axis='X', selected_only=True)
    proposal = repair.plan(obj, axis='X', mode='LEFT_TO_RIGHT', selected_only=True)
    ui._remember(bpy.context, obj, report)
    after = repair.fingerprint(obj)
    ids_after = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.scenes))
    mirror_after = (obj.data.use_mirror_x, obj.data.use_mirror_y,
                    obj.data.use_mirror_z, obj.data.use_mirror_topology)
    assert before == after, 'Model or selection changed during refresh/analysis'
    assert ids_before == ids_after, 'Temporary mirror lookup IDs remain'
    assert mirror_before == mirror_after, 'Artist mirror settings changed'
    result = dict(version=current.bl_info['version'], refresh_error=current.ADDON_REFRESH_LAST_ERROR,
                  object=obj.name, mode=obj.mode, selection=list(proposal._before['selection']),
                  matched=report.matched, misaligned=report.misaligned,
                  unmatched=list(report.unmatched), max_error=report.max_error,
                  pairs=report.pairs, planned_vertices=sorted(proposal.positions),
                  fingerprint_before=before, fingerprint_after=after,
                  model_and_selection_unchanged=before == after,
                  temporary_ids_cleaned=ids_before == ids_after,
                  artist_mirror_settings_preserved=mirror_before == mirror_after,
                  live_refine_applied=False, blend_saved=False)
    Path(r'D:\Blender\Projects\Character\X\validation\refine_0702_live_refresh_20261002.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print('REFINE_0702_LIVE_REFRESH_OK', report.matched, report.misaligned, list(report.unmatched))
finally:
    console_area.type = 'NODE_EDITOR'
    console_area.ui_type = 'GeometryNodeTree'
