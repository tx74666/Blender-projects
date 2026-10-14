"""Read-only JSON/FBX verification of the final 0.77.12 staged Export.

This ordinary-Python check mirrors the frozen Unity importer's data guards.
It proves capture/FBX/sidecar binding, not Unity import or Animator behavior.
"""
import hashlib
import json
import math
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
CAPTURE = HERE / 'real_export_after_07712'
EXPORT = HERE / 'final_export_07712/real_export_after.json'
LIVE = PROJECT / 'validation/forearm_twist_fix_20261009'
FINAL_SHA = '17a9312f6ec7f3ec0d709ca89fb2bc918aa94856af0fef544c3ce6ca83bded86'
OUT = EXPORT.parent / 'forearm_sidecar_verification.json'
report = {'status': 'STARTED', 'writes_to_Unity': False,
          'Unity_import_or_Animator_verified': False, 'saved_blend': False}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        assert name not in result, 'Duplicate JSON key: ' + name
        result[name] = value
    return result


def read(path):
    def invalid_constant(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def vector(value):
    assert isinstance(value, dict) and set(value) == {'x', 'y', 'z'}
    assert all(finite(v) for v in value.values())


def index(value, count):
    assert type(value) is int and 0 <= value < count


def main():
    capture, job, exported = read(CAPTURE / 'capture_report.json'), read(CAPTURE / 'job.json'), read(EXPORT)
    native, live, layout = (read(LIVE / name) for name in
                            ('fresh_actual_report.json', 'live_fix_receipt.json', 'layout_restore_receipt.json'))
    manifest_path = HERE / 'forearm_roll_07712_runtime/release_projection_07712.json'
    manifest = read(manifest_path)
    # Literal below is the approved 152-file projection used by the saved artist
    # operation; keep the complete hash rather than trusting a version label.
    projection_sha = '2c6e63bfe3919a2ed224da69aede0456315fcde35c49db187fcdf5872b8e34a6'
    assert sha(manifest_path) == projection_sha == native['projection_sha256'] == live['projection_sha256']
    assert manifest['version'] == '0.77.12' and len(manifest['files']) == 152
    runtime = HERE / 'forearm_roll_07712_runtime/character_designer'
    assert Path(capture['runtime']).resolve() == runtime.resolve()
    assert all(sha(runtime / relative) == expected for relative, expected in manifest['files'].items())
    assert capture['passed'] and capture['captured_data_unchanged'] and capture['source_file_unchanged']
    assert not capture['saved_input_blend'] and not capture['worker_started'] and not capture['Unity_started']
    assert capture['input_sha256'] == layout['artist_sha256'] == FINAL_SHA == sha(PROJECT / 'X.blend')
    assert Path(capture['input_blend']).resolve() == (PROJECT / 'X.blend').resolve()
    assert capture['snapshot_sha256'] == sha(CAPTURE / 'character.blend') == exported['input_sha256']
    assert capture['job_sha256'] == sha(CAPTURE / 'job.json') == exported['input_job_sha256']
    assert exported['passed'] and exported['source_file_unchanged'] and not exported['saved_blend']
    assert exported['worker_sha256'] == manifest['files']['unity_export_worker.py']
    assert exported['checks'] and all(c['passed'] and not c['missing'] and not c['mismatches'] for c in exported['checks'])
    result = exported['export_result']
    assert result['ok'] and result['forearm_correction']['meshes'] == ['Cosha']
    assert capture['forearm_meshes'] == ['Cosha'] and set(job['forearm']) == {'Cosha'}
    owned = [native['records'][side]['key'] for side in ('L', 'R')]
    assert capture['owned_keys']['Cosha'] == job['owned_keys']['Cosha'] == owned
    artists = native['original_keys'][1:]
    assert result['shape_keys']['Cosha'] == artists
    assert [s['name'] for s in capture['shape_inputs']['Cosha']['artists']] == artists
    old_keys = {'CD Forearm Twist.L', 'CD Forearm Twist.R', 'CD Forearm Twist.L.001', 'CD Forearm Twist.R.001'}
    unregistered = [k for k in capture['unregistered_prefixed_keys'] if k['object'] == 'Cosha']
    assert {k['key'] for k in unregistered} == old_keys
    assert all(k['value'] == 0 and not k['mute'] and k['treated_as_artist_shape_by_official_export'] for k in unregistered)
    fbx = Path(exported['fbx_path']).resolve()
    assert fbx.is_relative_to(EXPORT.parent.resolve()) and fbx.name == job['filename']
    assert sha(fbx) == exported['fbx_sha256']
    sidecar = fbx.parent / result['forearm_correction']['file']
    assert sidecar.resolve().parent == fbx.parent and sidecar.name in result['files']
    payload = read(sidecar)
    assert payload['schema'] == 'cdesigner.forearm/1' and payload['fbx'] == fbx.name
    assert payload['fbxSha256'] == sha(fbx) and len(payload['meshes']) == 1
    entry = payload['meshes'][0]
    captured = job['forearm']['Cosha']
    assert all(entry[field] == value for field, value in captured.items()), 'Sidecar changed captured correction data.'
    assert entry['objectName'] == 'Cosha' and entry['sourceVertexCount'] == 3658
    assert entry['sourceTopology'] == native['records']['L']['topology'] == native['records']['R']['topology']
    assert type(entry['vertexCount']) is int and entry['vertexCount'] >= 4
    assert entry['vertexCount'] == result['meshes']['Cosha']['vertices'] == len(entry['positions'])
    index(entry['idUvChannel'], 8)
    for point in entry['positions']:
        vector(point)
    assert [s['name'] for s in entry['sides']] == ['L', 'R']
    for side in entry['sides']:
        record = native['records'][side['name']]
        assert side['lowerBone'] == record['chain'][1] and side['handBone'] == record['chain'][2]
        assert side['enabled'] and side['lowerBone'] != side['handBone']
        vector(side['axis']); vector(side['pivot'])
        assert sum(v*v for v in side['axis'].values()) > 1e-12
    sources, used = entry['sources'], set()
    assert sources
    for sample in sources:
        index(sample['vertex'], entry['sourceVertexCount']); index(sample['side'], len(entry['sides']))
        assert sample['vertex'] not in used
        used.add(sample['vertex'])
        vector(sample['point'])
        assert all(finite(sample[k]) and 0 <= sample[k] <= 1 for k in
                   ('ratio', 'influence', 'lowerWeight', 'handWeight'))
        assert sample['lowerWeight'] + sample['handWeight'] <= 1.0001
    shape_names = set()
    for shape in entry['shapes']:
        assert shape['name'] in artists and shape['name'] not in shape_names
        shape_names.add(shape['name'])
        assert len(shape['deltas']) == len(sources)
        for delta in shape['deltas']:
            vector(delta)
    destinations = set()
    assert entry['stencils']
    for row in entry['stencils']:
        index(row['vertex'], entry['vertexCount'])
        assert row['vertex'] not in destinations
        destinations.add(row['vertex'])
        assert row['sources'] and len(row['sources']) == len(row['weights'])
        assert len(set(row['sources'])) == len(row['sources'])
        for source in row['sources']:
            index(source, len(sources))
        assert all(finite(weight) and weight >= 0 for weight in row['weights'])
        assert 0 < sum(row['weights']) <= 1.001
    assert finite(entry['stencilCheckMaxError']) and entry['stencilCheckMaxError'] <= 3e-6
    file_hashes = {}
    for name in result['files']:
        path = (fbx.parent / name).resolve()
        assert path.is_relative_to(fbx.parent)
        file_hashes[name] = sha(path)
    assert sha(PROJECT / 'X.blend') == FINAL_SHA
    report.update(status='PASS', final_artist_sha256=FINAL_SHA, projection_sha256=projection_sha,
                  manifest_file_count=152, fbx=str(fbx), fbx_sha256=sha(fbx), sidecar=str(sidecar),
                  sidecar_sha256=sha(sidecar), staged_file_sha256=file_hashes,
                  preserved_original_shape_keys=artists, owned_correction_keys_excluded=owned,
                  sides=['L', 'R'], source_sample_count=len(sources), baked_vertex_count=entry['vertexCount'],
                  stencil_count=len(entry['stencils']), stencil_check_max_error=entry['stencilCheckMaxError'],
                  retained_bone_count={c['rig']: c['retained_count'] for c in exported['checks']},
                  full_captured_payload_preserved=True, Unity_importer_structural_guards_pass=True)


try:
    main()
except Exception:
    report.update(status='FAIL', error=traceback.format_exc())
    raise
finally:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix('.json.writing')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(OUT)
    print('FINAL_FOREARM_SIDECAR_' + report['status'], str(OUT), flush=True)
