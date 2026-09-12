"""Prove the live migration guard against an immutable copy of current saved X."""
import bpy
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

OUT=Path(r'D:\Blender\Projects\Character\X\outputs/rig')
SOURCE=OUT.parent.parent/'X.blend'
spec=importlib.util.spec_from_file_location('foot_checks',OUT/'validate_foot_direction_0532.py')
test=importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
source_before=test.h.sha_file(SOURCE)
folder=OUT/'fixtures'
folder.mkdir(exist_ok=True)
fixture=folder/('X_foot_direction_0532_input_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.blend')
shutil.copy2(SOURCE,fixture)
fixture_before=test.h.sha_file(fixture)
assert fixture_before==source_before, 'Source changed while fixture was copied.'
test.checks.cd.register()
bpy.ops.wm.open_mainfile(filepath=str(fixture),use_scripts=False)
test.refresh()
rig=test.checks.rig
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
test.limb._mode_set(bpy.context,rig,'POSE')
before=test.capture_current()
mesh_before=test.checks.evaluated_meshes()
prior={side:record.get('rotation_direction','LEGACY') for side,record in test.service.records(rig).items()}
test.migrate()
errors=test.assert_unchanged(before,test.capture_current())
mesh_errors=test.checks.mesh_errors(mesh_before)
assert max(mesh_errors.values(),default=0.)<5e-6
test.checks.validate_existing()
fixture_after=test.h.sha_file(fixture)
assert fixture_after==fixture_before
summary={'ok':True,'fixture':str(fixture),'fixture_sha_before':fixture_before,
    'fixture_sha_after':fixture_after,'fixture_unchanged':True,'input_direction':prior,
    'live_helper_errors':errors,'mesh_errors':mesh_errors,
    'production_sha_before_copy':source_before,'production_sha_after':test.h.sha_file(SOURCE),
    'production_write_performed':False}
summary['production_checksum_external_change']=summary['production_sha_before_copy']!=summary['production_sha_after']
(OUT/'foot_direction_0532_fixture_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
report=json.loads((OUT/'foot_direction_0532_validation.json').read_text(encoding='utf-8'))
report['immutable_fixture_verification']=summary
(OUT/'foot_direction_0532_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FOOT_DIRECTION_FIXTURE',json.dumps(summary),flush=True)
