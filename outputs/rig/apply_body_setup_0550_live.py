"""Refresh the deployed add-on and add validated missing Body controls in X."""
import bpy, importlib, importlib.util, json, runpy, traceback
from datetime import datetime
from pathlib import Path

out = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
production = Path(r'D:\Blender\Projects\Character\X\X.blend')
report = {'ok': False, 'main_saved': False}
assert Path(bpy.data.filepath).resolve() == production.resolve()
assert not bpy.app.background and bpy.context.mode == 'OBJECT'
assert bpy.context.object and bpy.context.object.name == 'CoshaRig'
assert json.loads((out/'body_setup_repaired_0550_validation.json').read_text())['ok']
backup = out/'backups'/('X_before_body_setup_0550_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
report['backup'] = str(backup)
try:
    repair_ns = runpy.run_path(str(out/'repair_reversal_20260912.py'))
    mesh_before = repair_ns['digest_meshes']()
    import character_designer as cd
    if tuple(cd.bl_info['version']) != (0,55,0):
        cd._reload_addon_deferred()
        cd = importlib.import_module('character_designer')
    assert tuple(cd.bl_info['version']) == (0,55,0)
    assert repair_ns['digest_meshes']() == mesh_before, 'Plugin refresh changed native mesh data'
    spec = importlib.util.spec_from_file_location('body_setup_live_checks', out/'validate_body_setup_repaired_0550.py')
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    from character_designer import body_setup, limb_ik, bone_display, root_control
    rig = bpy.data.objects['CoshaRig']
    before = checks.capture_current()
    proposed = body_setup.plan(bpy.context, rig)
    assert not proposed['blocked'], str(proposed)
    report['created'] = [entry['key'] for entry in proposed['components'] if entry['status']=='ADD']
    report['reused'] = [entry['key'] for entry in proposed['components'] if entry['status']=='REUSE']
    assert bpy.ops.character_designer.body_setup(action='GENERATE') == {'FINISHED'}
    report['preservation'] = checks.compare_generation(before, checks.capture_current())
    assert not body_setup.generate(bpy.context, rig)['created']
    settings = limb_ik._settings(bpy.context)
    settings.show_body_setup_advanced = False
    bone_display.show_controls(bpy.context, rig, 'BODY')
    limb_ik._mode_set(bpy.context, rig, 'POSE')
    for pb in rig.pose.bones:
        pb.select = False
    master = root_control.control_name(rig)
    if master:
        rig.data.bones.active = rig.data.bones[master]
        rig.pose.bones[master].select = True
    if bpy.context.area.type == 'CONSOLE':
        bpy.context.area.type = 'VIEW_3D'
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    report.update(ok=True, version=list(cd.bl_info['version']), module=cd.__file__)
    assert bpy.ops.wm.save_as_mainfile(filepath=str(production)) == {'FINISHED'}
    report['main_saved'] = True
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
    raise
finally:
    (out/'body_setup_0550_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('BODY_SETUP_LIVE_0550', json.dumps(report), flush=True)
