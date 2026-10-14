"""Read a saved seed Action list in an owned empty Blender, without add-on registration."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
p=argparse.ArgumentParser()
for key in ('seed','snapshot','protected-artist','output'):
    p.add_argument('--'+key,required=True)
    if key!='output': p.add_argument('--'+key+'-sha256',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert bpy.app.background and not bpy.data.filepath and not bpy.data.actions
assert not any(n=='character_designer' or n.startswith('character_designer.') for n in sys.modules)
pins={}
for key in ('seed','snapshot','protected_artist'):
    path=Path(getattr(a,key)).resolve(); expected=getattr(a,key+'_sha256')
    assert sha(path)==expected
    pins[key]={'path':str(path),'sha256':expected,'bytes':path.stat().st_size}
out=Path(a.output).resolve()
root=Path('D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012').resolve()
assert out.is_relative_to(root) and not out.exists() and out.parent.is_dir()
snapshot=json.loads(Path(a.snapshot).read_text(encoding='utf-8-sig'))
expected=[row['identity'] for row in snapshot['before']['actions']]
with bpy.data.libraries.load(a.seed,link=False) as (source,destination):
    available=list(source.actions)
    destination.actions=list(source.actions)
loaded=[{'type':action.bl_rna.identifier,'name':action.name,'library':action.library.filepath if action.library else None,
    'users':action.users,'fake_user':action.use_fake_user,'asset':action.asset_data is not None,
    'slots':[{'handle':slot.handle,'identifier':slot.identifier} for slot in action.slots]} for action in bpy.data.actions]
expected_local={row['name'] for row in expected if row['library'] is None}
loaded_local={row['name'] for row in loaded if row['library'] is None}
report={'schema':'x.validation.saved-seed-action-inventory/1','completed':True,'addon_registered':False,
    'full_scene_opened':False,'artist_opened_or_written':False,'input_pins':pins,'expected_live_memory':expected,
    'saved_available_action_names':available,'loaded_action_details':loaded,
    'missing_original_local_names':sorted(expected_local-loaded_local),'unexpected_loaded_local_names':sorted(loaded_local-expected_local),
    'qualification':'Appended action-only data, not full scene/user count equivalence; native no-addon diagnosis only.'}
assert all(sha(row['path'])==row['sha256'] for row in pins.values())
report['input_files_unchanged']=True
with out.open('x',encoding='utf-8') as stream:
    stream.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SAVED_SEED_ACTION_INVENTORY '+json.dumps({'report':str(out),'sha256':sha(out),'completed':True}))
