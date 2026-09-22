"""Acknowledge only the two applied files, then verify the timers are quiet."""
import json
import sys
from pathlib import Path
import bpy
import character_designer as cd
from character_designer import finger_workflow_ui as ui

current = cd._source_signature()
old = {row[0]: row[1:] for row in cd.ADDON_LOADED_SIGNATURE}
new = {row[0]: row[1:] for row in current}
changed = sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))
assert set(changed) <= {'__init__.py', 'finger_workflow_ui.py'}, changed
assert cd.bl_info['version'] == (0, 61, 43)
assert not cd.ADDON_REFRESH_PENDING and not cd.ADDON_REFRESH_LAST_ERROR
cd.ADDON_LOADED_SIGNATURE = current
cd.ADDON_REFRESH_LAST_STATE = False
final_area = bpy.context.area


def finalize():
    final_area.type = 'VIEW_3D'
    report = dict(version=list(cd.bl_info['version']), acknowledged_files=changed,
                  monitor_pending=ui._refresh_request is not None,
                  monitor_timer=bpy.app.timers.is_registered(ui._refresh),
                  rebuilding=ui._rebuilding, profiler_active=sys.getprofile() is not None,
                  eye_enabled=bpy.context.object.character_designer_finger_workflow.preview_enabled,
                  source_changed=cd._source_changed(), mode=bpy.context.object.mode,
                  editor=final_area.type)
    report['quiet'] = not any(report[k] for k in ('monitor_pending', 'monitor_timer', 'rebuilding', 'profiler_active', 'source_changed'))
    Path(r'D:\Blender\Projects\Character\X\outputs\monitor_fix_20260921\final_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('MONITOR_FINAL_AUDIT', json.dumps(report))
    return None


bpy.app.timers.register(finalize, first_interval=.4)
