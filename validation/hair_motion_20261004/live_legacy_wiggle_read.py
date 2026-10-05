"""Read-only native compatibility inventory. No register/disable/frame/save."""
import bpy, sys, json, hashlib, datetime
from pathlib import Path

def value(v):
    if isinstance(v, bpy.types.ID):
        return {'id_type': v.bl_rna.identifier, 'name': v.name_full,
                'library': v.library.filepath if v.library else None}
    if hasattr(v, 'keys'):
        return {k: value(v[k]) for k in v.keys()}
    if hasattr(v, 'typecode') or isinstance(v, (list, tuple)):
        return [value(x) for x in v]
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    raise TypeError(type(v).__name__)

rows=[]
for owner in [*bpy.data.scenes, *bpy.data.objects,
              *(b for o in bpy.data.objects if o.type=='ARMATURE' for b in o.pose.bones)]:
    top={p.identifier: {'set':owner.is_property_set(p.identifier),
                       'value':None if p.type=='POINTER' and not owner.is_property_set(p.identifier) else value(getattr(owner,p.identifier))}
         for p in owner.bl_rna.properties if p.identifier.startswith('wiggle_')}
    group=owner.bl_rna.properties.get('wiggle')
    set_group=group is not None and owner.is_property_set('wiggle')
    if set_group or any(p['set'] or (k in ('wiggle_enable','wiggle_head','wiggle_tail') and p['value']) for k,p in top.items()):
        rows.append({'type':owner.bl_rna.identifier,'name':owner.name,
                     'armature':owner.id_data.name if isinstance(owner,bpy.types.PoseBone) else None,
                     'top':top,'group_set':set_group,
                     'group_raw':value(owner.wiggle) if set_group else None})
module=sys.modules.get('wiggle_2')
facts={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'runtime':bpy.app.version_string,'artist':bpy.data.filepath,
       'module':getattr(module,'__file__',None),
       'source_sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() if module else None,
       'registered': bool(module and getattr(module.WiggleScene,'is_registered',False)),
       'enabled_preference':'wiggle_2' in bpy.context.preferences.addons,
       'rows':rows}
path=Path(__file__).with_name('live_legacy_wiggle_read_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
path.write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf8')
print('LIVE_LEGACY_WIGGLE_READ',str(path),len(rows))
