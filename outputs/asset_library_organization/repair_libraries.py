import bpy
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

def repair_asset_libraries():
    out=Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization')
    desired={
        'Nodes':r'D:\Blender\Helper\Asset-Libraries\Costom\Nodes',
        'Procedural Material':r'D:\Blender\Helper\Asset-Libraries\Costom\Procedural Material',
        'Pose Library':r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library',
    }
    for name,path in desired.items():
        assert Path(path).is_dir() and (Path(path)/'blender_assets.cats.txt').is_file(), name
    assert 'Pose Library/Cosha:Cosha' in (Path(desired['Pose Library'])/'blender_assets.cats.txt').read_text(encoding='utf8')
    assert bpy.context.area.type=='CONSOLE'
    libs=bpy.context.preferences.filepaths.asset_libraries
    describe=lambda:[{'name':lib.name,'path':lib.path,'import_method':lib.import_method} for lib in libs]
    before=describe()
    prefs_path=Path(bpy.utils.user_resource('CONFIG'))/'userpref.blend'
    backup=out/'backups'/('repair-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid()))
    backup.mkdir(parents=True,exist_ok=False)
    if prefs_path.is_file():shutil.copy2(prefs_path,backup/'userpref.blend')
    for name,path in desired.items():
        lib=libs.get(name)
        if lib is None:
            lib=libs.new(name=name,directory=path)
            lib.import_method='PACK'
        else:
            lib.path=path
    after=describe()
    assert all(entry in after for entry in before if entry['name'] not in desired), 'Unrelated library changed'
    assert len([lib for lib in libs if lib.name=='Pose Library'])==1
    result=bpy.ops.wm.save_userpref()
    assert result=={'FINISHED'}, result
    window=bpy.context.window
    area=bpy.context.area
    report={'pid':os.getpid(),'time':datetime.now().isoformat(),'filepath':bpy.data.filepath,
            'before':before,'after':after,'preferences_saved':True,'project_saved':False,'backup':str(backup)}
    target=out/('repair_result_'+str(os.getpid())+'.json')
    def write():target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    write()
    def restore():
        area.ui_type='ASSETS'
        bpy.app.timers.register(refresh,first_interval=0.25)
    def refresh():
        space=area.spaces.active
        if space.type!='FILE_BROWSER' or space.params is None:return 0.2
        try:
            space.params.asset_library_reference='Pose Library'
            space.params.asset_catalog_visibility='ALL'
            space.params.filter_search=''
            region=next(r for r in area.regions if r.type=='WINDOW')
            with bpy.context.temp_override(window=window,area=area,region=region):
                refreshed=bpy.ops.asset.library_refresh(use_remote_listing=False)
            report['refresh']=list(refreshed)
            report['selected_library']=space.params.asset_library_reference
            area.tag_redraw()
        except Exception as exc:
            report['refresh_error']=repr(exc)
        write()
    bpy.app.timers.register(restore,first_interval=0.25)
    print('Saved Nodes, Procedural Material and Pose Library; restoring Pose Library browser. No blend saved.')

repair_asset_libraries()
