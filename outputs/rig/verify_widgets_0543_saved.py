import bpy,importlib.util,json
from pathlib import Path
OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
spec=importlib.util.spec_from_file_location('saved_widget_checks',OUT/'validate_widgets_0543.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.cd.register()
report=json.loads((OUT/'widgets_0543_live_result.json').read_text(encoding='utf-8'))
source=OUT.parent.parent/'X.blend'
sha=checks.checks.helpers.sha_file(source)
bpy.ops.wm.open_mainfile(filepath=report['backup'],use_scripts=False)
before=checks.snapshot(bpy.data.objects['CoshaRig'])
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
rig=bpy.data.objects['CoshaRig']
error=checks.unchanged(before,rig)
assert [x['collection'].name for x in checks.widgets._resources(rig)]==report['collections']
assert len(bpy.data.collections['CDesigner Widgets'].children)==1
assert all(x['collection'] in bpy.data.collections['CoshaRig · Widgets'].children_recursive for x in checks.widgets._resources(rig))
assert checks.checks.helpers.sha_file(source)==sha
report.update(main_saved=True,saved_pose_error=error,saved_sha256=sha,saved_preservation_verified=True)
(OUT/'widgets_0543_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SAVED_WIDGETS_VERIFIED',json.dumps(report),flush=True)
