"""Pure fault injection for actual Rigging display transactions, not native QA.

Only recovery functions are AST-loaded. Fake native IDs model ownership and
links; no Blender operators, solver, frame evaluation or external process runs.
"""
import ast
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid


SOURCE = Path(__file__).resolve().parents[1] / 'addons' / 'character_designer'


def functions(path, names, namespace):
    nodes = [node for node in ast.parse(path.read_text(encoding='utf-8')).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise AssertionError('The recovery API changed: ' + str(names))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


class Group(dict):
    def to_dict(self):
        return dict(self)


def property_value(value):
    if isinstance(value, dict) and not isinstance(value, Native):
        return Group({key: property_value(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return [property_value(item) for item in value]
    return value


class Native(dict):
    """An ID reference is identity-based, even when its properties are empty."""
    def __init__(self, name, **fields):
        super().__init__()
        self.name, self.removed, self.library = name, False, None
        self.__dict__.update(fields)

    def __setitem__(self, key, value):
        fault = getattr(self, 'write_fault', None)
        if fault is not None and fault(key, value):
            self.write_fault = None
            raise RuntimeError('injected second session store failure')
        super().__setitem__(key, property_value(value))

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    __hash__ = object.__hash__

    def __bool__(self):
        return True

    def __deepcopy__(self, _memo):
        return self

    def as_pointer(self):
        return id(self)


class Armature(Native):
    pass


class Action(Native):
    @property
    def users(self):
        return int(self.use_fake_user)


class Links:
    def __init__(self, root):
        self.root, self.members, self.fail_unlink = root, [], False

    def __contains__(self, value):
        return value in self.members

    def __iter__(self):
        return iter(self.members)

    def get(self, name):
        return next((value for value in self.members if value.name == name), None)

    def link(self, value):
        if value not in self.members:
            self.members.append(value)
            value.parents.add(self.root)

    def unlink(self, value):
        if self.fail_unlink:
            self.fail_unlink = False
            raise RuntimeError('injected Scene unlink failure')
        self.members.remove(value)
        value.parents.remove(self.root)


class Collection(Native):
    def __init__(self, name, world):
        super().__init__(name, objects=[], parents=set())
        self.world, self.children = world, Links(self)

    @property
    def users(self):
        record = self.world.rig.get(self.world.weapon.RECORD)
        return len(self.parents) + int(record is not None and record.get('collection') is self)


class Table(list):
    def get(self, name):
        return next((value for value in self if value.name == name), None)

    def remove(self, value, **_kwargs):
        value.removed = True
        super().remove(value)
        if isinstance(value, Collection):
            for root in tuple(value.parents):
                root.children.unlink(value)
        else:
            for collection in tuple(getattr(self, 'collections', ())):
                if value in collection.objects:
                    collection.objects.remove(value)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        package_name = '_rigging_recovery_' + uuid.uuid4().hex
        package = ModuleType(package_name)
        package.__path__ = []
        self.weapon = ModuleType(package_name + '.animation_composition_weapon')
        self.weapon.RECORD, self.weapon.SCHEMA = 'owned_weapon', 'cdesigner.weapon-context/1'
        self.weapon.OWNER = 'weapon_owner'
        self.rig = Native('Original Rig', type='ARMATURE', data=Armature('Original bones'),
                          matrix_world=[1.], pose_state={'target': 'current unkeyed drag'})
        self.root = Collection('Scene root', self)
        self.scene = Native('Artist Scene', collection=self.root,
                            unit_settings=SimpleNamespace(scale_length=1.))
        self.base = Action('Base Custom', use_fake_user=True)
        self.inputs = Action('Target inputs', use_fake_user=True)
        self.context = SimpleNamespace(scene=self.scene)
        self.rig.animation_data = SimpleNamespace(use_tweak_mode=False, use_nla=False,
            action=self.base, action_slot_handle=4, nla_tracks=Table())
        objects, collections = Table([self.rig]), Table()
        objects.collections = collections
        data = SimpleNamespace(objects=objects, collections=collections,
            actions=Table([self.base, self.inputs]), scenes=Table([self.scene]))
        data.user_map = self.user_map
        self.bpy = SimpleNamespace(types=SimpleNamespace(ID=Native, Object=Native,
            Collection=Collection, Scene=Native, Action=Action, Armature=Armature), data=data)
        self.modules = patch.dict(sys.modules, {package_name: package,
            self.weapon.__name__: self.weapon, 'bpy': self.bpy})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.composition = SimpleNamespace()
        serializer = {'bpy': self.bpy}
        functions(SOURCE / 'animation_composition.py', {'_encode', '_decode'}, serializer)
        self.composition._encode, self.composition._decode = serializer['_encode'], serializer['_decode']
        copy_namespace = {}
        functions(SOURCE / 'bone_collections.py', {'_copy_property'}, copy_namespace)
        self.copy_property = copy_namespace['_copy_property']
        self.composition._prior = lambda _context, rig: {'pose': deepcopy(rig.pose_state)}
        self.composition._restore_prior = lambda _context, rig, prior: setattr(rig, 'pose_state', deepcopy(prior['pose']))
        self.composition._slot = lambda _action, slot: SimpleNamespace(handle=slot)
        self.composition.active = lambda _rig: False
        self.composition._tweak = lambda *_args, **_kwargs: None
        self.display = {'groups': ['Original', 'Body'], 'color': 'original'}
        bone_display = SimpleNamespace(_snapshot=lambda _rig: deepcopy(self.display),
                                      _restore=lambda _rig, saved: self.display.update(saved))
        names = {'_require', '_digest', '_uid', '_detached', '_store', 'current',
            'restore_owned', '_capture_owned', '_weapon_token', '_detach_weapon',
            '_return_weapon', '_consume_token', '_finish_owned_state',
            '_restore_owned_state', 'snapshot_base_refs', 'import_inputs'}
        self.n = {'__package__': package_name, 'bpy': self.bpy, 'json': json,
            'uuid': uuid, 'hashlib': hashlib, 'deepcopy': deepcopy,
            'contextmanager': contextmanager, 'composition': self.composition,
            'bone_display': bone_display,
            'bone_collections': SimpleNamespace(_copy_property=self.copy_property),
            'SESSION_KEY': 'owned_session', '_REFS_KEY': 'owned_refs',
            'CAPTURE_KEY': 'original_capture', '_INPUT_REF': 'input_ref',
            '_INPUT_META': 'input_owner', '_INPUT_BASE': 'input_base',
            '_CACHE': {}, '_BUSY': set(), '_SUSPENDED': {}, '_HANDLER_ERRORS': {},
            '_OWNED_TOKENS': {}, '_SIDES': ('Right', 'Left'),
            '_FIELDS': (('targetPosition', 3), ('targetRotation', 4), ('hintPosition', 3)),
            '_property': lambda side, field: side + '_' + field,
            '_validate': lambda _session: None, '_motion': lambda _action, _slot: 'f' * 64,
            '_tracks': lambda _session: {}, '_remove_handlers_if_idle': lambda: None,
            '_restore_live_pose': lambda rig, prior: setattr(rig, 'pose_state', deepcopy(prior['pose'])),
            '_rows': lambda matrix: list(matrix), '_binding_plan': lambda *_args: [],
            '_curves': lambda *_args: None}
        functions(SOURCE / 'unity_animation_rigging.py', names, self.n)
        self.n['activate'] = self.activate
        self.weapon.__dict__.update(bpy=self.bpy, _require=self.n['_require'],
            re=__import__('re'), _ASSET_TABLES=(), _remove_unused_assets=lambda _assets: None,
            _host=lambda _name: SimpleNamespace(current=self.n['current']))
        functions(SOURCE / 'animation_composition_weapon.py',
            {'validate_owned', 'remove_context', 'remove_rigging_context'}, self.weapon.__dict__)
        self.capture = {'newActionId': '2' * 32, 'previewEnabled': True,
                        'sampleRate': 2., 'weaponPreview': {'display': 'fixture'}}
        self.session = dict(version=1, owner=str(uuid.uuid4()), rig=self.rig, scene=self.scene,
            capture=self.capture, base_action=self.base, base_slot=4, input_action=self.inputs,
            input_slot=7, new_action_id='2' * 32, work_item_id='1' * 32,
            source_packet_sha256='a' * 64, source_read_only=False,
            prior={'pose': {'target': 'entry pose'}}, display=deepcopy(self.display),
            tracks={}, properties_before={}, enabled=True, edit_role='RIGGING',
            tweak_enabled=False, committed=True, _time=.5, _left_parent=[1.])
        self.old_record = self.install_display(self.session, 'Old display')
        self.n['_store'](self.rig, self.session)

    def user_map(self):
        users = {}
        record = self.rig.get(self.weapon.RECORD)
        if record is not None:
            users[record['collection']] = {self.rig, self.root}
            for obj in record['objects'].values():
                users[obj] = {self.rig, record['collection']}
        if getattr(self, 'external_user', False) and record is not None:
            users[next(iter(record['objects'].values()))].add(self.base)
        return users

    def install_display(self, session, name):
        owner = str(uuid.uuid4())
        collection = Collection(name, self)
        obj = Native(name + ' mesh', users_collection={collection})
        obj[self.weapon.OWNER] = collection[self.weapon.OWNER] = owner
        collection.objects.append(obj)
        self.bpy.data.objects.append(obj)
        self.bpy.data.collections.append(collection)
        self.root.children.link(collection)
        self.rig[self.weapon.RECORD] = {'schema': self.weapon.SCHEMA, 'owner': owner,
            'collection': collection, 'scene': self.scene, 'scene_root': self.root,
            'objects': {'mesh': obj}, 'assets': {}, 'identity': name,
            'rigging_session_owner': session['owner']}
        session['weapon_preview'] = {'display_owner': owner, 'identity': name,
            'record_key': self.weapon.RECORD, 'rigging_session_owner': session['owner']}
        return self.copy_property(self.rig[self.weapon.RECORD])

    def activate(self, _context, session, *, edit_role, enabled):
        # Solver/display formulas are outside this test. Restore state ordering
        # is exercised by the actual transaction around this boundary.
        session.update(enabled=True, edit_role=edit_role, tweak_enabled=enabled)
        self.rig.pose_state = {'target': 'activation evaluation'}
        self.n['_store'](self.rig, session)

    def detach(self):
        token = self.n['_capture_owned'](self.context, self.rig)
        self.n['restore_owned'](self.context, self.rig)
        return token

    def assert_record_ids(self, expected):
        actual = self.rig[self.weapon.RECORD]
        self.assertIs(actual['collection'], expected['collection'])
        self.assertIs(actual['scene'], expected['scene'])
        self.assertIs(actual['objects']['mesh'], expected['objects']['mesh'])
        self.assertEqual(self.copy_property(actual), expected)

    def test_failed_worklist_rollback_restores_same_ids_session_and_live_pose(self):
        original_pose = deepcopy(self.rig.pose_state)
        token = self.detach()
        self.assertEqual(token['status'], 'detached')
        self.assertNotIn(self.weapon.RECORD, self.rig)
        self.assertEqual(self.old_record['collection'].users, 0)
        self.assertFalse(self.old_record['objects']['mesh'].removed)
        self.n['_restore_owned_state'](self.context, self.rig, token)
        self.assert_record_ids(self.old_record)
        recovered = self.n['current'](self.rig)
        self.assertIs(recovered['base_action'], self.base)
        self.assertIs(recovered['input_action'], self.inputs)
        self.assertEqual((recovered['base_slot'], recovered['input_slot']), (4, 7))
        self.assertEqual((recovered['enabled'], recovered['edit_role'], recovered['tweak_enabled']),
                         (True, 'RIGGING', False))
        self.assertEqual(self.rig.pose_state, original_pose)
        self.assertEqual(recovered['_time'], .5)
        self.assertEqual(token['status'], 'restored')
        self.assertEqual(self.n['_OWNED_TOKENS'], {})

    def test_commit_releases_only_old_geometry_and_keeps_new_native_ids(self):
        token = self.detach()
        new_session = dict(self.session, owner=str(uuid.uuid4()))
        new_record = self.install_display(new_session, 'New display')
        self.n['_store'](self.rig, new_session)
        self.n['_finish_owned_state'](self.context, self.rig, token)
        self.assertTrue(self.old_record['collection'].removed)
        self.assertTrue(self.old_record['objects']['mesh'].removed)
        self.assertFalse(new_record['collection'].removed)
        self.assertFalse(new_record['objects']['mesh'].removed)
        self.assert_record_ids(new_record)
        self.assertIs(self.n['current'](self.rig)['rig'], self.rig)
        self.assertFalse(self.rig.removed or self.base.removed or self.inputs.removed)
        self.assertEqual(token['status'], 'finished')
        self.assertEqual(self.n['_OWNED_TOKENS'], {})

    def test_detach_link_failure_restores_original_record_and_pending_token(self):
        token = self.n['_capture_owned'](self.context, self.rig)
        self.root.children.fail_unlink = True
        with self.assertRaisesRegex(RuntimeError, 'unlink failure'):
            self.n['restore_owned'](self.context, self.rig)
        self.assert_record_ids(self.old_record)
        self.assertIs(self.root.children.get(self.old_record['collection'].name), self.old_record['collection'])
        self.assertEqual(token['status'], 'pending')
        self.assertFalse(self.old_record['objects']['mesh'].removed)

    def test_failed_commit_guard_retains_old_and_restores_new_record(self):
        token = self.detach()
        new_session = dict(self.session, owner=str(uuid.uuid4()))
        new_record = self.install_display(new_session, 'New display')
        self.external_user = True
        with self.assertRaisesRegex(ValueError, 'external object'):
            self.n['_finish_owned_state'](self.context, self.rig, token)
        self.assert_record_ids(new_record)
        self.assertEqual(token['status'], 'detached')
        self.assertEqual(self.old_record['collection'].users, 0)
        self.assertFalse(self.old_record['objects']['mesh'].removed)
        self.assertFalse(new_record['objects']['mesh'].removed)

    def test_second_store_import_failure_removes_created_geometry_and_session(self):
        self.weapon.remove_context(self.context, self.rig)
        self.rig.pop(self.n['SESSION_KEY'])
        self.rig.pop(self.n['_REFS_KEY'])
        self.n['_CACHE'].clear()
        self.base['packet_sha'] = 'a' * 64
        self.n['ua'] = SimpleNamespace(PACKAGE_HASH_KEY='packet_sha',
            native_action_frame_rate=lambda _action: 2.,
            _mapping=lambda *_args: SimpleNamespace(conversion=[1.]), _rest_state=lambda _data: {})
        self.n['contract'] = SimpleNamespace(validate_capture=lambda value, **_kwargs: deepcopy(value))
        self.n['_new_input_action'] = lambda *_args: (self.inputs, 7, {'new_action_id': '2' * 32})
        created = []

        def add(_context, _rig, _preview, _packet, _mapping, *, session):
            created.append(self.install_display(session, 'Failed import display'))
            return session['weapon_preview']

        self.weapon.add_rigging_context = add
        actual_store, calls = self.n['_store'], []
        self.rig.write_fault = lambda key, value: (
            key == self.n['SESSION_KEY'] and '"weapon_preview"' in value)

        def fail_second(rig, session):
            calls.append('weapon_preview' in session)
            return actual_store(rig, session)

        self.n['_store'] = fail_second
        with self.assertRaisesRegex(RuntimeError, 'second session store'):
            self.n['import_inputs'](self.context, self.rig,
                {'rigging': self.capture, '_sha256': 'a' * 64}, base_action=self.base,
                base_slot=4, work_item_id='1' * 32)
        self.assertEqual(calls, [False, True])
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0]['collection'].removed)
        self.assertTrue(created[0]['objects']['mesh'].removed)
        self.assertNotIn(self.weapon.RECORD, self.rig)
        self.assertNotIn(self.n['SESSION_KEY'], self.rig)
        self.assertNotIn(self.n['_REFS_KEY'], self.rig)
        self.assertNotIn(self.n['CAPTURE_KEY'], self.base)
        self.assertNotIn(self.n['_INPUT_REF'], self.base)
        self.assertFalse(self.base.removed or self.rig.removed)

    def test_snapshot_tuple_shape_and_native_references_restore_after_write_failure(self):
        self.rig['Right_targetPosition'] = [1., 2., 3.]
        self.base[self.n['_INPUT_REF']] = self.inputs
        self.n['_SUSPENDED'][self.rig.as_pointer()] = 1
        for failure in (False, True):
            with self.subTest(write_failure=failure):
                try:
                    with self.n['snapshot_base_refs'](self.rig, self.base):
                        self.assertNotIn(self.weapon.RECORD, self.rig)
                        self.assertNotIn(self.n['SESSION_KEY'], self.rig)
                        self.assertNotIn(self.n['_INPUT_REF'], self.base)
                        if failure:
                            raise RuntimeError('injected snapshot write failure')
                except RuntimeError as error:
                    self.assertTrue(failure)
                    self.assertEqual(str(error), 'injected snapshot write failure')
                self.assert_record_ids(self.old_record)
                self.assertIs(self.base[self.n['_INPUT_REF']], self.inputs)
                self.assertEqual(self.rig['Right_targetPosition'], [1., 2., 3.])
                self.assertIs(self.n['current'](self.rig)['base_action'], self.base)
                self.assertFalse(self.old_record['objects']['mesh'].removed)

    def test_copied_unregistered_weapon_token_cannot_detach_old_display(self):
        token = self.n['_capture_owned'](self.context, self.rig)
        forged = dict(token)
        with self.assertRaisesRegex(ValueError, 'not this native transaction'):
            self.n['_detach_weapon'](self.rig, forged)
        self.assert_record_ids(self.old_record)
        self.assertEqual(token['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
