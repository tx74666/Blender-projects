"""Prepared Source for one isolated latest-original CoshaRig control round.

Open only a verified latest SaveCopy, never the artist. Attach one real prepared
Rigging work item to its original adopted Rig and old Worklist. No FBX import,
fresh setup, Sync, worker, publication, repair, or Unity Apply occurs here.
This script has not run; a new resource grant and final package are required.
"""

import argparse
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace


ROUND = Path(__file__).resolve().parent
CFAA_SHA = 'cfaa6dc580d69dbdc7c752078752f2a3cbe89f33ec02a60c5186a196fba4cdcb'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
SNAPSHOT_SOURCE_SHA = '803088d42e1b239b7cc5c6753120ae9707e0a8d3b5e003f474bdbd3a0df28862'
INHERITED = ROUND / 'new_official_cosha_round.py'


def load_source(path, expected, name):
    """Load only an admitted helper; this is called by the future launcher."""
    import hashlib
    path = Path(path).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Source helper pin changed: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The inherited module contains stdlib definitions only. No candidate add-on or
# bpy import/registration is performed until the explicit future main/start.
base = load_source(INHERITED, CFAA_SHA, 'original_control_inherited_cfaa')
require, pin, sha, document, digest = base.require, base.pin, base.sha, base.document, base.digest
DERIVED_ROW = {'scan_state', 'scan_reason', 'b_edited', 'composition_changed',
               'effective_inputs_changed', 'export_needed', 'sync_selected'}
HEADER_FIELDS = ('workspace_path', 'workspace_identity', 'workspace_id', 'prepare_request_id',
    'prepared_work_item_ids', 'target_name', 'target_guid', 'model_file', 'model_sha256',
    'composition_workspace_path', 'composition_workspace_identity', 'composition_base_item_id')


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-report', 'protected-artist', 'source-freeze', 'package-manifest',
                 'latest-snapshot-receipt', 'latest-seed', 'preservation-oracle'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    for name in ('script-sha256', 'unity-project-root', 'output-root', 'profile-root'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--reference-packet')
    parser.add_argument('--reference-packet-sha256')
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


class OriginalRound(base.Round):
    def __init__(self, args):
        own = pin(__file__, args.script_sha256)
        snapshot_pin = pin(args.latest_snapshot_receipt, args.latest_snapshot_receipt_sha256)
        seed_pin = pin(args.latest_seed, args.latest_seed_sha256)
        oracle_pin = pin(args.preservation_oracle, args.preservation_oracle_sha256)
        require(oracle_pin['sha256'] == ORACLE_SHA, 'Keep the unchanged historical preservation oracle.')
        receipt = document(snapshot_pin['path'])
        require(receipt['schema'] == 'x.validation.latest-original-artist-snapshot/1'
                and receipt['completed'] is True and receipt['backup_verified'] is True
                and receipt['original_artist_disk_unchanged'] is True
                and receipt['original_artist_saved'] is False
                and receipt['candidate_imported_or_registered'] is False
                and receipt['runtime_version'] == [0, 77, 24]
                and receipt['source']['sha256'] == SNAPSHOT_SOURCE_SHA
                and receipt['backup'] == seed_pin
                and receipt['protected_artist']['sha256'] == args.protected_artist_sha256
                and Path(receipt['protected_artist']['path']).resolve() == Path(args.protected_artist).resolve(),
                'Require an actual successful freshest original SaveCopy; no historical QA substitute.')
        require(Path(seed_pin['path']) != Path(args.protected_artist).resolve()
                and Path(seed_pin['path']).is_relative_to(ROUND), 'Never open or overwrite the artist file.')
        rig_read = receipt['before']['original_MainRig_session_and_rawRest']
        require(rig_read['known'] is True, 'The actual snapshot must identify its original Rig.')
        self.seed_names = {'scene': receipt['before']['context']['scene']['name'],
                           'rig': rig_read['value']['rig']['name']}
        require(all(isinstance(v, str) and v for v in self.seed_names.values()), 'Snapshot names are incomplete.')
        inherited_args = copy.copy(args)
        inherited_args.script_sha256 = CFAA_SHA
        super().__init__(inherited_args)
        self.args = args
        self.pins.update(script=own, inherited_control_harness=pin(INHERITED, CFAA_SHA),
            latest_snapshot_receipt=snapshot_pin, latest_seed=seed_pin, preservation_oracle=oracle_pin,
            snapshot_source=pin(receipt['source']['path'], SNAPSHOT_SOURCE_SHA))
        self.names, self.phase = dict(self.seed_names), 'open_latest_seed'
        self.report.update(schema='x.validation.original-cosha-control-save/1',
            source_inputs=self.pins, new_Rig_trial_only=False, original_Rig_acceptance=False,
            original_clone_Rig_acceptance=False, original_artist_opened=False,
            latest_original_SaveCopy_used=True, full_original_asset_preservation_verified=False,
            original_recovery_Restore_readopt_verified=False, factory_FBX_or_fresh_setup_performed=False,
            old_numeric_reused=False, asset_qualification='Exact protected original data/Rest plus authenticated motion-copy domain; exact original assets; official derived preview outputs recorded separately.',
            old_row_qualification='Immutable row/header/Link/cache/Actions/slots/motions exact; sync_selected exact at Attach boundary, then unmasked scanner/lifecycle-derived feedback separately measured. No old-row or batch Sync.')
        self.report_path = self.output / 'original_cosha_report.json'
        with self.report_path.open('x', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        # Keep the constructor's provisional report, explicitly marked as an
        # inherited admission record rather than a second native result.
        provisional = self.output / 'new_official_cosha_report.json'
        with provisional.open('w', encoding='utf-8') as stream:
            json.dump({'schema': 'x.validation.original-control-inherited-admission/1',
                'completed': False, 'native_execution_performed': False,
                'successor_report': str(self.report_path), 'inherited_source': self.pins['inherited_control_harness']}, stream, indent=2)
        self.old, self.assets_before, self.original_capture, self.original_objects = None, None, None, None
        self.snapshot_receipt = receipt
        self.oracle = None

    def id(self, value):
        if value is None:
            return None
        library = value.library
        return {'type': value.bl_rna.identifier, 'name': value.name,
                'library': str(Path(self.bpy.path.abspath(library.filepath)).resolve()) if library else None}

    def plain(self, value, depth=0):
        require(depth <= 24, 'Original metadata exceeds its bounded depth.')
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            require(math.isfinite(value), 'Nonfinite protected metadata is Unknown.')
            return value
        if isinstance(value, self.bpy.types.ID):
            return {'native_id': self.id(value)}
        if hasattr(value, 'items'):
            return {str(k): self.plain(v, depth + 1) for k, v in value.items()}
        if isinstance(value, (set, frozenset)):
            return sorted((self.plain(v, depth + 1) for v in value), key=digest)
        if hasattr(value, 'to_list'):
            value = value.to_list()
        require(hasattr(value, '__len__') and hasattr(value, '__iter__') and len(value) <= 100000,
                'Unsupported original metadata is Unknown: ' + type(value).__name__)
        return [self.plain(v, depth + 1) for v in value]

    def rna(self, value, *, exclude=(), depth=0):
        require(depth <= 12, 'Protected RNA depth exceeds its bound.')
        row = {}
        for prop in value.bl_rna.properties:
            name = prop.identifier
            if name in {'rna_type', 'execution_time'} or name in exclude:
                continue
            actual = getattr(value, name)
            if prop.type == 'COLLECTION':
                require(len(actual) <= 10000, 'Protected RNA collection is too large.')
                row[name] = [self.rna(v, depth=depth + 1) for v in actual]
            elif prop.type == 'POINTER' and actual is not None and not isinstance(actual, self.bpy.types.ID):
                row[name] = self.rna(actual, depth=depth + 1)
            else:
                row[name] = self.plain(actual)
        return row

    def old_state(self, ctx):
        saved = self.worklist.state(ctx)
        selected = tuple(saved.items) if self.old is None else tuple(i for i in saved.items if i.item_id in self.old['rows'])
        require(len({i.item_id for i in selected}) == len(selected), 'Duplicate original row identities.')
        rows, feedback, files = {}, {}, {}
        for item in selected:
            row = self.rna(item, exclude=DERIVED_ROW)
            for key in ('manifest_path', 'source_file', 'model_file', 'workspace_path'):
                if row.get(key):
                    row[key] = str(Path(row[key]).resolve())
            rows[item.item_id] = row
            feedback[item.item_id] = {key: getattr(item, key) for key in DERIVED_ROW}
            for path, expected in ((item.source_file, item.source_hash), (item.model_file, item.model_sha256)):
                if path:
                    checked = pin(path, expected)
                    files[checked['path']] = checked
            if item.manifest_path:
                checked = pin(item.manifest_path, sha(item.manifest_path))
                files[checked['path']] = checked
        header = {name: getattr(saved, name) for name in HEADER_FIELDS}
        for key in ('workspace_path', 'model_file', 'composition_workspace_path'):
            if header[key]:
                header[key] = str(Path(header[key]).resolve())
        for path in (saved.workspace_path, saved.composition_workspace_path):
            if path:
                checked = pin(path, sha(path))
                files[checked['path']] = checked
        return {'header': header, 'rig': self.id(saved.rig), 'catalog': [self.rna(i) for i in saved.catalog],
            'composition_catalog': [self.rna(i) for i in saved.composition_catalog],
            'rows': rows, 'linked_files': files, 'derived_feedback': feedback}

    def snapshot_identity(self, row):
        if row is None:
            return None
        library = row.get('library')
        return {'type': row['type'], 'name': row['name'],
            'library': str(Path(self.bpy.path.abspath(library)).resolve()) if library else None}

    def snapshot_value(self, value):
        if isinstance(value, dict):
            if {'native_pointer', 'type', 'name', 'library'} <= set(value):
                return {'native_id': self.snapshot_identity(value)}
            return {key: self.snapshot_value(v) for key, v in value.items() if key != '$custom_properties'}
        if isinstance(value, list):
            return [self.snapshot_value(v) for v in value]
        return value

    def check_loaded_snapshot(self, ctx, rig):
        """Compare available original-process light evidence, not Unknown geometry."""
        before = self.snapshot_receipt['before']
        raw = before['original_MainRig_session_and_rawRest']['value']
        require(self.id(rig) == self.snapshot_identity(raw['rig'])
                and self.id(rig.data) == self.snapshot_identity(raw['data'])
                and self.ua._rest_state(rig.data) == raw['rawRest'], 'Opening the latest seed changed the recorded original Rig/data/raw Rest.')
        actions = {digest(self.snapshot_identity(row['identity'])): row for row in before['actions']}
        require(len(actions) == len(before['actions']) and set(actions) == {digest(self.id(a)) for a in self.bpy.data.actions},
                'The SaveCopy did not retain the original Action inventory; no reconstruction is allowed.')
        for action in self.bpy.data.actions:
            expected = actions[digest(self.id(action))]['slots']
            actual = [{'handle': s.handle, 'target_id_type': s.target_id_type,
                'identifier': s.identifier, 'name_display': s.name_display} for s in action.slots] if action.is_action_layered else []
            require(actual == expected, 'A saved original Action slot identity changed before Attach.')
        skins = [o for o in ctx.scene.objects if o.type == 'MESH' and
            (o.parent == rig or any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))]
        actual_skins = {o.name: {'object': self.id(o), 'data': self.id(o.data),
            'materials': [self.id(m) for m in o.data.materials],
            'vertex_groups': [g.name for g in o.vertex_groups],
            'shape_keys': [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []} for o in skins}
        expected_skins = {name: {**row, 'object': self.snapshot_identity(row['object']),
            'data': self.snapshot_identity(row['data']),
            'materials': [self.snapshot_identity(m) for m in row['materials']]} for name, row in before['skin_native_ids'].items()}
        require(actual_skins == expected_skins, 'Saved original skin/data/material/group/Shape Key identities changed before Attach.')
        workspace = before['full_worklist']
        require(workspace['known'] is True, 'Original saved Worklist metadata is Unknown.')
        saved = self.worklist.state(ctx)
        recorded = self.snapshot_value(workspace['value'])
        for field in HEADER_FIELDS:
            if field in recorded:
                actual, expected = getattr(saved, field), recorded[field]
                if field.endswith('_path') or field == 'model_file':
                    actual = str(Path(actual).resolve()) if actual else actual
                    expected = str(Path(expected).resolve()) if expected else expected
                require(actual == expected, 'Latest seed changed a recorded original Worklist header: ' + field)
        expected_rows = {row['item_id']: row for row in recorded['items']}
        require(len(expected_rows) == len(recorded['items'])
                and set(expected_rows) == {i.item_id for i in saved.items}, 'Latest seed changed the original row identities.')
        for item in saved.items:
            actual = self.rna(item, exclude=DERIVED_ROW)
            for key, expected in expected_rows[item.item_id].items():
                if key in DERIVED_ROW:
                    continue
                require(key in actual, 'An original row field is unsupported by the candidate runtime: ' + key)
                observed = actual[key]
                if key in {'manifest_path', 'source_file', 'model_file', 'workspace_path'}:
                    expected = str(Path(expected).resolve()) if expected else expected
                    observed = str(Path(observed).resolve()) if observed else observed
                require(observed == expected, 'Latest seed changed an immutable original row field: ' + key)
        for field in ('catalog', 'composition_catalog'):
            actual = [self.rna(row) for row in getattr(saved, field)]
            require(actual == recorded[field], 'Latest seed changed the original catalog: ' + field)
        self.report['latest_snapshot_light_readback'] = {'recorded_original_Rig_data_rawRest_exact': True,
            'original_Action_inventory_and_slots_exact': True, 'original_skin_native_domains_exact': True,
            'recorded_original_Worklist_header_rows_catalog_exact': True,
            'original_process_full_geometry_was_Unknown': True, 'full_clone_asset_baseline_follows': True}

    def actions(self, *, full_motions=True):
        """Read every original Action slot; Unknown remains explicit, never equal by name."""
        result = {}
        allowed = None if self.old is None else set(self.old['actions'])
        motion_keys = set(self.target._action_motion_keys())
        for action in self.bpy.data.actions:
            key = digest(self.id(action))
            if allowed is not None and key not in allowed:
                continue
            slots = [self.rna(slot) for slot in action.slots] if action.is_action_layered else []
            handles = [slot.handle for slot in action.slots] if slots else [0]
            result[key] = {'identity': self.id(action), 'slots': slots,
                'motions': {str(h): self.fingerprints.fingerprint_action(action, h) for h in handles} if full_motions else None,
                'properties': self.plain({k: v for k, v in action.items() if k not in motion_keys}),
                'motion_recovery_refs': self.plain({k: action[k] for k in motion_keys if k in action})}
        return result

    def guard_old(self, ctx, boundary, *, changed_motion_refs=False, attach_boundary=False, full_motions=False):
        actual, actions = self.old_state(ctx), self.actions(full_motions=full_motions)
        require(set(actual['rows']) == set(self.old['rows']), 'An original work item disappeared.')
        for field in ('header', 'rig', 'catalog', 'composition_catalog', 'rows', 'linked_files'):
            require(actual[field] == self.old[field], 'Protected original Worklist field changed: ' + field)
        if attach_boundary:
            require(all(actual['derived_feedback'][key]['sync_selected'] == prior['sync_selected']
                    for key, prior in self.old['derived_feedback'].items()), 'Attach changed an original Sync-selection flag.')
        require(set(actions) == set(self.old['actions']), 'An original Action native identity disappeared.')
        for key, row in actions.items():
            prior = self.old['actions'][key]
            for field in ('identity', 'slots', 'properties') + (('motions',) if full_motions else ()):
                require(row[field] == prior[field], 'Original Action/slot content changed: ' + field)
            if not changed_motion_refs:
                require(row['motion_recovery_refs'] == prior['motion_recovery_refs'], 'Unexpected original Action recovery-reference change.')
        if changed_motion_refs:
            saved, rig = self.worklist.state(ctx), self.worklist.state(ctx).rig
            original = self.original_data(rig)
            for item in saved.items:
                if item.item_id in self.old['rows'] and item.custom_action:
                    self.target._read_action_motion_data(rig, item.custom_action, original)
            self.report['old_Action_recovery_reference_updates_authenticated'] = True
        self.report.setdefault('old_scanner_feedback', []).append({'boundary': boundary,
            'before': self.old['derived_feedback'], 'actual': actual['derived_feedback'],
            'scan_algorithm_unchanged': True, 'sync_selected_exact_at_Attach_boundary': attach_boundary,
            'later_sync_selection_is_scanner_or_SKIP_SAVE_lifecycle_feedback': not attach_boundary,
            'full_old_Action_motion_measured_this_boundary': full_motions,
            'old_row_Sync_or_batch_launch_performed': False})

    def original_data(self, rig):
        if self.target.is_adopted(rig):
            record = self.target._load(rig)
            capture = record['capture']['targets'][0]
            self.target._prove_motion_data(capture['data'], rig.data, capture['rest'],
                record['motion_rest'], record['mapped_names'])
            require(self.plain(capture['data']) == self.original_capture['targets'][0]['data']
                    and self.ua._rest_state(capture['data']) == self.original_capture['targets'][0]['rest'],
                    'The protected original data/Rest changed or was replaced.')
            return capture['data']
        require(self.plain(rig.data) == self.original_capture['targets'][0]['data']
                and self.ua._rest_state(rig.data) == self.original_capture['targets'][0]['rest'],
                'Restored Main Rig is not the exact original data/Rest.')
        return rig.data

    def asset_snapshot(self, ctx, rig):
        """Use unchanged 260b on the exact original object domain, not new gun assets."""
        self.original_data(rig)
        expected = set(self.original_objects)
        objects = {digest(self.id(o)): o for o in ctx.scene.objects}
        require(expected <= set(objects), 'An original Scene Object was removed or substituted.')
        extra = set(objects) - expected
        if extra:
            session = self.native.current(rig)
            require(session and session.get('weapon_preview'), 'An unowned new Scene Object appeared.')
            record, owned = self.weapon.validate_owned(rig)
            require(record['rigging_session_owner'] == session['owner']
                    and extra == {digest(self.id(o)) for o in owned}, 'Only the exact new owned weapon display may be outside the original asset domain.')
        scene = SimpleNamespace(objects=[objects[k] for k in sorted(expected)],
            frame_current=ctx.scene.frame_current, frame_subframe=ctx.scene.frame_subframe)
        result = self.oracle.asset_snapshot(scene, rig, self.ua)
        # 260b's mode-derived Body/FK/Forearm authorization is retained. Raw
        # current Rest is additionally recorded, never called raw-byte equal.
        result['raw_current_rest_sha256'] = digest(self.ua._rest_state(rig.data))
        result['authenticated_original_rest_sha256'] = digest(self.original_capture['targets'][0]['rest'])
        result['qualified_original_component_sha256'] = {
            **result['protected_preview_component_sha256'],
            'rest': result['authenticated_original_rest_sha256']}
        skins = [o for o in scene.objects if o.type == 'MESH' and
            (o.parent == rig or any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))]
        result['original_modifiers'] = {o.name: [self.rna(m) for m in o.modifiers] for o in skins}
        result['original_object_ids'] = {k: self.id(objects[k]) for k in sorted(expected)}
        result['original_object_structure'] = {k: {'parent': self.id(objects[k].parent),
            'parent_type': objects[k].parent_type, 'parent_bone': objects[k].parent_bone,
            'parent_inverse': base.matrix(objects[k].matrix_parent_inverse),
            'collection_links': sorted((self.id(c) for c in objects[k].users_collection), key=digest)}
            for k in sorted(expected)}
        return result

    def guard_assets(self, ctx, boundary):
        rig = self.worklist.state(ctx).rig
        actual = self.asset_snapshot(ctx, rig)
        native_changes = self.oracle.protected_preview_changes(self.assets_before, actual)
        require(actual['qualified_original_component_sha256'] == self.assets_before['qualified_original_component_sha256']
                and set(native_changes) <= {'rest'}
                and actual['original_modifiers'] == self.assets_before['original_modifiers']
                and actual['original_object_ids'] == self.assets_before['original_object_ids']
                and actual['original_object_structure'] == self.assets_before['original_object_structure'],
                'Protected original mesh/material/weights/Shape Keys/color/collection/widgets/modifiers/Forearm calibration changed.')
        self.report.setdefault('original_asset_snapshots', []).append({'boundary': boundary, 'snapshot': actual,
            'qualified_original_changes': [], 'oracle_protected_changes': native_changes,
            'raw_changes': self.oracle.changes(self.assets_before, actual),
            'derived_geometry_not_claimed_equal': True, 'original_rest_exact': True,
            'motion_copy_proved': self.target.is_adopted(rig)})

    def current(self, ctx):
        saved = self.worklist.state(ctx)
        items = [i for i in saved.items if i.item_id == self.names['item']]
        require(len(items) == 1 and self.id(saved.rig) == self.old['rig']
                and saved.rig.name == self.seed_names['rig'] and ctx.scene.name == self.seed_names['scene'],
                'The exact newly attached row/original Rig/Scene is missing or ambiguous.')
        item, rig = items[0], saved.rig
        require(ctx.scene.character_designer_setup.rig == rig and item.rig == rig
                and self.target.managed(rig) and self.target.is_adopted(rig), 'Original adoption/setup owner changed.')
        session = self.native.current(rig)
        require(session and session['scene'] == ctx.scene and session['base_action'] == item.custom_action
                and session['base_slot'] == item.custom_slot and session['work_item_id'] == self.work_id
                and session['source_packet_sha256'] == self.pins['packet']['sha256'], 'Original attached native owner changed.')
        # Tweak is legal only for the exact owned input. ensure_active itself
        # permits ordinary Worklist base Actions, not the separate Tweak Action.
        with self.native.base_only(ctx, rig, action=item.custom_action):
            self.target.ensure_active(ctx, rig)
            self.worklist.validate_rigging_entry(ctx, item, session)
        self.worklist._check_baseline(item)
        require(self.ua.native_action_frame_rate(item.custom_action) == self.packet['sampleRate']
                and self.ua.native_action_frame_rate(item.source_action) == self.packet['sampleRate']
                and len(self.native._curves(session['input_action'], session['input_slot'])) == 20,
                'Actual formal Base/Source/input clock or exact twenty-curve carrier changed.')
        return item, session

    def add_activate(self):
        with self.context() as ctx:
            saved, setup = self.worklist.state(ctx), ctx.scene.character_designer_setup
            rig = setup.rig
            require(rig and rig.name == self.seed_names['rig'] and rig == saved.rig
                    and rig.library is None and ctx.view_layer.objects.get(rig.name) == rig
                    and self.target.managed(rig) and self.target.is_adopted(rig)
                    and len(saved.items) > 0, 'The actual latest original Rig must already be adopted with retained rows; no repair/adoption fallback.')
            self.check_loaded_snapshot(ctx, rig)
            self.target.ensure_active(ctx, rig)
            self.oracle = load_source(self.pins['preservation_oracle']['path'], ORACLE_SHA, 'original_assets_260b')
            record = self.target._load(rig)
            self.target._validate_capture(ctx, record['capture'])
            self.original_capture = self.plain(record['capture'])
            self.original_objects = sorted(digest(self.id(o)) for o in ctx.scene.objects)
            self.old = self.old_state(ctx)
            self.old['actions'] = self.actions()
            require(all(proof['fingerprint_known'] for row in self.old['actions'].values()
                    for proof in row['motions'].values()), 'At least one original slot is Unknown; full original motion preservation cannot be claimed.')
            self.assets_before = self.asset_snapshot(ctx, rig)
            self.report['original_before'] = {'worklist': self.old, 'assets': self.assets_before,
                'recovery_capture_sha256': digest(self.original_capture), 'native_Rig': self.id(rig),
                'original_snapshot_full_oracle_was_deferred': True}
            self.checkpoint('before_public_Attach_existing_original_Rig')
            item = self.worklist.attach_prepared_rigging_work(ctx, self.pins['workspace']['path'], work_item_id=self.work_id)
            require(item.rig == rig and set(i.item_id for i in saved.items) == set(self.old['rows']) | {item.item_id}
                    and len(saved.items) == len(self.old['rows']) + 1, 'Public Attach did not retain exactly every original row plus one new row.')
            self.names = {'item': item.item_id, **self.seed_names}
            item, session = self.current(ctx)
            require(Path(item.manifest_path).resolve() == Path(self.pins['link']['path'])
                    and item.model_sha256 == self.pins['model']['sha256']
                    and session['capture'] == self.contract.validate_capture(self.packet['rigging'], packet=self.packet),
                    'Attach changed the real external work ownership or stripped captured inputs.')
            self.report['public_row'] = {'item_id': item.item_id, 'rig': item.rig.name, 'scene': ctx.scene.name,
                'source_action': item.source_action.name, 'source_slot': item.source_slot,
                'custom_action': item.custom_action.name, 'custom_slot': item.custom_slot,
                'source_cache': pin(item.source_file, item.source_hash), 'input_action': session['input_action'].name,
                'input_slot': session['input_slot'], 'draft_id': session['new_action_id']}
            self.base_sha = self.native._motion(item.custom_action, item.custom_slot)
            self.source_sha = self.native._motion(item.source_action, item.source_slot)
            self.presentation_before = self.presentation(rig)
            self.guard_old(ctx, 'Attach_before_scan', attach_boundary=True, full_motions=True)
            self.report['scan_before'] = self.collector.scan_changes(ctx)
            self.report['proof_before'] = self.collector.item_fingerprint(ctx, item)
            self.guard_old(ctx, 'Attach_scan_before')
            self.original_data(rig)
            self.phase = 'edit_save'
        self.checkpoint('public_Attach_Activate_original_Rig_finished')

    def save_scene(self):
        with self.context() as ctx:
            self.guard_old(ctx, 'before_save', changed_motion_refs=self.report.get('old_Action_recovery_reference_updates_authenticated', False))
            self.original_data(self.worklist.state(ctx).rig)
        # Original inherited save uses a unique QA path, never the input seed.
        super().save_scene()

    def verify_reopen(self, *, final=False):
        with self.context() as ctx:
            witness = self.cached_lifecycle(ctx, 'final_load_post' if final else 'load_post')
            require(witness['edit_role'] == 'BASE' and witness['tweak_enabled'] is False,
                    'Saved enabled BASE preview was not automatically reacquired before manual calls.')
            item, session = self.current(ctx)
            require(self.dto(ctx, session) == self.saved_dto
                    and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                    and self.native._motion(item.source_action, item.source_slot) == self.source_sha
                    and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha
                    and self.presentation(item.rig) == self.presentation_before, 'Original clone save/reopen lost exact input/base/presentation content.')
            self.guard_old(ctx, 'final_reopen' if final else 'reopen', changed_motion_refs=final, full_motions=final)
            if final:
                self.guard_assets(ctx, 'final_reopen')
            else:
                self.original_data(item.rig)
            self.immutable()
            self.runtime_paths()
            self.phase = 'done' if final else 'owned_restore_roundtrip'
            if final:
                self.report.update(completed=True, original_Rig_acceptance=False,
                    original_clone_Rig_acceptance=True, formal_public_Attach_Activate_verified=True,
                    explicit_input_save_verified=True, save_reopen_verified=True,
                    full_original_asset_preservation_verified=True, original_recovery_Restore_readopt_verified=True,
                    automatic_saved_cache_before_manual_Activate=True, callbacks=witness['callbacks'],
                    live_original_integration_verified=False, artist_writes_performed=False)
        self.checkpoint('completed_original_clone_control_save_only' if final else 'original_clone_reopen_verified')

    def owned_restore_roundtrip(self):
        with self.context() as ctx:
            item, session = self.current(ctx)
            record, objects = self.weapon.validate_owned(item.rig)
            pointers = {'base': item.custom_action.as_pointer(), 'input': session['input_action'].as_pointer(),
                'weapon_collection': record['collection'].as_pointer(),
                'weapon_objects': sorted(o.as_pointer() for o in objects)}
            token = self.native._capture_owned(ctx, item.rig)
            require(token is not None, 'Actual owned rollback token is missing.')
            self.native.restore_owned(ctx, item.rig)
            self.native._restore_owned_state(ctx, item.rig, token)
            item, session = self.current(ctx)
            record, objects = self.weapon.validate_owned(item.rig)
            require(pointers == {'base': item.custom_action.as_pointer(), 'input': session['input_action'].as_pointer(),
                'weapon_collection': record['collection'].as_pointer(),
                'weapon_objects': sorted(o.as_pointer() for o in objects)}
                and self.dto(ctx, session) == self.saved_dto
                and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha,
                'Owned rollback did not retain the exact live input/display native IDs and saved values.')
            self.report['owned_restore_roundtrip'] = {'exact_native_ID_identity': True,
                'saved_input_and_Return_exact': True, 'forced_fault_injection': False}
            self.guard_old(ctx, 'owned_restore_roundtrip')
            self.original_data(item.rig)
            self.phase = 'restore_readopt'
        self.checkpoint('owned_preview_restore_roundtrip_finished')

    def restore_readopt(self):
        with self.context() as ctx:
            item, session = self.current(ctx)
            retained = {'item': item.item_id, 'base': self.id(item.custom_action), 'source': self.id(item.source_action),
                'input': self.id(session['input_action']), 'slot': session['input_slot'],
                'input_motion': self.native._motion(session['input_action'], session['input_slot']), 'dto': self.dto(ctx, session)}
            expected = self.plain(self.target._load(item.rig)['capture'])
            require(expected == self.original_capture, 'Attach rewrote the original recovery capture.')
            rig = self.worklist.restore_main_rig(ctx)
            actual = self.plain(self.target._capture(ctx, rig))
            require(actual == expected and not self.target.is_adopted(rig)
                    and self.native.current(rig) is None, 'Public Restore Main Rig did not recover the exact original capture/close owned preview.')
            self.original_data(rig)
            self.guard_old(ctx, 'Restored', changed_motion_refs=True)
            self.report['exact_original_recovery_readback'] = {'capture_sha256': digest(actual),
                'protected_original_data_rest_exact': True, 'retained_input_before': retained}
            require(self.worklist.adopt_main_rig(ctx) == rig, 'Public re-adopt did not retain the exact original Rig.')
            self.worklist.activate(ctx, retained['item'], 'CUSTOM')
            item, session = self.current(ctx)
            require(self.id(item.custom_action) == retained['base'] and self.id(item.source_action) == retained['source']
                    and self.id(session['input_action']) == retained['input'] and session['input_slot'] == retained['slot']
                    and self.native._motion(session['input_action'], session['input_slot']) == retained['input_motion']
                    and self.dto(ctx, session) == retained['dto'], 'Public re-adopt/Activate replaced or lost the retained draft/input values.')
            require(self.target._read_action_motion_data(rig, item.custom_action, self.original_data(rig))[0]
                    == frozenset(self.target._load(rig)['mapped_names']), 'Retained new-row motion mapping domain changed.')
            self.guard_old(ctx, 'readopt_Activate', changed_motion_refs=True)
            self.original_data(rig)
            self.report['protected_action_motions'] = {'custom_base': self.base_sha, 'source_base': self.source_sha, 'custom_input': self.input_sha}
            self.report['native_controller_presentation'] = {'sha256': digest(self.presentation_before), 'proof': self.presentation_before}
            path = self.output / 'original_cosha_recovered.blend'
            require(not path.exists() and self.bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(path), check_existing=False) == {'FINISHED'}
                    and Path(self.bpy.data.filepath).resolve() == path, 'Recovered original clone was not saved at its unique owned path.')
            self.report['saved_scene'] = pin(path, sha(path))
            self.phase = 'open_final_scene'
        self.checkpoint('Restore_readopt_retained_input_saved_old_scope_ended')

    def tick(self):
        try:
            phase = self.phase
            if phase == 'open_latest_seed':
                row = self.pins['latest_seed']
                pin(row['path'], row['sha256'])
                require(self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=row['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'Latest original SaveCopy did not open.')
                self.phase = 'add_activate'
                self.checkpoint('latest_original_seed_opened_new_RNA_deferred_next_tick')
            elif phase == 'add_activate': self.add_activate()
            elif phase == 'edit_save': self.edit_save()
            elif phase == 'undo_inputs': self.undo_redo()
            elif phase == 'check_undo': self.check_undo_redo()
            elif phase == 'redo_inputs': self.undo_redo(redo=True)
            elif phase == 'check_redo': self.check_undo_redo(redo=True)
            elif phase == 'preview_reference': self.preview_reference()
            elif phase == 'save_scene': self.save_scene()
            elif phase in {'open_scene', 'open_final_scene'}:
                row = self.report['saved_scene']
                pin(row['path'], row['sha256'])
                require(self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=row['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'Owned original clone did not reopen.')
                self.phase = 'verify_final_reopen' if phase == 'open_final_scene' else 'verify_reopen'
                self.checkpoint('original_clone_open_returned_old_override_absent')
            elif phase == 'verify_reopen': self.verify_reopen()
            elif phase == 'owned_restore_roundtrip': self.owned_restore_roundtrip()
            elif phase == 'restore_readopt': self.restore_readopt()
            elif phase == 'verify_final_reopen': self.verify_reopen(final=True)
            else: require(phase == 'done', 'Unknown original control phase.')
            if self.phase == 'done' and self.args.quit_on_completion:
                with self.context():
                    returned = self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')
                    self.checkpoint('normal_quit_requested', operator_result=sorted(returned), natural_exit_verified=False)
            return None if self.phase == 'done' else .5
        except Exception as error:
            self.report.update(completed=False, original_clone_Rig_acceptance=False,
                failure_phase=self.phase, error=str(error), traceback=traceback.format_exc())
            self.checkpoint('failed_no_repair_retry_Sync_or_artist_write')
            return None

    def start(self):
        super().start()
        self.fingerprints = __import__('character_designer.animation_worklist_fingerprint', fromlist=['fingerprint_action'])
        require(callable(getattr(self.worklist, 'attach_prepared_rigging_work', None))
                and callable(getattr(self.worklist, 'validate_rigging_entry', None)), 'Future complete package must contain the reviewed original-Rig Attach/public validation APIs.')
        self.runtime_paths()


def main():
    run = OriginalRound(arguments())
    try:
        run.start()
    except Exception as error:
        run.report.update(completed=False, failure_phase='startup', error=str(error), traceback=traceback.format_exc())
        run.checkpoint('startup_failed_no_retry')
        raise


if __name__ == '__main__':
    main()
