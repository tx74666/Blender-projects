"""Verify widget organization in a disposable scene; helpers never open/save on import."""
import bpy, importlib.util, json, sys, traceback
from pathlib import Path
OUT = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import widget_collections as widgets
spec=importlib.util.spec_from_file_location('widgets_preservation_checks',OUT/'validate_bone_display_0540.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
original_properties=checks.properties

def normalized_properties(item):
    values=original_properties(item)
    if isinstance(item,bpy.types.Armature):
        modules=widgets._modules()
        for module in modules[1:]:
            if module.RECORD_KEY not in values:
                continue
            record=json.loads(values[module.RECORD_KEY])
            if module==modules[1]:
                for side,leg in record['legs'].items():
                    leg['widget_collection']='@Foot.'+side
            elif module in modules[-3:]:
                record['collection']='@'+module.__name__
            else:
                record['widget_collection']='@'+module.__name__
            values[module.RECORD_KEY]=json.dumps(record,sort_keys=True)
    return values
checks.properties=normalized_properties

def display_state():
    return {obj.name:{'shapes':obj.data.show_bone_custom_shapes,'display':obj.data.display_type,
      'collections':[[c.name,c.is_visible,c.is_solo,c.is_expanded,list(c.bones.keys())] for c in obj.data.collections_all],
      'bones':[[pb.name,pb.bone.hide,pb.bone.hide_select,getattr(pb,'hide',None)] for pb in obj.pose.bones]}
      for obj in bpy.data.objects if obj.type=='ARMATURE'}

def collection_state(rig):
    resources=widgets._resources(rig)
    labels={item['collection']:'@'+item['label'] for item in resources}
    def key(c):return labels.get(c,c.name)
    result={}
    for c in bpy.data.collections:
        if c.get(widgets.OWNER_KEY)==widgets.OWNER_VALUE:
            continue
        settings=checks.rna_values(c)
        settings.pop('name',None)
        result[key(c)]={'settings':settings,'props':original_properties(c),
          'objects':sorted(c.objects.keys()),'children':sorted(key(x) for x in c.children if x not in labels and x.get(widgets.OWNER_KEY)!=widgets.OWNER_VALUE),
          'parents':None if c in labels else sorted(key(x) for x in widgets._parents(c)),
          'layers':[[view.id_data.name,view.name,flags] for view,flags in widgets._layer_states(c)]}
    return result

def snapshot(rig):
    return {'scene':checks.capture_current(),'display':display_state(),'collections':collection_state(rig)}

def unchanged(before,rig):
    after=snapshot(rig)
    error=checks.assert_unchanged(before['scene'],after['scene'])
    assert before['display']==after['display'],'Bone visibility or shape display changed'
    assert before['collections']==after['collections'],'Collection contents or visibility changed'
    return error

def main():
    assert bpy.app.background
    fixture=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(json.loads((OUT/'widget_collections_0543_audit.json').read_text())['source'])
    preview=OUT/'X_widgets_0543_preview.blend'
    report={'ok':False,'fixture':str(fixture),'preview':str(preview),'main_file_written':False}
    protected=checks.helpers.sha_file(fixture)
    try:
        cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(fixture),use_scripts=False)
        rig=bpy.data.objects['CoshaRig']
        before=snapshot(rig)
        report['organized']=widgets.organize(bpy.context,rig)
        report['pose_error']=unchanged(before,rig)
        first_count=len(bpy.data.collections)
        report['repeat']=widgets.organize(bpy.context,rig)
        assert not report['repeat']['renamed']
        assert len(bpy.data.collections)==first_count
        report['repeat_pose_error']=unchanged(before,rig)
        assert bpy.ops.wm.save_as_mainfile(filepath=str(preview),copy=True)=={'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(preview),use_scripts=False)
        rig=bpy.data.objects['CoshaRig']
        report['reopen_pose_error']=unchanged(before,rig)
        report['root_children']=list(bpy.data.collections['CDesigner Widgets'].children.keys())
        report['leaves']=[x['collection'].name for x in widgets._resources(rig)]
        report.update(ok=True,version=list(cd.bl_info['version']),counts=before['scene']['counts'])
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        report['fixture_unchanged']=checks.helpers.sha_file(fixture)==protected
        (OUT/'widgets_0543_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('WIDGET_VALIDATION',json.dumps(report),flush=True)
    assert report['ok'],report.get('error')
    assert report['fixture_unchanged']

if __name__=='__main__':main()
