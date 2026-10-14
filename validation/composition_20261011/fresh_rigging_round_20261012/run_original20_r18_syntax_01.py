"""Actual R18 syntax-only check; imports no target modules and runs no tests."""
import ast, hashlib, json
from pathlib import Path
INPUTS = [
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py",
    "sha256": "f2f6e1693c7fab0cb8ffaa479a3af19f5c4392f66119844183c32a61f91b1473",
    "bytes": 37288
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_rigging.py",
    "sha256": "b3348175c63cf1d0d29ffb184bd7eb5123c2e4ca274eb5b39893f94658a5019f",
    "bytes": 109020
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\__init__.py",
    "sha256": "81b276e22fb170f860a08510db7db2bc26508fb3a711bc8e291b328a59fe71a9",
    "bytes": 355944
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\forearm_twist.py",
    "sha256": "54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408",
    "bytes": 97739
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_original_inputs_ui.py",
    "sha256": "38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426",
    "bytes": 15250
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_worklist_ui.py",
    "sha256": "24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067",
    "bytes": 43636
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_composition_weapon.py",
    "sha256": "881dc4bfd28e0830628835e3329f77e72f458b0c2ae139033c0ecc618ffa47a1",
    "bytes": 41160
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_character_composition_weapon_ownership.py",
    "sha256": "c1203ebdb0f32a933106eea4bad03935a5b13770711cda65fd5f272554d4b7f9",
    "bytes": 15199
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_recovery.py",
    "sha256": "67b4f45988d9eddab0e54b0eeb886cbc32f41a8d2beb68baf95e49730811524b",
    "bytes": 70235
  },
  {
    "path": "D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_weapon.py",
    "sha256": "5e79a45de2186a66a7dd11a5701ab6be1514e00fbaed20585a6127b92fc174a1",
    "bytes": 10858
  },
  {
    "path": "D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\certify_original_legacy_base_clock_latest_saved.py",
    "sha256": "9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155",
    "bytes": 24915
  }
]
OUT = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/r18_syntax_01')
OUT.mkdir(exist_ok=False)
lines = []
for row in INPUTS:
    source = Path(row['path'])
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256'] and len(raw) == row['bytes'], str(source)
    compile(ast.parse(raw, filename=str(source)), str(source), 'exec')
    lines.append('AST_COMPILE_PASS ' + source.name + ' ' + row['sha256'])
lines.append('SOURCE_ONLY files=11 target_imports=0 tests=0 native=0')
raw = ('\n'.join(lines) + '\n').encode('utf-8')
log = OUT / 'syntax.txt'
log.write_bytes(raw)
result = {'result':'PASS','exit_code':0,'target_imports':0,'source_files':11,'input_pins':{row['path']:row['sha256'] for row in INPUTS},'raw_log':{'path':str(log.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}}
(OUT / 'syntax_receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
