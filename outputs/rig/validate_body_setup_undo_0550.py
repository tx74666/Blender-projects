"""Blender Undo/Redo check using disposable data and a background VIEW_3D context."""
import json
import sys
import traceback
from pathlib import Path

import bpy

sys.path[:0] = [r'D:\MyRepository\Blender-addons-by-Randy\addons',
                r'D:\MyRepository\Blender-addons-by-Randy\tests']
import character_designer
from character_designer import body_setup, limb_ik, torso_controls
import test_body_setup_plan_blender as fixtures

REPORT = Path(__file__).with_name('body_setup_undo_0550_validation.json')


def snapshot(names):
    rig, body = (bpy.data.objects[name] for name in names)
    torso_controls._update(bpy.context, rig)
    state = fixtures.states(rig, body)
    state['records'] = {key: value for key, value in rig.data.items() if isinstance(value, str)}
    state['skin'] = {name: [list(row) for row in matrix]
                     for name, matrix in body_setup._native_skin(rig).items()}
    return state


def verify(before, after, label):
    assert before.keys()==after.keys(), label
    for field in ('resources','data_keys','object_keys','constraints','records','weights'):
        assert before[field]==after[field], (label,field)
    assert {key:set(value) for key,value in before['collections'].items()}=={
        key:set(value) for key,value in after['collections'].items()}, (label,'collections')
    assert before['rest'].keys()==after['rest'].keys(), (label,'bone membership')
    rig = bpy.data.objects['Humanoid']
    for name, rest in before['rest'].items():
        assert torso_controls._same_rest(rig.data.bones[name],rest), (label,'rest',name)
    errors = {}
    for field in ('basis','pose','skin'):
        assert before[field].keys()==after[field].keys(), (label,field,'membership')
        errors[field] = max(abs(value[i][j]-after[field][name][i][j])
                            for name,value in before[field].items() for i in range(4) for j in range(4))
        assert errors[field] < 1e-4, (label,field,errors[field])
    return errors


def main():
    assert bpy.app.background
    report = {'ok':False, 'status':'RUNNING', 'background':True,
              'production_file_read':False,'production_file_written':False,'checks':{}}
    try:
        character_designer.register()
        rig,body = fixtures.fixture()
        names = rig.name,body.name
        bpy.context.preferences.edit.use_global_undo = True
        area = next((area for area in bpy.context.screen.areas if area.type=='VIEW_3D'),None)
        if area is None:
            report.update(status='UNAVAILABLE',reason='Factory background screen has no VIEW_3D area.')
            return
        region = next(region for region in area.regions if region.type=='WINDOW')
        with bpy.context.temp_override(window=bpy.context.window,area=area,region=region):
            report['context'] = {'area':bpy.context.area.type,'region':bpy.context.region.type,
                                 'mode':bpy.context.mode,'global_undo':bpy.context.preferences.edit.use_global_undo}
            before = snapshot(names)
            assert bpy.ops.ed.undo_push(message='Before Body Setup Generate')=={'FINISHED'}
            assert bpy.ops.character_designer.body_setup(action='GENERATE')=={'FINISHED'}
            generated = snapshot(names)
            assert body_setup.has_generated(bpy.data.objects[names[0]])
            assert bpy.ops.ed.undo_push(message='After Body Setup Generate')=={'FINISHED'}
            report['undo_poll'] = bpy.ops.ed.undo.poll()
            if not report['undo_poll']:
                report.update(status='UNAVAILABLE',reason='Blender ed.undo.poll() is false in this background VIEW_3D context.')
                return
            assert bpy.ops.ed.undo()=={'FINISHED'}
            report['checks']['undo_generate'] = verify(before,snapshot(names),'Undo Generate')
            assert not body_setup.has_generated(bpy.data.objects[names[0]])
            assert bpy.ops.ed.redo()=={'FINISHED'}
            report['checks']['redo_generate'] = verify(generated,snapshot(names),'Redo Generate')
            assert body_setup.has_generated(bpy.data.objects[names[0]])
            assert bpy.ops.character_designer.body_setup(action='REMOVE')=={'FINISHED'}
            removed = snapshot(names)
            assert not body_setup.has_generated(bpy.data.objects[names[0]])
            assert bpy.ops.ed.undo_push(message='After Body Setup Remove')=={'FINISHED'}
            assert bpy.ops.ed.undo()=={'FINISHED'}
            report['checks']['undo_remove'] = verify(generated,snapshot(names),'Undo Remove')
            assert body_setup.has_generated(bpy.data.objects[names[0]])
            assert bpy.ops.ed.redo()=={'FINISHED'}
            report['checks']['redo_remove'] = verify(removed,snapshot(names),'Redo Remove')
            assert not body_setup.has_generated(bpy.data.objects[names[0]])
            report.update(ok=True,status='PASSED')
    except Exception as exc:
        report.update(status='FAILED',error=str(exc),traceback=traceback.format_exc())
    finally:
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
        print('BODY_SETUP_UNDO_0550',json.dumps(report),flush=True)
    assert report['ok'], report.get('error',report.get('reason'))


if __name__=='__main__':
    main()
