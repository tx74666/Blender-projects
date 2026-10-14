"""Run the shipped publication phase on immutable verified worker output.

Disposable factory-startup Blender only. No model load/pose/save, worker launch,
Unity operation or Assets write. The shipped _publish creates the manifest and
publishes to a new X evidence directory after its normal ownership checks.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback
from types import SimpleNamespace

import bpy

HERE = Path(__file__).resolve().parent
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
CANDIDATE = HERE / 'forearm_roll_07712_runtime/character_designer'
PROJECTION = CANDIDATE.parent / 'release_projection_07712.json'
PROOF = HERE / 'final_export_07712/real_export_after.json'
SIDECAR_PROOF = HERE / 'final_export_07712/forearm_sidecar_verification.json'
ROUNDTRIP = HERE / 'final_fbx_roundtrip_07712.json'
CAPTURE = HERE / 'real_export_after_07712/capture_report.json'
JOB = HERE / 'real_export_after_07712/job.json'
ARTIST = HERE.parent.parent / 'X.blend'
FINAL_ARTIST_SHA = '17a9312f6ec7f3ec0d709ca89fb2bc918aa94856af0fef544c3ce6ca83bded86'
STAGE = HERE / 'publication_stage_07712'
DESTINATION = HERE / 'published_export_07712'
OUT = HERE / 'publication_receipt_07712.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


inputs = {str(path): sha(path) for path in [PROOF, SIDECAR_PROOF, ROUNDTRIP, CAPTURE, JOB, ARTIST, PROJECTION]}
report = {'status': 'STARTED', 'publication_method': 'shipped unity_export._publish',
          'inputs_before': inputs, 'model_loaded': False, 'model_saved': False,
          'worker_launched': False, 'Unity_invoked': False, 'Unity_Assets_written': False}
try:
    assert bpy.app.background and not bpy.data.filepath, 'Require disposable factory-startup Blender.'
    assert not STAGE.exists() and not DESTINATION.exists(), 'Refuse reuse of publication output.'
    assert sha(ARTIST) == FINAL_ARTIST_SHA
    sys.path.insert(0, str(REPOSITORY / 'tools'))
    from release_projection import load_source
    source = load_source('character_designer', PROJECTION, root=REPOSITORY)
    assert source.version == '0.77.12' and source.root == CANDIDATE.resolve()
    sys.path.insert(0, str(CANDIDATE.parent))
    import character_designer
    from character_designer import unity_export
    assert Path(character_designer.__file__).resolve().parent == CANDIDATE.resolve()
    assert Path(unity_export.__file__).resolve() == (CANDIDATE / 'unity_export.py').resolve()

    proof, sidecar, roundtrip, capture, specification = map(read, [PROOF, SIDECAR_PROOF, ROUNDTRIP, CAPTURE, JOB])
    assert proof['passed'] and sidecar['status'] == 'PASS' and roundtrip['passed'] and capture['passed']
    assert roundtrip['raw_fbx']['passed'] and roundtrip['input_files_unchanged']
    assert capture['source_file_unchanged'] and capture['captured_data_unchanged']
    assert capture['input_sha256'] == FINAL_ARTIST_SHA
    assert capture['job_sha256'] == sha(JOB)
    assert proof['input_job_sha256'] == sha(JOB)
    worker_stage = Path(proof['fbx_path']).resolve().parent
    result = copy.deepcopy(proof['export_result'])
    assert result['ok'] and result['files'] and specification['filename'] in result['files']
    assert proof['fbx_sha256'] == sidecar['fbx_sha256'] == sha(worker_stage / specification['filename'])
    assert sidecar['staged_file_sha256'].keys() == dict.fromkeys(result['files']).keys()
    assert result['forearm_correction']['meshes'] == ['Cosha']
    assert result['hair_motion']['active'] is True
    before_files = {}
    for relative in result['files']:
        verified = unity_export._safe_file(worker_stage, relative)
        assert verified.is_file() and verified.suffix.casefold() != '.meta'
        before_files[relative] = sha(verified)
        assert before_files[relative] == sidecar['staged_file_sha256'][relative]
    STAGE.mkdir()
    for relative in result['files']:
        target = unity_export._safe_file(STAGE, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(unity_export._safe_file(worker_stage, relative), target)
        assert sha(target) == before_files[relative]

    job = {'directory': DESTINATION, 'stage': STAGE,
           'filename': specification['filename'], 'asset_id': specification['asset_id'],
           'manifest_hash': None, 'prior': None,
           'rig': SimpleNamespace(name=specification['rig']),
           'objects': specification['objects'], 'hair_motion': specification['hair_motion']}
    receipt = unity_export._publish(job, result)
    manifest_path = Path(receipt['report_path'])
    manifest = read(manifest_path)
    assert manifest_path == DESTINATION / 'Cosha.cdesigner.json'
    assert manifest['schema'] == unity_export.SCHEMA
    assert manifest['asset_id'] == specification['asset_id'] and manifest['source_rig'] == specification['rig']
    assert manifest['filename'] == specification['filename'] and manifest['files'] == before_files
    assert manifest['forearm_correction'] == result['forearm_correction']
    assert manifest['hair_motion'] == result['hair_motion']
    assert len(manifest['source_rigs']['CoshaRig']) == 217
    assert not any(path.suffix.casefold() == '.meta' for path in DESTINATION.rglob('*'))
    published = {relative: sha(unity_export._safe_file(DESTINATION, relative)) for relative in before_files}
    assert published == before_files
    published[manifest_path.name] = sha(manifest_path)
    assert unity_export._previous(DESTINATION, specification['filename'], specification['asset_id']) == manifest
    assert all(sha(unity_export._safe_file(worker_stage, relative)) == expected for relative, expected in before_files.items())
    report.update(status='PASS', native_publication_receipt=receipt,
                  source_root=str(CANDIDATE), projection_sha256=source.projection_sha256,
                  publisher_source_sha256=sha(CANDIDATE / 'unity_export.py'),
                  destination=str(DESTINATION), published_file_sha256=published,
                  manifest=str(manifest_path), manifest_sha256=sha(manifest_path),
                  fbx_sha256=published[specification['filename']],
                  asset_id=manifest['asset_id'], forearm_meshes=manifest['forearm_correction']['meshes'],
                  hair_active=manifest['hair_motion']['active'], retained_bones=217,
                  original_worker_outputs_unchanged=True, blender=bpy.app.version_string)
except Exception:
    report.update(status='FAIL', error=traceback.format_exc())
    raise
finally:
    report['all_inputs_unchanged'] = all(sha(Path(path)) == expected for path, expected in inputs.items())
    if report['status'] == 'PASS' and not report['all_inputs_unchanged']:
        report['status'] = 'FAIL'
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('OFFICIAL_PUBLICATION_' + report['status'], str(OUT), flush=True)
