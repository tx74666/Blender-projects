"""Append the preserved Fist Action and retain both Poses in the external library."""
import hashlib
import json
from array import array
from pathlib import Path

import bpy
from character_designer import animation_retarget, control_pose_assets as poses
from character_designer import body_original_mode as original
from character_designer.control_pose_capture import _show_current_file

folder = Path(__file__).resolve().parent
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
arm_name = 'Arm Flat'
external_arm = source.parent / (arm_name + '.asset.blend')
expected_source = '0092ee46255e2101c72df5e78f0504bfdf789486ea72c2646c8f273cc8713cbb'
if Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('Unexpected artist file; nothing imported.')
rig = bpy.context.view_layer.objects.active
if rig is None or rig.name != 'CoshaRig' or rig.type != 'ARMATURE':
    raise RuntimeError('Expected active CoshaRig; nothing imported.')
if bpy.context.area is None or bpy.context.area.type != 'CONSOLE':
    raise RuntimeError('Run from the temporary artist Console.')
if hashlib.sha256(source.read_bytes()).hexdigest() != expected_source:
    raise RuntimeError('Protected Fist source changed.')
if (folder / 'saved.json').exists():
    raise RuntimeError('A completion receipt already exists; inspect before repeating.')

def fingerprint(action):
    def plain(value):
        if hasattr(value, 'to_dict'):
            return {k: plain(v) for k, v in value.to_dict().items()}
        if hasattr(value, 'to_list'):
            return [plain(v) for v in value.to_list()]
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        if value is None or isinstance(value, (str, float, int, bool)):
            return value
        raise RuntimeError('Unsupported custom Action property; faithful copy cannot be verified.')
    def properties(value):
        result = {}
        for prop in value.bl_rna.properties:
            if prop.identifier == 'rna_type' or prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
                continue
            item = getattr(value, prop.identifier)
            result[prop.identifier] = (list(item) if getattr(prop, 'is_array', False) else
                                       sorted(item) if isinstance(item, set) else item)
        return result
    def curve_data(curve):
        return {'properties': properties(curve),
                'group': curve.group.name if curve.group else None,
                'keys': [properties(key) for key in curve.keyframe_points],
                'samples': [properties(point) for point in curve.sampled_points],
                'modifiers': [properties(modifier) for modifier in curve.modifiers]}
    def bag_data(bag):
        return {'slot_handle': bag.slot_handle,
                'curves': [curve_data(curve) for curve in bag.fcurves]}
    layout = [{'properties': properties(layer),
               'strips': [{'properties': properties(strip),
                           'bags': [bag_data(bag) for bag in strip.channelbags]}
                          for strip in layer.strips]} for layer in action.layers]
    return {
        'slots': [(s.identifier, s.target_id_type) for s in action.slots],
        'curves': [(c.data_path, c.array_index, c.mute, c.extrapolation,
                    [(list(k.co), k.interpolation, list(k.handle_left), list(k.handle_right))
                     for k in c.keyframe_points])
                   for c in animation_retarget._curves(action, None)],
        'curve_details': [curve_data(c) for c in animation_retarget._curves(action, None)],
        'layout': layout,
        'properties': {k: plain(action[k]) for k in action.keys() if k != 'asset_data'},
    }

def preview(action):
    item = action.preview
    if item is None:
        return None
    def pixel_hash(values):
        return hashlib.sha256(array('I', (int(value) & 0xffffffff for value in values)).tobytes()).hexdigest()
    return {'size': list(item.image_size), 'pixels': pixel_hash(item.image_pixels),
            'icon_size': list(item.icon_size), 'icon_pixels': pixel_hash(item.icon_pixels),
            'is_image_custom': item.is_image_custom, 'is_icon_custom': item.is_icon_custom}

def asset_details(action):
    return {'author': action.asset_data.author, 'description': action.asset_data.description,
            'catalog_id': action.asset_data.catalog_id,
            'tags': sorted(t.name for t in action.asset_data.tags)}

def artist_state():
    bpy.context.view_layer.update()
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    animation = rig.animation_data
    assigned = animation.action if animation else None
    return {
        'mode': bpy.context.mode,
        'frame': (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe),
        'active': rig.name,
        'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
        'selected': sorted(b.name for b in rig.pose.bones
                           if (b if hasattr(b, 'select') else b.bone).select),
        'assigned': assigned.name if assigned else None,
        'slot': animation.action_slot.identifier if animation and animation.action_slot else None,
        'assigned_data': fingerprint(assigned) if assigned else None,
        'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
        'original': rig.get(original.SESSION),
        'channels': {b.name: {p: list(getattr(b, p)) for p in poses._TRANSFORMS} | {
            'rotation_mode': b.rotation_mode, 'ik_fk': b.get('ik_fk')}
            for b in rig.pose.bones},
        'matrices': {b.name: [list(r) for r in b.matrix] for b in evaluated.pose.bones},
        'objects': sorted(bpy.data.objects.keys()),
        'armatures': sorted(bpy.data.armatures.keys()),
        'meshes': sorted(bpy.data.meshes.keys()),
        'materials': sorted(bpy.data.materials.keys()),
    }

with bpy.types.BlendData.temp_data() as temporary:
    with temporary.libraries.load(str(source)) as (available, requested):
        if 'Fist' not in available.actions:
            raise RuntimeError('Expected Fist Action is missing.')
        requested.actions = ['Fist']
    template = requested.actions[0]
    if temporary.objects or temporary.armatures or temporary.meshes or temporary.materials:
        raise RuntimeError('Fist references unexpected scene data; nothing imported.')
    expected_data, expected_preview = fingerprint(template), preview(template)
    if not template.asset_data:
        raise RuntimeError('The protected Fist is not marked as an asset.')
    expected_asset = asset_details(template)
    catalog = template.asset_data.catalog_id
    try:
        values = poses.channels(template, rig)
        compatibility = {'readable': True, 'names': sorted(values),
                         'control_matching_needed': poses._needs_control_matching(rig, values)}
    except (ValueError, RuntimeError, KeyError, TypeError) as error:
        compatibility = {'readable': False, 'reason': str(error)}

arm = bpy.data.actions.get(arm_name)
if arm is None or arm.asset_data is None or poses.asset_metadata(arm) is None:
    raise RuntimeError('The confirmed current Arm Flat Pose is unavailable; nothing imported.')
if sorted(poses.asset_metadata(arm)['names']) != ['forearm.L', 'hand.L', 'shoulder.L', 'upper_arm.L']:
    raise RuntimeError('The arm Pose has unexpected scope; nothing imported.')
arm_data, arm_preview, arm_asset = fingerprint(arm), preview(arm), asset_details(arm)
external_asset = dict(arm_asset, catalog_id=catalog)
if external_arm.exists():
    with bpy.types.BlendData.temp_data() as temporary:
        with temporary.libraries.load(str(external_arm)) as (available, requested):
            if arm.name not in available.actions:
                raise RuntimeError('An external arm file already exists with different contents.')
            requested.actions = [arm.name]
        existing = requested.actions[0]
        if (fingerprint(existing) != arm_data or preview(existing) != arm_preview
                or not existing.asset_data or asset_details(existing) != external_asset):
            raise RuntimeError('An external arm file already exists with different contents.')

before = artist_state()
original_actions = {a.name: fingerprint(a) for a in bpy.data.actions}
before_dirty = bpy.data.is_dirty
checkpoint = folder / 'X_before_fist_import.blend'
if checkpoint.exists():
    raise RuntimeError('Checkpoint already exists; inspect before repeating.')
if bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True) != {'FINISHED'}:
    raise RuntimeError('Could not preserve the complete unsaved scene.')

action = bpy.data.actions.get('Fist')
if action is not None and (action.library or fingerprint(action) != expected_data
                           or action.asset_data is None or asset_details(action) != expected_asset
                           or preview(action) != expected_preview):
    action = None
if action is None:
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        requested.actions = ['Fist']
    action = requested.actions[0]
    if action.name != 'Fist':
        action.name = 'Fist 库副本'
if (action.library or fingerprint(action) != expected_data or preview(action) != expected_preview
        or action.asset_data is None or asset_details(action) != expected_asset):
    raise RuntimeError('Appended Fist does not match its protected source; scene not saved.')
action.use_fake_user = True
if action.asset_data is None:
    action.asset_mark()

if external_arm.exists():
    with bpy.types.BlendData.temp_data() as temporary:
        with temporary.libraries.load(str(external_arm)) as (available, requested):
            if arm.name not in available.actions:
                raise RuntimeError('An external arm file already exists with different contents.')
            requested.actions = [arm.name]
        existing = requested.actions[0]
        if (fingerprint(existing) != arm_data or preview(existing) != arm_preview
                or not existing.asset_data or asset_details(existing) != external_asset):
            raise RuntimeError('An external arm file already exists with different contents.')
else:
    stage = folder / 'arm_pose_original.asset.blend'
    ready = folder / 'arm_pose_library.asset.blend'
    if stage.exists() or ready.exists():
        raise RuntimeError('Arm export staging exists; inspect before repeating.')
    bpy.data.libraries.write(str(stage), {arm}, fake_user=True, compress=True)
    with bpy.types.BlendData.temp_data() as temporary:
        with temporary.libraries.load(str(stage)) as (available, requested):
            requested.actions = [arm.name]
        copied = requested.actions[0]
        copied.asset_data.catalog_id = catalog
        temporary.libraries.write(str(ready), {copied}, fake_user=True, compress=True)
    with bpy.types.BlendData.temp_data() as temporary:
        with temporary.libraries.load(str(ready)) as (available, requested):
            requested.actions = [arm.name]
        copied = requested.actions[0]
        if (fingerprint(copied) != arm_data or preview(copied) != arm_preview
                or not copied.asset_data or asset_details(copied) != external_asset):
            raise RuntimeError('External arm backup validation failed.')
    # Exclusive creation preserves any external asset produced concurrently.
    with external_arm.open('xb') as destination:
        destination.write(ready.read_bytes())
    if external_arm.read_bytes() != ready.read_bytes():
        raise RuntimeError('External arm copy differs from the validated staging file.')

after = artist_state()
max_error = max(abs(x-y) for n, rows in before['matrices'].items()
                for left, right in zip(rows, after['matrices'][n]) for x,y in zip(left,right))
if (any(before[k] != after[k] for k in before if k != 'matrices') or max_error > 4e-6
        or any(fingerprint(bpy.data.actions[n]) != data for n, data in original_actions.items())):
    raise RuntimeError('Protected artist state changed; final save stopped.')
if hashlib.sha256(source.read_bytes()).hexdigest() != expected_source:
    raise RuntimeError('The protected external Fist source changed.')
_show_current_file(bpy.context)
receipt = {'source': str(source), 'source_sha256': expected_source,
           'source_unchanged': True, 'local_asset': action.name,
           'fist_curves': len(expected_data['curves']), 'fist_slots': expected_data['slots'],
           'fist_preview': expected_preview, 'fist_compatibility': compatibility,
           'fist_asset_details': expected_asset, 'max_pose_matrix_error': max_error,
           'existing_actions_preserved': sorted(original_actions),
           'artist_state_unchanged': True, 'dirty_before': before_dirty,
           'checkpoint': str(checkpoint), 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
           'external_arm': str(external_arm), 'external_arm_sha256': hashlib.sha256(external_arm.read_bytes()).hexdigest(),
           'local_assets': [a.name for a in bpy.data.actions if a.asset_data],
           'mode': before['mode'], 'frame': before['frame'], 'selected': before['selected']}
(folder / 'imported.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
window, area = bpy.context.window, bpy.context.area

def assert_preserved():
    if Path(bpy.data.filepath).resolve() != artist.resolve() or bpy.context.view_layer.objects.active != rig:
        raise RuntimeError('Artist identity changed before final save.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected_source:
        raise RuntimeError('Protected source changed before final save.')
    state = artist_state()
    error = max(abs(x-y) for n, rows in before['matrices'].items()
                for left, right in zip(rows, state['matrices'][n]) for x,y in zip(left,right))
    if (any(before[k] != state[k] for k in before if k != 'matrices') or error > 4e-6
            or any(fingerprint(bpy.data.actions[n]) != data for n, data in original_actions.items())):
        raise RuntimeError('Artist state changed around final save.')
    if (fingerprint(action) != expected_data or preview(action) != expected_preview
            or not action.asset_data or asset_details(action) != expected_asset):
        raise RuntimeError('Imported Fist changed around final save.')
    if fingerprint(arm) != arm_data or preview(arm) != arm_preview or asset_details(arm) != arm_asset:
        raise RuntimeError('Current arm Pose changed around final save.')
    return error

def finish():
    try:
        assert_preserved()
        area.type = 'NODE_EDITOR'
        area.ui_type = 'ShaderNodeTree'
        with bpy.context.temp_override(window=window):
            result = bpy.ops.wm.save_as_mainfile(filepath=str(artist))
        if result != {'FINISHED'}:
            raise RuntimeError('Artist save was not confirmed.')
        receipt['post_save_matrix_error'] = assert_preserved()
        receipt.update(saved_file=str(artist), save_result=sorted(result),
                       artist_sha256=hashlib.sha256(artist.read_bytes()).hexdigest(),
                       artist_bytes=artist.stat().st_size)
        (folder / 'saved.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        print('FIST_AND_ARM_SAVED_IN_BOTH_LOCATIONS', receipt['local_assets'])
    except Exception as error:
        (folder / 'save_error.json').write_text(json.dumps({'error': repr(error)}), encoding='utf-8')
        raise
    return None

bpy.app.timers.register(finish, first_interval=.5)
print('FIST_IMPORTED_AND_ARM_EXTERNAL_BACKUP_VERIFIED; ARTIST_SAVE_QUEUED')
