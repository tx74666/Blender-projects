"""Export and reimport one stopped saved-X candidate in a disposable Blender.

Use --background --factory-startup --disable-autoexec and explicitly open the
CD_HAIR_EXPORT_CANDIDATE file before --python this script. No child Blender,
full Character Designer registration, candidate save, artist save or Unity
write is performed. Partial Validation evidence is retained on failure.
"""
import collections
import ctypes
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

import bpy

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/addons')
from character_designer import bl_info
from character_designer import hair_bones_rig as hair, hair_strand_registry as registry
from character_designer import hair_motion_profiles as profiles, hair_motion_export as sidecar
from character_designer import hair_wiggle_adapter as preview
from character_designer import unity_export as exporter, unity_export_worker as worker, unity_forearm

EXPECTED_UID = '331afdb7e5154ae1aaa39603a4f61768'
EXPECTED_PORTABLE_RAW = 'c0a05c28207cfefb5e441686ee14b56eb5da91495bc2fe2f81a97ce9f576e4c2'
FILENAME = 'Cosha_HairValidation.fbx'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _windows_argv(command):
    """Tokenize the native Windows command line without exposing it in evidence."""
    require(isinstance(command, str) and command.strip(),
        'Another Blender/Unity process has no readable command line; cannot classify.')
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    split = shell32.CommandLineToArgvW
    split.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    split.restype = ctypes.POINTER(ctypes.c_wchar_p)
    release = kernel32.LocalFree
    release.argtypes = [ctypes.c_void_p]
    release.restype = ctypes.c_void_p
    count = ctypes.c_int()
    allocated = split(command, ctypes.byref(count))
    require(bool(allocated), 'Windows command-line parsing failed; cannot classify another process.')
    try:
        return [allocated[index] for index in range(count.value)]
    finally:
        require(not release(ctypes.cast(allocated, ctypes.c_void_p)),
            'Windows command-line argument allocation could not be released.')


def _process_identity(name, command):
    """Classify exact argv flags; retain only a native import-worker identity."""
    tokens = _windows_argv(command)[1:]
    flags = [token.lower() for token in tokens]
    if name.lower() == 'blender.exe':
        return {'classification': 'background_task' if any(
            token in {'--background', '-b'} for token in flags) else 'foreground_GUI'}
    require(name.lower() == 'unity.exe', 'Resource probe returned an unexpected process type.')
    def values(option):
        return [tokens[index + 1] if index + 1 < len(tokens) else ''
            for index, token in enumerate(flags) if token == option]
    labels, parents = values('-name'), values('-parentpid')
    worker_labels = [label for label in labels
        if re.fullmatch(r'AssetImportWorker(?:HW)?\d*', label, re.IGNORECASE)]
    # Unity's native worker CLI can repeat -name with the secondary AssetImport
    # role. Require one unambiguous worker identity and reject all other roles.
    worker_names = set(worker_labels)
    persistent = ('-executemethod' not in flags and len(worker_names) == 1
        and all(label in worker_names or label == 'AssetImport' for label in labels)
        and parents and all(re.fullmatch(r'[0-9]+', value) for value in parents)
        and len({int(value) for value in parents}) == 1 and int(parents[0]) > 0)
    if persistent:
        return {'classification': 'persistent_asset_import_worker',
            'worker_name': worker_labels[0], 'parent_pid': int(parents[0])}
    return {'classification': 'background_task' if any(
        token in {'-batchmode', '-executemethod'} for token in flags) else 'foreground_GUI'}


def resource_gate():
    """Check current RAM and recognizable competing background jobs, read-only."""
    require(os.name == 'nt', 'This machine-specific validation needs the Windows resource probe.')
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ('total_phys', 'available_phys', 'total_page',
                'available_page', 'total_virtual', 'available_virtual', 'available_extended')]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)), 'Memory probe failed.')
    require(status.available_phys >= 200 * 1024 * 1024, 'Less than 200 MiB physical RAM is available; do not add export work.')
    query = """@(Get-CimInstance Win32_Process -Filter "Name = 'blender.exe' OR Name = 'Unity.exe'" |
        Select-Object ProcessId,Name,CommandLine) | ConvertTo-Json -Compress"""
    checked = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
        capture_output=True, text=True, timeout=20, check=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    processes = json.loads(checked.stdout) if checked.stdout.strip() else []
    if isinstance(processes, dict):
        processes = [processes]
    other_gui, background, importer_workers = [], [], []
    idle_proof = os.environ.get('CD_HAIR_UNITY_IDLE_CONFIRMED', '').strip()
    for process in processes:
        if process['ProcessId'] == os.getpid():
            continue
        command = process.get('CommandLine')
        require(command is not None, 'Another Blender/Unity process cannot be classified; keep heavy runs serial.')
        identity = _process_identity(process['Name'], command)
        if identity['classification'] == 'persistent_asset_import_worker':
            require(8 <= len(idle_proof) <= 256,
                'Persistent Unity import workers require explicit caller idle-scheduling evidence in CD_HAIR_UNITY_IDLE_CONFIRMED.')
            importer_workers.append({'name': process['Name'], 'pid': process['ProcessId'],
                **identity, 'idle_source': 'explicit caller scheduling proof; not inferred from process flags'})
            continue
        (background if identity['classification'] == 'background_task' else other_gui).append(
            {'name': process['Name'], 'pid': process['ProcessId'], **identity})
    require(not background, 'Another Blender background/Unity batch job is running; keep heavy validation serial.')
    return {'available_physical_bytes': status.available_phys, 'memory_load_percent': status.load,
            'competing_background_jobs': background, 'other_GUI_processes_preserved': other_gui,
            'persistent_Unity_import_workers_preserved': importer_workers,
            'Unity_idle_scheduling_proof': idle_proof if importer_workers else None,
            'probe_scope': 'Windows current RAM + recognizable background tasks; persistent import workers require explicit caller idle proof; foreground activity is not inferred from flags'}


def exact_pair(data, first_order, other_order):
    by_order = {item['order']: item for item in data['strands']}
    first, other = by_order[first_order], by_order[other_order]
    require(first['mirror_id'] == other['strand_id'] and other['mirror_id'] == first['strand_id']
        and first['pair_id'] == other['pair_id'] and first['pair_proof'] == other['pair_proof']
        and first['pair_proof'] in {'TOPOLOGY', 'GEOMETRY', 'GRAPH', 'MIRROR'},
        'The explicit preview pair is missing its current reciprocal proof.')
    return [first['strand_id'], other['strand_id']]


def reopen_proof(source, candidate, data, effective, first_pair, long_pair):
    """Compare the reopened candidate with its passing Head-local evidence."""
    evidence = Path(os.environ.get('CD_HAIR_EXPORT_PREVIEW_REPORT',
        str(DIRECTORY / 'real_hair_preview_validation_51_headlocal3.json'))).resolve()
    require(evidence.is_file() and evidence.is_relative_to(DIRECTORY.resolve()), 'Use the owned passing Head-local preview report.')
    saved = json.loads(evidence.read_text(encoding='utf8'))
    require(saved.get('ok') is True and saved.get('strictbaseline') is True
        and saved.get('simulation_baked') is False and saved['source_uid'] == EXPECTED_UID
        and Path(saved['recoverypath']).resolve() == candidate, 'The saved preview evidence does not prove this exact stopped candidate.')
    require(saved['input']['kind'] != 'root_armature_world_rotation', 'Use the passing actual Head-local preview candidate.')
    require(saved['topology'] == data['topology']
        and saved['firstpair_ids'] == first_pair and saved['longpair_ids'] == long_pair,
        'Reopening changed source topology or the explicit proven pair identities.')
    require(saved['stages'][0]['effective_inputs'] == effective, 'Reopening changed effective saved Hair motion profiles.')
    native = {item['strand_id']: item for item in data['strands']}
    all_stage = next(item for item in saved['stages'] if item['name'] == 'all_32_synchronized')
    by_id = {item['strand_id']: item for item in all_stage['chains']}
    require(set(native) == set(by_id) and len(native) == 32
        and all(len(item['bones']) == 4 for item in native.values()),
        'Reopening changed the exact 32 strand IDs or four-segment topology.')
    for strand_id, item in native.items():
        before = by_id[strand_id]
        require(item['order'] == before['order'] and item['pair_id'] == before['pair_id']
            and item['pair_proof'] == before['pair_proof'] and effective[strand_id]['group'] == before['group'],
            'Reopening changed a saved strand order, pair proof or motion group.')
    require(saved['final_fingerprint']['portable_sha256'] == EXPECTED_PORTABLE_RAW,
            'The passing preview raw portable baseline differs from this explicitly reviewed candidate.')
    spec = importlib.util.spec_from_file_location('_cd_real_hair_raw_fingerprint',
        DIRECTORY / 'validate_real_hair_preview.py')
    inspector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)  # Main is not invoked; no backend, simulation or save.
    fingerprint = inspector.asset_fingerprint(source)
    require(fingerprint['portable_sha256'] == EXPECTED_PORTABLE_RAW,
            'Reopened raw mesh/UV/weights/material/Rest/Action portable fingerprint differs.')
    return {'ok': True, 'preview_report': str(evidence), 'source_uid': EXPECTED_UID,
        'strand_ids': sorted(native), 'first_pair_ids': first_pair, 'long_pair_ids': long_pair,
        'topology': data['topology'], 'profiles_exact': True, 'IDs_pairs_groups_exact': True,
        'counts': {'strands': 32, 'segments_per_strand': 4, 'Hair_segments': 128},
        'raw_portable_fingerprint': fingerprint}


class Delegate:
    """Observe one module call while preserving real native RNA/operators."""
    def __init__(self, target, **overrides):
        self.target, self.overrides = target, overrides

    def __getattr__(self, name):
        return self.overrides[name] if name in self.overrides else getattr(self.target, name)


def observed_worker(specification, report):
    original = worker.bpy
    def actual_fbx(**options):
        observed = {key: sorted(value) if isinstance(value, set) else value for key, value in options.items()}
        report['actual_fbx_export_options'] = observed
        require(all(options.get(key) is False for key in
                    ('bake_anim', 'bake_anim_use_nla_strips', 'bake_anim_use_all_actions')),
                'Ordinary rest-model export must not bake animation or Hair simulation.')
        return bpy.ops.export_scene.fbx(**options)
    worker.bpy = Delegate(bpy, ops=Delegate(bpy.ops, export_scene=Delegate(bpy.ops.export_scene, fbx=actual_fbx)))
    try:
        return worker.export_job(specification)
    finally:
        worker.bpy = original


def publish_local(job, result, backup_directory):
    original = exporter.bpy
    resource = bpy.utils.user_resource
    def owned_resource(kind, *, path='', create=False):
        if kind == 'DATAFILES' and path == 'character_designer/export_backups':
            backup_directory.mkdir(exist_ok=True)
            return str(backup_directory)
        return resource(kind, path=path, create=create)
    exporter.bpy = Delegate(bpy, utils=Delegate(bpy.utils, user_resource=owned_resource))
    try:
        return exporter._publish(job, result)
    finally:
        exporter.bpy = original


def check_sidecar(payload, capture, result, main_name, asset_id):
    data, effective = capture['registry'], capture['profiles']
    require(payload['asset_id'] == asset_id and payload['source_uid'] == EXPECTED_UID
        and payload['simulation_baked'] is False, 'Sidecar identity/bake state differs.')
    require(payload['registry']['topology'] == data['topology'] and len(payload['strands']) == 32,
            'Sidecar source topology/inventory differs.')
    by_id = {item['strand_id']: item for item in data['strands']}
    retained = result['source_rigs'][capture['rig']]
    expected_names = [name for item in data['strands'] for name in item['bones']]
    require(len(expected_names) == 128 and len(set(expected_names)) == 128
        and set(expected_names).issubset(retained), 'The real worker omitted an owned Hair bone.')
    mapping = ({name: name for name in expected_names} if capture['rig'] == main_name
               else result['accessory_bone_mapping'][capture['rig']])
    for item in payload['strands']:
        native, settings = by_id[item['strand_id']], effective[item['strand_id']]
        for key in ('chain_id', 'signature', 'order', 'pair_id', 'mirror_id', 'side', 'pair_proof', 'vertices', 'layers'):
            require(item[key] == native[key], 'Sidecar changed explicit identity/proof: ' + key)
        for key in ('vertex_map', 'boundary_map'):
            if key in item:
                require(item[key] == native[key], 'Sidecar changed complete mesh correspondence: ' + key)
        require(item['source_bones'] == native['bones'] and item['source_rest'] == native['rest'],
                'Sidecar changed ordered source bones/Rest.')
        require(item['exported_bones'] == [mapping[name] for name in native['bones']],
                'Sidecar binding differs from the actual retained/merged worker map.')
        require(item['group'] == settings['group'] and item['depth'] == settings['depth']
            and item['sync_mirror'] == settings['sync_mirror']
            and item['effective'] == {key: settings[key] for key in ('recovery', 'damping', 'gravity', 'stretch')},
            'Sidecar changed effective motion groups/settings.')
    return mapping


def empty_disposable_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.data.scenes.new('Hair FBX Import Roundtrip')
    bpy.context.window.scene = scene
    for other in tuple(bpy.data.scenes):
        if other != scene:
            bpy.data.scenes.remove(other)
    purged = bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    return purged


def roundtrip_fbx(filepath, payload, result, expected_parents, source_name, root):
    began = time.perf_counter()
    purged = empty_disposable_scene()
    resources = resource_gate()
    before_actions = {action.as_pointer() for action in bpy.data.actions}
    bpy.ops.preferences.addon_enable(module='io_scene_fbx')
    imported = bpy.ops.import_scene.fbx(filepath=str(filepath), use_anim=True)
    require('FINISHED' in imported, 'Native FBX import did not finish.')
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    require(len(rigs) == 1, 'The ordinary merged worker FBX did not import as one rig.')
    rig = rigs[0]
    names = [name for item in payload['strands'] for name in item['exported_bones']]
    require(len(names) == 128 and len(set(names)) == 128 and set(names).issubset(rig.data.bones.keys()),
            'Imported Hair Transform inventory is incomplete.')
    require(set(next(iter(result['rigs'].values()))).issubset(rig.data.bones.keys()),
            'Imported skeleton omitted a retained worker Transform.')
    roots = []
    for item in payload['strands']:
        ordered = [rig.data.bones[name] for name in item['exported_bones']]
        require(all(bone.parent == ordered[index - 1] for index, bone in enumerate(ordered) if index),
                'FBX import changed an explicit ordered Hair parent chain.')
        for bone in ordered:
            require((bone.parent.name if bone.parent else None) == expected_parents[bone.name],
                    'FBX import changed the real retained Hair attachment/parent.')
            require(all(math.isfinite(value) for row in bone.matrix_local for value in row),
                    'Imported Hair Rest matrix is nonfinite.')
        roots.append({'strand_id': item['strand_id'], 'root_transform': ordered[0].name,
                      'parent_transform': ordered[0].parent.name if ordered[0].parent else None})
    require(len(roots) == 32 and len({item['root_transform'] for item in roots}) == 32,
            'Imported strand roots are not 32 independent explicit paths.')
    by_name = {obj.name: obj for obj in meshes}
    require(set(by_name) == set(result['meshes']), 'Imported character mesh parts differ from actual worker output.')
    mesh_proofs = []
    for name, info in result['meshes'].items():
        obj = by_name[name]
        require(len(obj.data.vertices) == info['vertices'], 'FBX import changed worker vertex count: ' + name)
        keys = set(obj.data.shape_keys.key_blocks.keys()) if obj.data.shape_keys else set()
        require(set(info['shape_keys']).issubset(keys), 'FBX import omitted an exported artist BlendShape: ' + name)
        modifiers = [modifier for modifier in obj.modifiers if modifier.type == 'ARMATURE']
        require(not info['skinned'] or any(modifier.object == rig for modifier in modifiers),
                'Imported mesh lost its actual character skin binding: ' + name)
        mesh_proofs.append({'name': name, 'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
            'shape_keys': sorted(keys), 'armature_binding': [modifier.object.name for modifier in modifiers if modifier.object]})
    require(source_name in by_name, 'The collected Hair source did not survive as an FBX mesh.')
    hair_mesh = by_name[source_name]
    require(set(names).intersection(hair_mesh.vertex_groups.keys()), 'Hair mesh has no skin groups for the retained Hair skeleton.')
    for owner in rigs + meshes + [obj.data.shape_keys for obj in meshes if obj.data.shape_keys]:
        require(not owner.animation_data or (not owner.animation_data.action and not owner.animation_data.nla_tracks),
                'Ordinary rest FBX imported animation/NLA instead of an unbaked model.')
    require(not ({action.as_pointer() for action in bpy.data.actions} - before_actions),
            'Native FBX import created an Action: the ordinary rest export unexpectedly contains animation.')
    result_proof = {'ok': True, 'elapsed_seconds': time.perf_counter() - began, 'resources': resources,
        'orphans_purged_before_import': purged, 'imported_rig': rig.name, 'retained_bone_count': len(rig.data.bones),
        'strands': 32, 'Hair_transforms': 128, 'roots': roots, 'meshes': mesh_proofs,
        'missing_unweighted_Hair_vertex_groups': sorted(set(names) - set(hair_mesh.vertex_groups.keys())),
        'animation_import_enabled_for_detection': True, 'new_actions': 0, 'simulation_baked': False,
        'scope': 'Blender native FBX roundtrip binding/structure; Unity native Rest/physics equivalence remains unverified'}
    write_json(root / 'fbx_roundtrip.json', result_proof)
    return result_proof


def main():
    require(bpy.app.background, 'Run only in a disposable background Blender.')
    candidate = Path(os.environ['CD_HAIR_EXPORT_CANDIDATE']).resolve()
    require(candidate.is_file() and candidate.is_relative_to(DIRECTORY.resolve())
        and candidate.name.startswith('real_hair_preview_candidate_'), 'Use the explicit isolated stopped candidate in this Validation folder.')
    require(Path(bpy.data.filepath).resolve() == candidate, 'Blender must explicitly open the requested saved candidate.')
    asset_id = uuid.uuid4().hex
    root = (DIRECTORY / ('character_consumer_' + asset_id)).resolve()
    require(root.is_relative_to(DIRECTORY.resolve()) and not root.exists(), 'New validation ownership folder is not fresh.')
    root.mkdir()
    stage, directory = root / 'stage', root / 'published'
    stage.mkdir()
    report = {'ok': False, 'asset_id': asset_id, 'blender': bpy.app.version_string,
        'Character_Designer_version': '.'.join(map(str, bl_info['version'])),
        'candidate': str(candidate), 'owned_folder': str(root), 'artist_saved': False,
        'candidate_saved': False, 'Unity_written': False, 'child_Blender_started': False,
        'simulation_baked': False, 'phase': 'preflight',
        'limitations': ['Blender native FBX roundtrip is not Unity importer/physical-equivalence validation',
                        'Hair native baseline conversion/application is pending and must be explicit',
                        'foreground Unity import/compile inactivity is scheduled by the caller, not inferred from batch flags']}
    started = time.perf_counter()
    try:
        report['resources_before_worker'] = resource_gate()
        original_hash = file_hash(candidate)
        report['candidate_sha256_before'] = original_hash
        source = bpy.data.objects['Hair']
        data = registry.read(source, validate=True)
        require(data and data['source_uid'] == EXPECTED_UID and len(data['strands']) == 32
            and sum(len(item['bones']) for item in data['strands']) == 128, 'Candidate Hair strict source inventory differs.')
        record = profiles.read(source, registry=data)
        require(record is not None, 'Candidate has no saved Hair motion profile.')
        effective = profiles.effective_all(source, registry=data)
        first_pair, long_pair = exact_pair(data, 14, 16), exact_pair(data, 2, 5)
        report['reopen_proof'] = reopen_proof(source, candidate, data, effective, first_pair, long_pair)
        require(not preview.status()['active'], 'The saved candidate must be stopped before ordinary export.')
        main_rig = source.get(hair.RIG_KEY)
        require(main_rig.type == 'ARMATURE' and main_rig.parent is None,
                'This verified Cosha candidate must have the authoritative Hair/Main Rig as its root Object.')
        config = SimpleNamespace(extras=[], simple_materials=[], filename=FILENAME,
                                 directory=str(directory), asset_id=asset_id)
        collected = exporter.collect_character(bpy.context, main_rig, config)
        objects = collected['objects']
        require(source in objects and main_rig in objects, 'Ordinary character collection omitted the authoritative Hair source/rig.')
        capture = exporter._capture_hair_motion(objects)
        require(capture['registry'] == data and capture['profiles'] == effective
            and capture['rig'] == main_rig.name, 'Live Hair capture differs from strict candidate proof.')
        owned_keys = exporter._owned_keys(objects)
        forearm = {obj.name: unity_forearm.capture(obj) for obj in objects if obj.type == 'MESH' and obj.name in owned_keys}
        main_name, source_name = main_rig.name, source.name
        specification = {'objects': [obj.name for obj in objects], 'rig': main_name,
            'rigs': [obj.name for obj in objects if obj.type == 'ARMATURE'], 'filename': FILENAME,
            'stage': str(stage), 'asset_id': asset_id, 'unit_scale': bpy.context.scene.unit_settings.scale_length,
            'owned_keys': owned_keys, 'warnings': collected['warnings'], 'forearm': forearm,
            'hair_motion': capture, 'had_forearm': False, 'simple_materials': [], 'image_buffers': {}}
        write_json(root / 'job.json', specification)
        report.update(source_uid=data['source_uid'], registry_topology=data['topology'],
            counts={'strands': 32, 'Hair_segments': 128}, first_pair_ids=first_pair, long_pair_ids=long_pair,
            groups=dict(collections.Counter(item['group'] for item in effective.values())),
            collected_objects=specification['objects'], original_source_rig=main_name,
            image_buffers='empty: use saved candidate actual packed/resolved textures; no synthesized RGB conversion',
            simple_materials=[], phase='native_worker')
        before = time.perf_counter()
        result = observed_worker(specification, report)
        report['worker_seconds'] = time.perf_counter() - before
        write_json(stage / 'result.json', result)
        require(result['ok'] and result['hair_motion']['active'] and result['hair_motion']['simulation_baked'] is False,
                'Native worker did not complete an active unbaked Hair contract.')
        staged_payload = sidecar.verify_read(stage / Path(FILENAME).with_suffix('.hair-motion.json'), fbx_path=stage / FILENAME)
        mapping = check_sidecar(staged_payload, capture, result, main_name, asset_id)
        expected_parents = {name: main_rig.data.bones[name].parent.name if main_rig.data.bones[name].parent else None
                            for name in mapping.values()}
        report.update(worker_source_rigs=result['source_rigs'], accessory_bone_mapping=result['accessory_bone_mapping'],
                      explicit_Hair_bone_mapping=mapping, worker_files=result['files'], phase='publication')
        job = {'directory': directory, 'stage': stage, 'filename': FILENAME, 'asset_id': asset_id,
            'rig': main_rig, 'objects': specification['objects'], 'hair_motion': capture,
            'manifest_hash': None, 'prior': None, 'temporary': None, 'config': config}
        published = publish_local(job, result, root / 'publication_backups')
        manifest = json.loads(Path(published['report_path']).read_text(encoding='utf8'))
        require(manifest['asset_id'] == asset_id and manifest['hair_motion']['active']
            and manifest['hair_motion']['strands'] == 32 and manifest['hair_motion']['simulation_baked'] is False,
            'Published manifest does not advertise the exact active unbaked Hair contract.')
        payload = sidecar.verify_read(Path(published['filepath']).with_suffix('.hair-motion.json'), staged_payload,
                                     fbx_path=published['filepath'])
        for relative, digest in manifest['files'].items():
            require(file_hash(exporter._safe_file(directory, relative)) == digest, 'Published file hash differs: ' + relative)
        report.update(published=published, manifest=str(Path(published['report_path'])),
            fbx_sha256=payload['fbx_sha256'], sidecar=str(Path(published['filepath']).with_suffix('.hair-motion.json')),
            published_files_sha256=manifest['files'], phase='FBX_roundtrip')
        report['roundtrip'] = roundtrip_fbx(published['filepath'], payload, result, expected_parents, source_name, root)
        report['candidate_sha256_after'] = file_hash(candidate)
        require(report['candidate_sha256_after'] == original_hash, 'The saved candidate file changed during validation.')
        report.update(ok=True, phase='complete', elapsed_seconds=time.perf_counter() - started,
            handoff={'fbx': published['filepath'], 'sidecar': report['sidecar'], 'manifest': published['report_path'],
                     'candidate_unchanged': True, 'simulation_baked': False, 'Unity_import_verified': False})
    except Exception as exc:
        report['error'] = str(exc)
        report['elapsed_seconds'] = time.perf_counter() - started
        raise
    finally:
        write_json(root / 'character_consumer_validation.json', report)
        print('REAL_HAIR_CHARACTER_CONSUMER', json.dumps({'ok': report['ok'], 'phase': report['phase'],
            'evidence': str(root / 'character_consumer_validation.json'), 'Unity_written': False,
            'candidate_saved': False, 'child_Blender_started': False}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
