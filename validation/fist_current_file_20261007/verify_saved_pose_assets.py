"""Read only the saved Action assets; do not load or write the artist scene."""
import ast
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder / 'approved_release_0772' / 'addons'))
from character_designer import animation_retarget

tree = ast.parse((folder / 'import_and_backup.py').read_text(encoding='utf-8'))
definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name in {'fingerprint', 'preview', 'asset_details'}]
assert len(definitions) == 3
exec(compile(ast.Module(body=definitions, type_ignores=[]), 'saved_asset_fingerprint', 'exec'))

artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
expected_artist_hash = '994c1edd4c9bfc338726e9dfa23ee5d76b3b074da2523e860bbf8d3a9e044a95'
proof = json.loads((folder / 'asset_file_verification.json').read_text(encoding='utf-8'))
library = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions')
source_hashes = {'Fist': proof['fist_source_sha256'],
                 'Arm Flat': proof['external_arm_sha256']}

def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def plain(value):
    return json.loads(json.dumps(value, ensure_ascii=False))

assert file_hash(artist) == expected_artist_hash, 'Artist file changed before verification'
assert not bpy.data.filepath
scene_counts = {name: len(getattr(bpy.data, name))
                for name in ('scenes', 'objects', 'armatures', 'meshes', 'materials')}
with bpy.data.libraries.load(str(artist), link=False) as (available, requested):
    assert {'Fist', 'Arm Flat'}.issubset(available.actions), available.actions
    requested.actions = ['Fist', 'Arm Flat']
assert scene_counts == {name: len(getattr(bpy.data, name)) for name in scene_counts}
assert not bpy.data.filepath, 'Artist scene was unexpectedly opened'

assets = []
for name, action in zip(('Fist', 'Arm Flat'), requested.actions):
    key = 'fist' if name == 'Fist' else 'arm'
    assert action is not None and action.name == name
    assert action.library is None and action.asset_data is not None
    assert action.use_fake_user, name
    assert plain(fingerprint(action)) == proof[key + '_data'], name + ': channels or metadata differ'
    assert preview(action) == proof[key + '_preview'], name + ': thumbnail differs'
    expected_asset = dict(proof[key + '_asset'])
    if name == 'Arm Flat':
        expected_asset['catalog_id'] = proof['fist_asset']['catalog_id']
    assert asset_details(action) == expected_asset, name + ': asset details differ'
    assert file_hash(library / (name + '.asset.blend')) == source_hashes[name]
    assets.append({'name': name, 'asset_marked': True, 'fake_user': True,
                   'channel_count': len(proof[key + '_data']['curves']),
                   'channels_and_metadata_verified': True,
                   'preview': preview(action), 'asset_details': asset_details(action),
                   'external_path': str(library / (name + '.asset.blend')),
                   'external_sha256': source_hashes[name]})

assert file_hash(artist) == expected_artist_hash, 'Artist file changed during verification'
receipt = {'passed': True, 'artist': str(artist), 'artist_sha256': expected_artist_hash,
           'artist_bytes': artist.stat().st_size, 'artist_scene_not_opened': True,
           'scene_datablock_counts_unchanged': True, 'artist_file_unchanged': True,
           'external_files_unchanged': True, 'assets': assets,
           'blender_version': bpy.app.version_string,
           'blender_build': bpy.app.build_hash.decode()}
(folder / 'saved_asset_verification.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('SAVED_POSE_ASSETS_VERIFIED: Fist + Arm Flat, channels + metadata + thumbnails')
