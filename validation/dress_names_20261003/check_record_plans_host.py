"""Exercise name-record plans against saved X evidence without importing Blender."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parent
baseline = json.loads((ROOT.parent / 'bone_palette_20261003' / 'actual_x_before_palette.json').read_text(encoding='utf-8'))
protected = baseline['protected']


class Holder:
    def __init__(self, name, props):
        self.name, self.props = name, copy.deepcopy(props)
        self.library = self.override_library = None
        self.is_editable = True

    def get(self, key, default=None):
        return self.props.get(key, default)

    def __getitem__(self, key):
        return self.props[key]

    def __contains__(self, key):
        return key in self.props

    def __deepcopy__(self, memo):
        # Native Blender ID pointers remain shared inside copied properties.
        return self


objects = {name: Holder(name, state['props']) for name, state in protected['objects'].items()}
armatures = {}
for name, state in protected['armatures'].items():
    data_name = protected['objects'][name]['data']['name']
    armatures[data_name] = Holder(data_name, state['props'])
    objects[name].data = armatures[data_name]


def native(value):
    if isinstance(value, dict):
        if value.get('id_type') == 'Object':
            return objects[value['name']]
        return {key: native(item) for key, item in value.items()}
    if isinstance(value, list):
        return [native(item) for item in value]
    return value


for item in (*objects.values(), *armatures.values()):
    item.props = native(item.props)
scene = Holder('Scene', native(protected['scene']['props']))
sys.modules['bpy'] = types.SimpleNamespace(data=types.SimpleNamespace(
    objects=tuple(objects.values()), armatures=tuple(armatures.values()), scenes=(scene,)))
pkg = types.ModuleType('record_check_package')
pkg.__path__ = []
sys.modules[pkg.__name__] = pkg


def module(name, **fields):
    item = types.ModuleType(pkg.__name__ + '.' + name)
    item.__dict__.update(fields)
    sys.modules[item.__name__] = item


def layout(record):
    controls = record['controls']
    selected = {controls[key] for key in ('waist', 'mid', 'hem')}
    selected.update(name for entry in controls['chains'] for name in entry.values())
    return (selected, {name for chain in record['chains'] for name in chain['def']},
            {name for chain in record['chains'] for key in ('manual', 'phys') for name in chain[key]})


module('skirt_rig', RECORD_KEY='character_designer_skirt_v1', OWNER_KEY='character_designer_skirt_owner',
       RIG_KEY='character_designer_skirt_armature', PARENT_KEY='character_designer_skirt_original_parent',
       ATTACHMENT_PARENT_KEY='character_designer_skirt_attachment_previous_parent',
       ATTACHMENT_BACKUP_KEY='character_designer_skirt_attachment_before_update_v1',
       _bone_collection_layout=layout)
module('body_original_mode', SESSION='character_designer_body_original_mode_v1',
       DISPLAY_REFS='character_designer_original_display_refs_v1')
module('skirt_original_mode', CORRECTIONS='character_designer_skirt_pose_corrections_v1')
module('control_weight_paint', SESSION='character_designer_weight_workspace_v1')
module('bone_collections', BACKUP_KEY='character_designer_bone_collections_backup_v1')
module('bone_display', VIEW_KEY='character_designer_bone_display_view_v1', REFS_KEY='character_designer_bone_display_refs_v1')
module('quick_bind', BACKUP_KEY='character_designer_quick_binding_v1', RIG_KEY='character_designer_quick_binding_rig',
       REMOVED_KEY='character_designer_removed_binding_v1', REMOVED_RIG_KEY='character_designer_removed_binding_rig')
path = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\skirt_name_records.py')
spec = importlib.util.spec_from_file_location(pkg.__name__ + '.skirt_name_records', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
source, rig = objects['Dress'], objects['CoshaRig']
record = json.loads(source['character_designer_skirt_v1'])
prefix = 'SK_Dress_' + record['owner'][:6] + '_'
mapping = {name: 'SK_Dress_' + name[len(prefix):] for name in set.union(*layout(record))}
before = {id(item): copy.copy(item.props) for item in (*objects.values(), *armatures.values(), scene)}
plans = helper.snapshots(source, rig, mapping)
assert all(item.props == before[id(item)] for item in (*objects.values(), *armatures.values(), scene)), 'planning mutated an ID'
planned = {(item.name, key): json.loads(updated) for item, key, raw, updated in plans}
new_record = planned[('Dress', 'character_designer_skirt_v1')]
old_session = json.loads(rig['character_designer_body_original_mode_v1'])
new_session = planned[('CoshaRig', 'character_designer_body_original_mode_v1')]
assert new_record['owner'] == record['owner']
assert new_record['shared']['names'] == sorted(mapping[name] for name in record['shared']['names'])
assert new_session['bones'] == sorted(mapping.get(name, name) for name in old_session['bones'])
old_entry = next(entry for entry in old_session['dress_edit'] if entry['owner'] == record['owner'])
new_entry = next(entry for entry in new_session['dress_edit'] if entry['owner'] == record['owner'])
for field in ('channels', 'entered_channels', 'entered_basis', 'locks', 'pose', 'rest', 'constraints'):
    assert new_entry[field] == {mapping.get(name, name): value for name, value in old_entry[field].items()}, field
for field in ('channels', 'entered_channels', 'pose', 'rest'):
    assert new_session[field] == old_session[field], 'unrelated Body/Hair changed: ' + field
palette_keys = ('character_designer_bone_color_palette_v1', '_cd_bone_palette_rigs_v1', '_cd_bone_palette_main_v1')
assert not any(key in palette_keys for _item, key, _raw, _updated in plans)
assert all(raw == item[key] for item, key, raw, _updated in plans)
actual_plans = [(item.name, key) for item, key, _raw, _updated in plans]

# Exact native refs scope auxiliary snapshots; unrelated artist strings stay intact.
old, new = next(iter(mapping.items()))
def encode(value):
    if isinstance(value, dict):
        return {'group': {key: encode(item) for key, item in value.items()}}
    if isinstance(value, list):
        return {'array': [encode(item) for item in value]}
    return value
collection_backup = encode({'original': {'hidden': {old: [False, False]},
    'pose_hidden': {old: False}, 'collections': [{'name': old, 'parent': old,
    'bones': [old], 'properties': {'artist_text': old, 'ref': {'id': 'keep-native-ref'}}}]},
    'managed': [{'name': old, 'bones': [old]}]})
rig.data.props['character_designer_bone_collections_backup_v1'] = json.dumps(collection_backup)
view = {'mode': 'ORIGINAL', 'rigs': {'0': {'hidden': {old: [False, False]}},
                                     '1': {'hidden': {old: [True, True]}}}}
rig.data.props['character_designer_bone_display_view_v1'] = json.dumps(view)
rig.data.props['character_designer_bone_display_refs_v1'] = {'0': rig, '1': objects['Cosha']}
other_data = Holder('Display copy', copy.deepcopy(rig.data.props))
other_data.props['character_designer_bone_display_refs_v1'] = {'0': rig, '1': objects['Cosha']}
qb = Holder('Detached QB', {'character_designer_quick_binding_rig': rig,
    'character_designer_quick_binding_v1': json.dumps({'version': 1, 'names': [old],
        'groups': [{'name': old, 'values': [[1, .42]]}], 'artist_text': old}),
    'character_designer_removed_binding_rig': rig,
    'character_designer_removed_binding_v1': json.dumps({'version': 1, 'parent_removed': True,
        'parent_type': 'BONE', 'parent_bone': old}),
    'character_designer_skirt_attachment_previous_parent': rig,
    'character_designer_skirt_attachment_before_update_v1': json.dumps({'parent_type': 'BONE', 'parent_bone': old})})
bpy = sys.modules['bpy']
bpy.data.objects = (*bpy.data.objects, qb)
bpy.data.armatures = (*bpy.data.armatures, other_data)
aux_plans = helper.snapshots(source, rig, mapping)
aux = {(item.name, key): json.loads(updated) for item, key, _raw, updated in aux_plans}
cb = aux[(rig.data.name, 'character_designer_bone_collections_backup_v1')]['group']
record0 = cb['original']['group']['collections']['array'][0]['group']
assert record0['bones']['array'] == [new]
assert record0['name'] == old and record0['parent'] == old
assert record0['properties'] == collection_backup['group']['original']['group']['collections']['array'][0]['group']['properties']
for data in (rig.data, other_data):
    current = aux[(data.name, 'character_designer_bone_display_view_v1')]
    assert set(current['rigs']['0']['hidden']) == {new}
    assert current['rigs']['1'] == view['rigs']['1']
q = aux[('Detached QB', 'character_designer_quick_binding_v1')]
assert q['names'] == [new] and q['groups'][0]['name'] == new and q['artist_text'] == old
assert aux[('Detached QB', 'character_designer_removed_binding_v1')]['parent_bone'] == new
assert aux[('Detached QB', 'character_designer_skirt_attachment_before_update_v1')]['parent_bone'] == new
assert all(raw == item[key] for item, key, raw, _updated in aux_plans), 'aux planning mutated an ID'
for key, value, holder in [('character_designer_skirt_bake_preview', '{}', source),
                           ('character_designer_weight_workspace_v1', {'rig': rig}, scene)]:
    holder.props[key] = value
    try:
        helper.snapshots(source, rig, mapping)
    except ValueError:
        pass
    else:
        raise AssertionError('active recovery state was not rejected: ' + key)
    del holder.props[key]
print(json.dumps({'passed': True, 'mapped_bones': len(mapping), 'actual_x_plans': actual_plans,
                  'auxiliary_schemas_passed': 5, 'active_recovery_refusals_passed': 2,
                  'no_blender_import': True, 'ids_unchanged': True}, ensure_ascii=False, indent=2))
