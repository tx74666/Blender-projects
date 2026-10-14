"""Owned empty-factory Pose library readback; never opens or saves artist X."""
import argparse
import bpy
import hashlib
import json
import sys
from pathlib import Path
import traceback

ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012').resolve()
WRITER_SHA = '702aa1b69291cba7e8bc722d3324507f8d412043a6b15503d97a4b9fb9cc5458'
REPORT_SHA = '6ac66dc320e88238075a243586cdb92b535da14cc4decf912886dedb912296d4'
BACKUP_SHA = 'c956d715940c7a92ea19a85e26997498a7bda0b0d86a300a443ba507e0055dc6'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def curves(action):
    if action.is_action_layered:
        return [curve for layer in action.layers for strip in layer.strips
                for bag in strip.channelbags for curve in bag.fcurves]
    return list(action.fcurves)


def pose_content(action):
    result = {'name': action.name, 'custom_properties': {key: action[key] for key in action.keys()},
        'slots': [{'handle': slot.handle, 'identifier': slot.identifier, 'name_display': slot.name_display,
                   'target_id_type': slot.target_id_type} for slot in action.slots],
        'layer_names': [layer.name for layer in action.layers],
        'layout': [{'name': layer.name, 'strips': [{'type': strip.type,
            'channelbags': [{'slot_handle': bag.slot_handle,
                'curves': [[curve.data_path, curve.array_index] for curve in bag.fcurves]}
                for bag in strip.channelbags]} for strip in layer.strips]} for layer in action.layers],
        'curves': []}
    for curve in curves(action):
        result['curves'].append({'data_path': curve.data_path, 'array_index': curve.array_index,
            'mute': curve.mute, 'lock': curve.lock, 'extrapolation': curve.extrapolation,
            'group': curve.group.name if curve.group else None,
            'modifiers': [(modifier.type, modifier.name, modifier.mute) for modifier in curve.modifiers],
            'sampled': [list(point.co) for point in curve.sampled_points],
            'keys': [{'co': list(key.co), 'left': list(key.handle_left), 'right': list(key.handle_right),
                'interpolation': key.interpolation, 'easing': key.easing, 'type': key.type,
                'left_type': key.handle_left_type, 'right_type': key.handle_right_type,
                'back': key.back, 'amplitude': key.amplitude, 'period': key.period,
                'selected': [key.select_control_point, key.select_left_handle, key.select_right_handle]}
                for key in curve.keyframe_points]})
    return result



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report', required=True)
    parser.add_argument('--write-report-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    report_path = Path(args.write_report).resolve()
    assert report_path == ROUND / 'Pose-preservation_01/Pose_library_write_report.json'
    raw = report_path.read_bytes()
    assert args.write_report_sha256 == REPORT_SHA and hashlib.sha256(raw).hexdigest() == REPORT_SHA
    assert len(raw) == 496343
    written = json.loads(raw)
    assert written['schema'] == 'x.validation.original-Pose-library-write/1'
    assert written['write_completed'] is True and written['original_state_unchanged'] is True
    assert written['artist_saved'] is False and written['requested_datablocks'] == ['Action:Pose']
    expected = written['pose_content']
    assert digest(expected) == written['before']['pose_content_sha256']
    assert written['before'] == written['after']
    backup = written['backup']
    backup_path = Path(backup['path']).resolve()
    assert backup_path == ROUND / 'Pose-preservation_01/Pose.blend'
    backup_raw = backup_path.read_bytes()
    assert backup['sha256'] == BACKUP_SHA and backup['bytes'] == 95415
    assert len(backup_raw) == 95415 and hashlib.sha256(backup_raw).hexdigest() == BACKUP_SHA
    output = Path(args.output).resolve()
    assert output.is_relative_to(ROUND) and output != backup_path.parent and not output.exists()
    output.mkdir()
    result = {'schema': 'x.validation.original-Pose-library-readback/1', 'completed': False,
        'artist_opened_or_saved': False, 'write_report': {'path': str(report_path),
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}, 'backup': backup,
        'writer_source_sha256': WRITER_SHA, 'available_IDs': {}, 'actions_loaded': [],
        'content_equal': False, 'fake_user_after_append': None, 'fake_user_in_library': None, 'user_count_after_load': None}
    try:
        # This initialization is confined to the separately owned readback child.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        assert not bpy.data.objects and not bpy.data.actions and bpy.data.filepath == ''
        with bpy.data.libraries.load(str(backup_path), link=False) as (available, requested):
            for name in dir(available):
                if name.startswith('_'):
                    continue
                value = getattr(available, name)
                if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
                    result['available_IDs'][name] = list(value)
            assert available.actions == ['Pose'], 'The action library must contain exactly Pose.'
            assert not any(values for name, values in result['available_IDs'].items() if name != 'actions'), 'Unexpected non-Action library ID.'
            requested.actions = ['Pose']
        result['actions_loaded'] = [action.name if action else None for action in requested.actions]
        assert result['actions_loaded'] == ['Pose'] and len(bpy.data.actions) == 1
        action = requested.actions[0]
        actual = pose_content(action)
        result.update(actual_pose_content=actual, actual_content_sha256=digest(actual),
            expected_content_sha256=digest(expected), content_equal=actual == expected,
            fake_user_after_append=action.use_fake_user, user_count_after_load=action.users,
            is_asset=action.asset_data is not None, objects_created=len(bpy.data.objects))
        assert actual == expected, 'Pose layers/strips/channelbags/slots/curves/keys/metadata changed.'
        assert action.asset_data is None
        assert len(curves(action)) == 360 and sum(len(curve.keyframe_points) for curve in curves(action)) == 360
        assert not bpy.data.objects and bpy.data.filepath == ''
        # Append clears the source fake-user flag by default; inspect persisted flag by opening only the owned library.
        bpy.ops.wm.open_mainfile(filepath=str(backup_path), load_ui=False)
        opened = bpy.data.actions.get('Pose')
        assert opened is not None and len(bpy.data.actions) == 1 and not bpy.data.objects
        opened_content = pose_content(opened)
        result['direct_open'] = {'content_equal': opened_content == expected,
            'content_sha256': digest(opened_content), 'fake_user': opened.use_fake_user,
            'is_asset': opened.asset_data is not None, 'filepath': bpy.data.filepath,
            'objects': len(bpy.data.objects)}
        result['fake_user_in_library'] = opened.use_fake_user
        assert opened_content == expected and opened.use_fake_user is True and opened.asset_data is None
        assert Path(bpy.data.filepath).resolve() == backup_path
        assert hashlib.sha256(backup_path.read_bytes()).hexdigest() == backup['sha256']
        result['completed'] = True
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        with (output / 'Pose_library_readback_report.json').open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    assert result['completed'], 'Owned Pose library readback failed; preserve actual report.'
    print(json.dumps({'completed': True, 'content_equal': True, 'fake_user_in_library': True,
        'available_IDs': result['available_IDs'], 'actions_loaded': result['actions_loaded'], 'artist_opened_or_saved': False}))


if __name__ == '__main__':
    main()
