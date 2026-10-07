"""Disposable saved-Artist Direct cold install; no 7ac binding, timeline or deployment.

Component checks include preallocation refusal, fresh native bind, two rollback
checkpoints, mode state and public Original correction. Collision/effect/export
and cache payload acceptance remain false. Root alone runs native BG5.2.
"""
import argparse
import ast
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
PROVIDER = REPOSITORY / 'addons/character_designer/skirt_surface_direct.py'
COMPARATOR = HERE / 'compare_current_artist_fixture52.py'
COMPARATOR_SHA = 'b0b4730dac104dc6ad750eaba2ee7cb89acf6ed57a274d15f8c7bc57f296ec6f'
LOCATOR = HERE / 'compare_current_artist_fixture52_v2.py'
LOCATOR_SHA = '55c0265c576473e736ec9c44e283026fc62f6503c491c34816ff5681c2d4093d'
LIMIT_M = 5.0e-5
OLD_QA = HERE / 'verify_direct_cold_install52.py'
OLD_QA_SHA = 'acd898a2f4076d0cb92a1651ae661241d2a916d66bbfe490cc7bd803a2411ad6'
OLD_FAIL = HERE / 'actual_direct_cold_install_52_20261007_014736_925/report.json'
OLD_FAIL_SHA = '15dfb84564a139fda924cd2dcd7a7e82af2f0bf2f27658fe1ba57b58b8ec59c7'
OLD_V2 = HERE / 'verify_direct_cold_install52_v2.py'
OLD_V2_SHA = '5483fbcf504541a673f8be3efd6a1c44b0de7eda3ea1c96c61e5e5c3db37ff79'
OLD_V2_FAIL = HERE / 'actual_direct_cold_install_role_fix_52_20261007_020019_485/report.json'
OLD_V2_FAIL_SHA = '9bbaee185016425b5f3c9caad98333b016501f00c45721773c693dd7c5a13d93'


def need(value, message):
    if not value:
        raise RuntimeError('DirectCold52: ' + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def inventory(bpy):
    return {prop.identifier: sorted((value.name, value.as_pointer()) for value in getattr(bpy.data, prop.identifier)
                                   if isinstance(value, bpy.types.ID))
            for prop in bpy.data.bl_rna.properties if prop.type == 'COLLECTION'}


def error(a, b, metres, indices=None):
    need(len(a) == len(b) and len(a) > 0, 'Native coordinate/index count changed')
    chosen = list(range(len(a))) if indices is None else list(indices)
    need(chosen, 'Empty geometry coverage')
    distances = [(a[i] - b[i]).length * metres for i in chosen]
    need(all(math.isfinite(v) for v in distances), 'Nonfinite native geometry')
    return {'count': len(chosen), 'maximum_m': max(distances),
            'rms_m': math.sqrt(sum(v*v for v in distances)/len(distances)),
            'worst_index': chosen[distances.index(max(distances))]}


def bone_selection(rig):
    """Read actual 5.2 PoseBone selection, or its legacy Bone owner; no false defaults."""
    rows = []
    for pb in rig.pose.bones:
        owner = pb if hasattr(pb, 'select') else pb.bone
        fields = {name: getattr(owner, name) for name in ('select', 'select_head', 'select_tail') if hasattr(owner, name)}
        need('select' in fields and all(type(value) is bool for value in fields.values()), 'Native selection owner/boolean fields unresolved')
        need(hasattr(pb, 'hide') and type(pb.hide) is bool and hasattr(pb.bone, 'hide') and type(pb.bone.hide) is bool,
             'Native PoseBone/DataBone visibility fields unresolved')
        rows.append({'name': pb.name, 'selection_owner': owner.bl_rna.identifier,
                     'fields': fields, 'unavailable_fields': sorted(set(('select', 'select_head', 'select_tail'))-set(fields)),
                     'pose_bone_hide': pb.hide, 'data_bone_hide': pb.bone.hide,
                     'EditBone_head_tail_sampled': False})
    return rows


def first_difference(expected, actual, path='$'):
    """Only exact diagnostic readout; uses the original receipt equality."""
    if expected == actual: return None
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected or key not in actual:
                return {'path': path+'/'+str(key), 'expected_present': key in expected, 'actual_present': key in actual}
            if expected[key] != actual[key]: return first_difference(expected[key], actual[key], path+'/'+str(key))
    if isinstance(expected, list) and isinstance(actual, list):
        for index, (old, new) in enumerate(zip(expected, actual)):
            if old != new: return first_difference(old, new, path+'/'+str(index))
        return {'path': path, 'expected_length': len(expected), 'actual_length': len(actual)}
    return {'path': path, 'expected': expected, 'actual': actual,
            'expected_type': type(expected).__name__, 'actual_type': type(actual).__name__}


def receipt(bpy, p, q, direct, source, rig, body):
    shared = direct.shared
    holder, _, _ = direct.skirt.physics_control(source)
    objects = (source, rig, body)
    context = bpy.context
    return p.primitive({'inventory': inventory(bpy), 'raw_Dress': q.digest(q.raw_mesh_content(source)),
        'raw_Body': q.digest(q.raw_mesh_content(body)), 'Rest': q.digest(q.rest_content(rig)),
        'pose': q.pose_channels(rig), 'pose_position': rig.data.pose_position,
        'custom': {o.name: {key: q.custom_content(value) for key, value in o.items()} for o in objects},
        'influence': holder['physics_influence'], 'influence_ui': holder.id_properties_ui('physics_influence').as_dict(),
        'constraints': [(pb.name, [(con.as_pointer(), con.name, con.type, shared._rna(con)) for con in pb.constraints]) for pb in rig.pose.bones],
        'drivers': shared._drivers(rig), 'bindings': {o.name: [p.animation(o, q), p.animation(o.data, q)] for o in objects},
        'Body_Key_channels': None if body.data.shape_keys is None else [q.simple_rna(body.data.shape_keys),
                            [q.simple_rna(block) for block in body.data.shape_keys.key_blocks]],
        'Body_Key_binding': None if body.data.shape_keys is None else p.animation(body.data.shape_keys, q),
        'modifiers': {o.name: [(m.as_pointer(), m.type, shared._rna(m), m.is_active) for m in o.modifiers] for o in objects},
        'charts': {o.name: shared._frame(o) for o in objects},
        'frame': [context.scene.frame_current, context.scene.frame_subframe], 'mode': context.mode,
        'active': q.id_name(context.view_layer.objects.active), 'selected': sorted(o.name for o in context.selected_objects),
        'active_bone': None if rig.data.bones.active is None else rig.data.bones.active.name,
        'bone_selection': bone_selection(rig),
        'bone_collections': [(c.name, shared._rna(c)) for c in rig.data.collections_all]})


def load_artist(bpy, p, locator, artist, body_name, dress_name):
    """Open only the protected saved Artist; explicit saved owner/pointer selection."""
    bpy.ops.wm.open_mainfile(filepath=str(artist), load_ui=False)
    choices = []
    scene, rig, body, source, record = locator.locate_explicit(bpy, p, body_name, dress_name, choices)
    need(not record.get('physics'), 'Cold input must be saved controls-only LEGACY, no existing physics')
    return scene, rig, body, source, record, choices


def exercise(bpy, p, q, direct, source, rig, body, record, report, write, budget):
    """Public provider/native operators only; all timeline inputs remain untouched."""
    from mathutils import Quaternion, Vector
    shared, skirt = direct.shared, direct.skirt
    context = bpy.context
    metres = context.scene.unit_settings.scale_length
    need(math.isfinite(metres) and metres > 0, 'Unknown scene metre scale')
    guard = min(LIMIT_M, LIMIT_M * metres)
    frame = (context.scene.frame_current, context.scene.frame_subframe)
    original = receipt(bpy, p, q, direct, source, rig, body)
    protection = q.Protection()
    def unchanged(expected, label):
        actual = receipt(bpy, p, q, direct, source, rig, body)
        fields = [name for name in expected if expected[name] != actual[name]]
        report.setdefault('rollback_checks', []).append({'label': label, 'exact': not fields, 'changed_fields': fields})
        write(); need(not fields and protection.verify()['success'], label + ' changed original state/IDs/raw assets')
    def rejection(label, setup, teardown, expected_error, expected_message):
        budget(); token = setup()
        try:
            expected = receipt(bpy, p, q, direct, source, rig, body)
            try:
                direct.install(context, source, body=body, capability='BOTH')
            except expected_error as exc:
                need(expected_message in str(exc), label + ' rejected for an unrelated reason')
                report.setdefault('install_rejections', []).append({'label': label, 'exception': str(exc),
                    'preallocation_proved': label == 'Shape_Keys_preallocation',
                    'no_live_allocations_after_rejection': True})
            else:
                need(False, label + ' was not rejected')
            # Protection includes the temporary Key fixture; compare its exact receipt here.
            actual = receipt(bpy, p, q, direct, source, rig, body)
            if actual != expected:
                report.setdefault('rejection_receipt_diagnostics', []).append({'label': label,
                    'changed_fields': sorted(key for key in set(expected)|set(actual) if expected.get(key) != actual.get(key)),
                    'first_difference': first_difference(expected, actual), 'expected': expected, 'actual': actual,
                    'original_equality_passed': False, 'acceptance_changed': False})
                write()
            need(actual == expected, label + ' allocated IDs or altered its rejection fixture')
        finally:
            teardown(token)
        unchanged(original, label + '_restored')
    def duplicate():
        active = [(m, m.is_active) for m in body.modifiers]
        modifier = body.modifiers.new('QA duplicate Body ARM', 'ARMATURE'); modifier.object = rig
        return modifier, active
    def remove_duplicate(token):
        body.modifiers.remove(token[0])
        for modifier, active in token[1]:
            modifier.is_active = active
    rejection('duplicate_Body_ARM_transaction', duplicate, remove_duplicate, shared.SkirtSurfaceError,
              "Use the registered Body's native Armature and optional Subsurf")
    def keys():
        old = source.data; copied = old.copy(); source.data = copied
        try:
            source.shape_key_add(name='QA Basis', from_mix=False)
        except Exception:
            source.data = old
            if copied.users == 0: bpy.data.meshes.remove(copied)
            raise
        return old, copied, copied.shape_keys, copied.shape_keys.as_pointer()
    def remove_keys(token):
        old, copied, key, pointer = token
        need(source.data == copied and copied.users == 1 and key == copied.shape_keys
             and set(bpy.data.user_map(subset={key}).get(key, set())) == {copied}, 'QA Key ownership unresolved')
        source.shape_key_clear(); source.data = old
        need(copied.users == 0, 'QA Mesh acquired an outside user')
        bpy.data.meshes.remove(copied)
        need(not any(item.as_pointer() == pointer for item in bpy.data.shape_keys), 'QA Key was not released with its owned Mesh')
    rejection('Shape_Keys_preallocation', keys, remove_keys, direct.SkirtDirectError, 'Shape Key input is not validated')
    old_hook = direct._install_checkpoint
    class Injected(RuntimeError): pass
    for checkpoint in ('bound', 'validated'):
        hit = []
        def fail(context, obj, stage):
            old_hook(context, obj, stage)
            if stage == checkpoint:
                hit.append(stage); raise Injected('QA late rollback ' + checkpoint)
        direct._install_checkpoint = fail
        try:
            budget()
            try: direct.install(context, source, body=body, capability='BOTH')
            except Injected: pass
            else: need(False, 'Checkpoint did not raise')
        finally:
            direct._install_checkpoint = old_hook
        need(hit == [checkpoint], 'Wrong or repeated native install failure checkpoint')
        unchanged(original, 'late_' + checkpoint)
    budget(); installed = direct.install(context, source, body=body, capability='BOTH')
    actual, cloth = direct.validate(source, rig, installed)
    report['installed_backend'] = installed['physics']['backend']
    need(installed['physics']['backend'] == direct.BACKEND and protection.verify()['success'], 'Cold install changed raw assets/Rest/Actions')
    need(p.primitive(q.pose_channels(rig)) == original['pose'] and (context.scene.frame_current, context.scene.frame_subframe) == frame,
         'Native binding did not restore author pose/frame')
    noop_ids = inventory(bpy); second = direct.install(context, source, body=body, capability='BOTH')
    need(second == installed and inventory(bpy) == noop_ids, 'Already installed public no-op changed its record or IDs')
    initial_mode = direct.capture_mode(source, installed)
    direct.set_mode(source, installed, 'MANUAL'); direct.validate(source, rig, installed)
    need(not cloth.show_viewport and not cloth.show_render, 'Manual must pause Cloth')
    direct.set_mode(source, installed, 'AUTOMATIC'); direct.validate(source, rig, installed)
    need(cloth.show_viewport and cloth.show_render, 'Automatic must enable Cloth')
    direct.restore_mode(source, installed, initial_mode); direct.set_mode(source, installed, 'MANUAL')
    input_obj = bpy.data.objects[installed['physics']['surface']['roles']['INPUT_SURFACE'][0]]
    sd = input_obj.modifiers[1]; clone = sd.target
    need(sd.type == 'SURFACE_DEFORM' and sd.is_bound and actual.modifiers[1].is_bound
         and actual.modifiers[1].target == clone and clone != body and clone.data == body.data,
         'Fresh Body binding or actual read-only BodyClone missing')
    ring = direct._ring_ids(installed, len(source.data.vertices)); outside = sorted(set(range(800)) - set(ring))
    need(len(ring) == 80 and len(outside) == 720 and len(source.vertex_groups) == 33, 'Actual Cosha 800/80/720/33 coverage differs')
    mask = input_obj.vertex_groups[sd.vertex_group]
    weights = {v.index: w.weight for v in input_obj.data.vertices for w in v.groups if w.group == mask.index}
    need(weights == {i: 1. for i in ring} and cloth.settings.vertex_group_mass == direct.PIN_GROUP,
         'Fresh native raw80 full Body mask/Cloth pin wrong')
    raw = q.raw_mesh_content(source)
    for obj in (input_obj, actual):
        own = q.raw_mesh_content(obj); own['groups'] = own['groups'][:33]
        own['weights'] = [[w for w in row if w[0] < 33] for row in own['weights']]
        need(own == raw, 'Derived Mesh lost author UV/index/33groups/weights/Keys')
    # Independent native MainSkin oracle: original Dress copy, no Direct GN/Subsurf.
    oracle = source.copy(); oracle.name = 'QA original native skin'
    # An observational skin copy must never become a second public Dress source.
    for key in list(oracle.keys()): del oracle[key]
    context.scene.collection.objects.link(oracle)
    try:
        for modifier in list(oracle.modifiers)[1:]: oracle.modifiers.remove(modifier)
        def sample(label):
            budget(); context.view_layer.update()
            need((context.scene.frame_current, context.scene.frame_subframe) == frame, 'Cold operation advanced time')
            direct.validate(source, rig, direct.skirt.read_record(source))
            start = time.perf_counter(); before = shared._points(oracle, context)
            old = (sd.show_viewport, sd.show_render)
            try:
                sd.show_viewport = sd.show_render = False; context.view_layer.update()
                pre = shared._points(input_obj, context)
            finally:
                sd.show_viewport, sd.show_render = old; context.view_layer.update()
            post = shared._points(input_obj, context); visible = shared._points(source, context)
            need(len(pre) == len(post) == len(before) == 800 and len(visible) == 3040, 'Cold actual800/final3040 coverage missing')
            row = {'label': label, 'skin_oracle': error(pre, before, metres), 'raw80_effect': error(post, pre, metres, ring),
                   'outside720': error(post, pre, metres, outside), 'frame': list(frame),
                   'native_update_readback_seconds': time.perf_counter()-start, 'GUI_FPS_measured': False}
            report.setdefault('samples', []).append(row); write()
            need(row['skin_oracle']['maximum_m'] <= guard and row['outside720']['maximum_m'] == 0., 'Main skin/Body raw80 gate failed')
            need(not cloth.show_viewport and not cloth.show_render, 'Original sample enabled physical time simulation')
            return pre, post, visible
        base = sample('Manual_baseline')
        skirt._activate(context, rig, 'POSE')
        def public(action):
            result = bpy.ops.character_designer.body_original_mode('EXEC_DEFAULT', action=action)
            need('FINISHED' in result, 'Public Original/' + action + ' cancelled')
        public('ORIGINAL'); entered = sample('Original_entered')
        enter = [error(b, a, metres)['maximum_m'] for a, b in zip(base, entered)]
        need(max(enter) <= guard, 'Original entry changed native input/visible pose >50um')
        deform = {name for chain in installed['chains'] for name in chain['def']}
        weighted = sorted({source.vertex_groups[w.group].name for v in source.data.vertices for w in v.groups
                           if w.weight > 0. and source.vertex_groups[w.group].name in deform})
        need(weighted, 'No actual weighted Dress DEF')
        bone = rig.pose.bones[weighted[0]]; bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = Quaternion(bone.rotation_quaternion) @ Quaternion(Vector((1., 0., 0.)), .08)
        rig.update_tag(); edited = sample('Original_edit')
        change = [error(b, a, metres)['maximum_m'] for a, b in zip(entered, edited)]
        need(change[0] > guard and change[2] > guard, 'Real Original weighted edit not visible in800/final3040')
        public('CONTROLS'); returned = sample('Controls_correction')
        leave = [error(b, a, metres)['maximum_m'] for a, b in zip(edited, returned)]
        from character_designer import skirt_original_mode
        report['Original'] = {'weighted_bone': bone.name, 'angle_rad': .08, 'enter_errors_m': enter,
            'visible_edit_m': change, 'return_errors_m': leave,
            'correction_saved': bool(source.get(skirt_original_mode.CORRECTIONS))}
        write(); need(max(leave) <= guard and report['Original']['correction_saved'], 'Controls lost the persistent Original correction')
        direct.set_editing(source, installed, True); direct.set_editing(source, installed, False)
        blocked_state = source[direct.STATE_KEY]
        try: direct.set_mode(source, installed, 'AUTOMATIC')
        except direct.SkirtDirectError: pass
        else: need(False, 'Pending editing exposed stale Automatic Cloth')
        need(source[direct.STATE_KEY] == blocked_state and not cloth.show_viewport, 'Rejected pending switch mutated mode')
        report['fresh_bind'] = installed['physics']['surface']['bind_proof']
        report['raw_Rest_Actions_protection'] = protection.verify()
        need(report['raw_Rest_Actions_protection']['success'], 'Cold component changed protected author data')
    finally:
        bpy.data.objects.remove(oracle, do_unlink=True)
    report['native_component_completed'] = True


def pure_checks():
    tree = ast.parse(PROVIDER.read_text(encoding='utf-8'))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    expected = {'install': (['context', 'source'], ['body', 'capability']), 'validate': (['source', 'rig', 'record'], []),
                'capture_mode': (['source', 'record'], []), 'set_mode': (['source', 'record', 'mode'], []),
                'set_editing': (['source', 'record', 'editing'], []), 'restore_mode': (['source', 'record', 'state'], []),
                '_install_checkpoint': (['_context', '_source', '_stage'], [])}
    for name, (args, keywords) in expected.items():
        need(name in functions and [a.arg for a in functions[name].args.args] == args
             and [a.arg for a in functions[name].args.kwonlyargs] == keywords, 'Actual provider ABI differs: '+name)
    own = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    calls = [n for n in ast.walk(own) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    need(not any(n.func.attr in {'frame_set', 'save_as_mainfile', 'bake', 'free_bake'} for n in calls), 'Cold QA must not seek/save/bake/free')
    need({n.func.attr for n in calls if isinstance(n.func.value, ast.Name) and n.func.value.id == 'direct'} <= set(functions),
         'Direct QA calls a missing actual provider function')
    print(json.dumps({'pure_provider_signature_checks': len(expected), 'no_seek_save_bake': True, 'actual_provider_direct_calls_exist': True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artist-protection', type=Path, required=True); parser.add_argument('--artist-protection-sha', required=True)
    parser.add_argument('--expected-direct-sha', required=True); parser.add_argument('--body-object', required=True); parser.add_argument('--dress-object', required=True)
    parser.add_argument('--soft-seconds', type=float, default=120.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(), 'Fresh private JSON output required')
    need(0. < args.soft_seconds <= 180. and sha(PROVIDER) == args.expected_direct_sha, 'Provider SHA or soft budget differs')
    import bpy
    need(bpy.app.background and bpy.app.version[:2] == (5, 2) and '--factory-startup' in sys.argv and not bpy.data.filepath, 'Empty factory BG5.2 only')
    import importlib.util
    spec = importlib.util.spec_from_file_location('cold_comparator_readers', COMPARATOR); p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
    need(sha(COMPARATOR) == COMPARATOR_SHA and sha(LOCATOR) == LOCATOR_SHA, 'Frozen raw/locator helper differs')
    locator = p.load(LOCATOR, LOCATOR_SHA, 'cold_explicit_locator')
    disk = p.load(p.DISK, p.DISK_SHA, 'cold_disk'); source_manifest = p.load(p.SOURCE, p.SOURCE_SHA, 'cold_source')
    pins = {Path(__file__): sha(__file__), COMPARATOR: COMPARATOR_SHA, LOCATOR: LOCATOR_SHA, p.QA: p.QA_SHA,
            p.DISK: p.DISK_SHA, p.SOURCE: p.SOURCE_SHA, PROVIDER: args.expected_direct_sha,
            OLD_QA: OLD_QA_SHA, OLD_FAIL: OLD_FAIL_SHA, OLD_V2: OLD_V2_SHA, OLD_V2_FAIL: OLD_V2_FAIL_SHA}
    need(all(sha(path) == value for path, value in pins.items()), 'Cold QA history/self/helper/provider pins differ')
    before = source_manifest.current_manifest(); started = time.perf_counter()
    report = {'native_component_completed': False, 'accepted': False, 'effect_accepted': False, 'export_accepted': False,
        'artist_saved': False, 'QA_blend_saved': False, 'timeline_seek_by_QA': False, 'cache_payload_preserved': 'Unknown',
        'cold_bind_source': 'Protected saved Artist LEGACY; no 7ac object, SD or cache copied', 'source_before': before, 'errors': []}
    report['observer_selection_API'] = {'scope': 'Only present native PoseBone/Bone fields; absent fields recorded, never defaulted False',
        'old_QA': str(OLD_QA), 'old_QA_sha256': OLD_QA_SHA, 'old_failed_report': str(OLD_FAIL),
        'old_failed_report_sha256': OLD_FAIL_SHA, 'historical_failure_upgraded': False}
    report['rejection_observer_diagnostics'] = {'old_v2': str(OLD_V2), 'old_v2_sha256': OLD_V2_SHA,
        'old_failed_report': str(OLD_V2_FAIL), 'old_failed_report_sha256': OLD_V2_FAIL_SHA,
        'same_hard_equality_required': True, 'historical_failure_upgraded': False}
    def write():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    def budget(): need(time.perf_counter()-started < args.soft_seconds, 'Native cold soft budget exceeded')
    try:
        report['artist_before'] = disk.proof(args.artist_protection, args.artist_protection_sha)
        q = p.readers(bpy); artist = Path(report['artist_before']['receipt']['artist_path'])
        scene, rig, body, dress, record, choices = load_artist(bpy, p, locator, artist, args.body_object, args.dress_object)
        report['explicit_selection'] = choices; loaded = q.Protection(); loaded_pose = q.pose_channels(rig)
        sys.path.insert(0, str(REPOSITORY/'addons')); package = importlib.import_module('character_designer'); package.register()
        direct = importlib.import_module('character_designer.skirt_surface_direct')
        need(Path(direct.__file__).resolve() == PROVIDER.resolve() and loaded.verify()['success']
             and q.pose_channels(rig) == loaded_pose, 'Canonical registration altered loaded raw/Rest/Actions/pose')
        exercise(bpy, p, q, direct, dress, rig, body, record, report, write, budget)
    except Exception as exc:
        report['errors'].append({'exception': repr(exc), 'traceback': traceback.format_exc()})
    finally:
        try:
            bpy.ops.wm.read_factory_settings(use_empty=True); report['private_scene_disposed'] = True
        except Exception as exc: report['errors'].append({'disposal': repr(exc)})
        try:
            report['artist_after'] = disk.proof(args.artist_protection, args.artist_protection_sha)
            report['source_after'] = source_manifest.current_manifest()
            report['source_files_Artist_exact'] = report['source_after'] == before and all(sha(path) == value for path, value in pins.items())
            need(report['source_files_Artist_exact'], 'Source/QA/Provider/Artist disk changed')
        except Exception as exc: report['errors'].append({'final_guard': repr(exc)})
        report['native_component_completed'] = report['native_component_completed'] and not report['errors']
        report['elapsed_seconds'] = time.perf_counter()-started; write()
    print(json.dumps({'completed': report['native_component_completed'], 'errors': report['errors'], 'report': str(args.output)}))
    return 0 if report['native_component_completed'] else 2


if __name__ == '__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
