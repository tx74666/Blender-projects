"""Small index of live reports; never rewrite raw evidence."""
import hashlib
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
rows = []
for path in sorted(FOLDER.glob('response_*.json')):
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get('operation') != 'sample':
        continue
    components = report.get('components', {})
    runtime = components.get('function:character_designer.forearm_twist.update_runtime', {})
    frames = report.get('frame_boundaries', [])
    rows.append({
        'path': path.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'created_utc': report['created_utc'], 'id': report['id'], 'schema': report['schema'],
        'accepted': bool(report.get('completed')) and not report.get('callback_exceptions')
            and report.get('disk_unchanged') is True,
        'request': report.get('request'), 'loaded_addons': report.get('addons'),
        'displayed_frame_change_hz': report.get('observed_displayed_frame_change_hz'),
        'evaluated_frames': report.get('evaluated_frame_count'),
        'covered_frame_count': len({event['frame'] for event in frames}),
        'covered_frame_min': min((event['frame'] for event in frames), default=None),
        'covered_frame_max': max((event['frame'] for event in frames), default=None),
        'frame_evaluation_ms': report.get('frame_evaluation_ms'),
        'forearm_update_mean_ms': runtime.get('mean_ms'),
        'forearm_update_calls': runtime.get('count'),
        'forearm_prepare_mean_ms': components.get('function:character_designer.forearm_twist._prepare_runtime_records', {}).get('mean_ms'),
        'forearm_calculate_mean_ms': components.get('function:character_designer.forearm_twist._calculate_records', {}).get('mean_ms'),
        'panel_total_ms_per_draw': sum(component['mean_ms'] for name, component in components.items() if name.startswith('panel:')),
        'callback_exceptions': report.get('callback_exceptions'), 'errors': report.get('errors'),
        'restored': report.get('restored'), 'disk_unchanged': report.get('disk_unchanged'),
    })
rows.sort(key=lambda row: row['created_utc'])
summary = {
    'schema': 'x.playback-live-round4-summary/1',
    'date_local': '2026-10-15', 'artist_pid': 24416, 'blender': '5.2.0 LTS',
    'artist_input_sha256': '40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721',
    'model': 'gpt-6.1-sol', 'reasoning_effort': 'ultra',
    'samples': rows,
    'limits': [
        'POST_PIXEL frame changes are viewport draw events, not physical monitor presentation.',
        'Nested inclusive component timings must not be added.',
        'Each sample starts at frame21 with two seconds warmup and sixteen seconds measurement; measured frame phases differ, covered frame range is indexed.',
        'Sequential baseline changed from 5.55 to 4.08/4.78 Hz with Forearm cost 72.76 to 96.13/83.21ms. Small differences are not controlled marginal gains.',
        'hide_set preserves dependency evaluation; hide_viewport and modifier disable are separate diagnostics. No deletion has occurred in artist.',
        'New input/runtime conditions differ from the human 4.5/10/30 report; that report has not yet been reproduced.',
        'Failed first profiler attempt is retained and excluded from accepted samples.',
        'Hardware paused readings do not establish GPU load during playback.'
    ],
    'goal_complete': False,
}
(FOLDER / 'live_measurement_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps([{'id': row['id'], 'accepted': row['accepted'], 'hz': row['displayed_frame_change_hz'],
                   'forearm_ms': row['forearm_update_mean_ms'], 'frames': row['covered_frame_count']}
                  for row in rows], ensure_ascii=False))
