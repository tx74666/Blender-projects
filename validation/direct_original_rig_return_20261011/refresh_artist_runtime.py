import bpy,sys,json,hashlib,importlib,addon_utils
from pathlib import Path
evidence=Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
sys.path.insert(0,str(evidence))
import validation_preservation
importlib.reload(validation_preservation)
import verify_addon_refresh_isolated as verifier
importlib.reload(verifier)
assert Path(bpy.data.filepath).resolve()==Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
old=importlib.import_module('character_designer')
assert tuple(old.bl_info['version'])==(0,77,23)
from character_designer.animation import _link_idle
assert _link_idle(), 'An animation/export job is active; defer refresh.'
install=Path(old.__file__).resolve().parent
manifest=json.loads((evidence/'release_projection_07724.json').read_text(encoding='utf-8'))
for name,digest in manifest['files'].items():
    assert hashlib.sha256((install/name).read_bytes()).hexdigest()==digest, 'Disk projection mismatch: '+name
before_scene=verifier.scene_capture()
before_wm=verifier.wm_capture(old)
before_context=verifier.native_context()
before_pose=verifier.native_pose_channels()
before_assets=verifier.assets(importlib.import_module('character_designer.unity_animation'))
report={'old_version':list(old.bl_info['version']),'path':str(install),'completed':False}
try:
    addon_utils.disable('character_designer',default_set=False)
    assert not getattr(old,'__addon_enabled__',False)
    for name in list(sys.modules):
        if name=='character_designer' or name.startswith('character_designer.'):
            del sys.modules[name]
    new=verifier.mount(install.parent)
    assert tuple(new.bl_info['version'])==(0,77,24)
    assert not verifier.differences(before_scene,verifier.scene_capture()), 'Persistent Scene data changed.'
    restored=[]
    for name,fields in before_wm.items():
        verifier.restore_only_changed_wm(getattr(bpy.context.window_manager,name),fields,name,restored)
    assert not verifier.differences(before_wm,verifier.wm_capture(new)), 'WM state changed.'
    assert not verifier.differences(before_context,verifier.native_context()), 'Active context changed.'
    assert not verifier.differences(before_pose,verifier.native_pose_channels()), 'Pose channels changed.'
    assert not verifier.differences(before_assets,verifier.assets(importlib.import_module('character_designer.unity_animation'))), 'Artist assets changed.'
    report.update({'new_version':list(new.bl_info['version']),'wm_fields_restored':restored,'context':verifier.native_context(),'completed':True})
finally:
    (evidence/'artist_refresh_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'completed':report['completed'],'version':report.get('new_version')}))
