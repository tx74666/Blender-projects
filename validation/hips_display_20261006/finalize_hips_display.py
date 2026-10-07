"""Save the verified live display preference after restoring the artist editor."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import bpy

root = Path(r'D:\Blender\Projects\Character\X\Validation\hips_display_20261006')
namespace = {'action': 'inspect'}
exec(compile((root / 'prepare_hips_display.py').read_text(encoding='utf-8'),
             'hips_display_save_preflight', 'exec'), namespace)
rig, pb, service, record = namespace['_preflight']()
apply_path = max(root.glob('apply_*.json'), key=lambda path: path.stat().st_mtime_ns)
applied = json.loads(apply_path.read_text(encoding='utf-8'))
if applied.get('status') != 'PASS':
    raise RuntimeError('The latest application did not pass; do not save.')
if namespace['_snapshot'](rig, service) != applied['after']:
    raise RuntimeError('Live scene data changed after the display check; do not save.')
if tuple(pb.custom_shape_scale_xyz) != (0.0, 0.0, 0.0):
    raise RuntimeError('The Hips display preference is not active.')
metadata = namespace['_metadata'](pb, record)
if metadata != applied['restore_metadata_after']:
    raise RuntimeError('The original restore record changed; do not save.')
area = bpy.context.area
if area is None or area.type != 'CONSOLE':
    raise RuntimeError('Expected the temporary Console editor before restoring it.')
area.ui_type = 'ShaderNodeTree'
if area.type != 'NODE_EDITOR' or area.ui_type != 'ShaderNodeTree':
    raise RuntimeError('The original Shader Editor could not be restored.')
result = bpy.ops.wm.save_mainfile()
if 'FINISHED' not in result or not namespace['_same_path'](bpy.data.filepath, namespace['ARTIST_FILE']):
    raise RuntimeError('Blender did not confirm saving the current artist X.blend.')
after = namespace['_snapshot'](rig, service)
if after != applied['after'] or service.validate(rig) != record:
    raise RuntimeError('Saved live rig state changed outside the display preference.')
artist = namespace['ARTIST_FILE']
report = {
    'status': 'PASS', 'saved_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
    'artist_file': str(artist), 'artist_sha256': namespace['_sha256'](artist),
    'artist_size_bytes': artist.stat().st_size, 'blender_version': bpy.app.version_string,
    'blender_save_result': sorted(result), 'main_artist_saved': True,
    'data_is_dirty_after_save': bpy.data.is_dirty,
    'editor_restored': area.ui_type, 'hips_bone': pb.name,
    'hips_custom_shape_scale_xyz': list(pb.custom_shape_scale_xyz),
    'restore_property': namespace['RESTORE_KEY'], 'restore_metadata': metadata,
    'apply_evidence': str(apply_path), 'all_other_recorded_rig_data_unchanged': True,
    'runtime_refreshed': False, 'addon_deployed': False, 'background_process_started': False,
    'saved_file_reopened': False,
}
(root / 'final_saved_scene.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('HIPS_DISPLAY_SAVED', str(artist), report['artist_sha256'], report['artist_size_bytes'], sorted(result))
