from pathlib import Path
import hashlib, json, zipfile

repo = Path(r'D:\MyRepository\Blender-addons-by-Randy')
evidence = Path(__file__).resolve().parent
baseline = repo/'dist/character_designer-0.77.23.zip'
base_sha = hashlib.sha256(baseline.read_bytes()).hexdigest()
assert base_sha == 'dd2d4903a7c45b5ed7a3b442e132dd04d13e34fbca099864eaaada08e0165f1e'
root = evidence/'release_07724'/'character_designer'
root.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(baseline) as archive:
    for name in archive.namelist():
        relative = Path(name).relative_to('character_designer')
        if not relative.parts or name.endswith('/'):
            continue
        destination = root/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(name))
    init = archive.read('character_designer/__init__.py')
    assert init.count(b'"version": (0, 77, 23)') == 1
    (root/'__init__.py').write_bytes(init.replace(b'"version": (0, 77, 23)', b'"version": (0, 77, 24)'))
owned = ['unity_animation.py', 'unity_animation_controls.py', 'unity_animation_dress.py',
         'animation_worklist.py', 'animation_worklist_ui.py', 'animation_worklist_target.py',
         'limb_ik.py', 'root_control.py', 'torso_controls.py', 'spine_ik_fk.py',
         'eye_controls.py', 'foot_controls.py', 'bone_display.py', 'bone_collections.py']
overlays = {}
for name in owned:
    payload = (repo/'addons/character_designer'/name).read_bytes()
    (root/name).write_bytes(payload)
    overlays[name] = hashlib.sha256(payload).hexdigest()
files = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
         for path in root.rglob('*') if path.is_file() and '__pycache__' not in path.parts
         and path.suffix not in {'.pyc','.pyo'}}
manifest = {'schema_version':1,'module':'character_designer','version':'0.77.24',
            'source_root':str(root),'files':files,'source_provenance':{
                'baseline_release':str(baseline),'baseline_sha256':base_sha,
                'canonical_overlays':overlays,'init_version_only':True,
                'scope':'Direct original scene/Rig Worklist adoption, exact static Dress delegation and persistent recovery.',
                'excluded':'Unrelated pending Dress drafts, export changes and text fixes in canonical repository.'}}
(evidence/'release_projection_07724.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'root':str(root),'files':len(files),'overlays':overlays},indent=2))
