import argparse,hashlib,importlib,json,os,sys,time,traceback
from pathlib import Path
import bpy,addon_utils
p=argparse.ArgumentParser();p.add_argument('--source-sha256',required=True);p.add_argument('--output-root',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.output_root)
assert bpy.app.background and not bpy.data.filepath
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==a.source_sha256
root=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/package_c1e59f7f/source/character_designer')
manifest=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/package_c1e59f7f/python_projection.json')
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'
for leaf,h in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():assert hashlib.sha256((root/leaf).read_bytes()).hexdigest()==h
sys.path.insert(0,str(root.parent));importlib.invalidate_caches()
module=importlib.import_module('character_designer');assert Path(module.__file__).resolve().is_relative_to(root)
errors=[]
def error(ex):errors.append({'type':type(ex).__name__,'message':str(ex),'traceback':''.join(traceback.format_exception(ex))})
started=time.monotonic();enabled=addon_utils.enable('character_designer',default_set=False,persistent=False,handle_error=error)
report={'schema':'x.validation.standard-registration-diagnostic/1','completed':True,'pid':os.getpid(),'addon_enable_returned_module':enabled is not None,'root_module_present':'character_designer' in sys.modules,'runtime_enabled':bool(getattr(module,'__addon_enabled__',False)),'errors':errors,'elapsed_seconds':time.monotonic()-started,'scene_opened_or_saved':False,'source_sha256':a.source_sha256,'manifest_sha256':'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'}
with (out/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=True))
