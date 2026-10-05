"""Summarize read-only counters separately from scene loading and timed updates."""
import json
from pathlib import Path
import statistics
import time
from run_arm_drag_probe import Counters, memory, process_sample

ROOT = Path(r'D:\Blender\Projects\Character\X\Validation\arm_drag_performance_20261003')

def ranges(rows):
    if not rows:
        return {'count': 0}
    result = {'count': len(rows), 'availableMiBMin': min(r['memory']['availableBytes'] for r in rows)/2**20,
              'availableMiBMax': max(r['memory']['availableBytes'] for r in rows)/2**20,
              'usedPercentMax': max(r['memory']['usedPercent'] for r in rows), 'counters': {}}
    for key in rows[-1]['counters']:
        values = [r['counters'].get(key) for r in rows if r['counters'].get(key) is not None]
        if values:
            result['counters'][key] = {'median': statistics.median(values), 'max': max(values)}
    for pid in {p['pid'] for r in rows for p in r['processes']}:
        procs = [p for r in rows for p in r['processes'] if p['pid']==pid]
        result.setdefault('processes', {})[str(pid)] = {}
        for key in ('workingSetBytes', 'privateCommitBytes', 'cpuCoreEquivalents', 'allPageFaultsPerSec'):
            values = [p[key] for p in procs if key in p]
            if values:
                result['processes'][str(pid)][key] = {'median': statistics.median(values), 'max': max(values)}
    return result

summary = {'method': 'PDH 0.5s snapshots cover windows, not individual ~20ms movements; system page I/O has no per-process attribution.', 'runs': {}}
for name in ('body_probe_fixed','body_probe_reverse'):
    folder = ROOT/name
    benchmark = json.loads((folder/'benchmark.json').read_text(encoding='utf-8'))
    rows = [json.loads(line) for line in (folder/'resources.jsonl').read_text(encoding='utf-8').splitlines()]
    events = [json.loads(line.split(' ',1)[1]) for line in (folder/'blender.log').read_text(encoding='utf-8').splitlines() if line.startswith('ARM_DRAG_EVENT ')]
    cases = []
    for case in benchmark['timing']['cases']:
        starts = [e['unix_time'] for e in events if e['event']=='sample_start' and e.get('case')==case['name']]
        ends = [e['unix_time'] for e in events if e['event']=='sample_end' and e.get('case')==case['name']]
        samples = [r for r in rows if min(starts) <= r['epoch'] <= max(ends)]
        cases.append({'name':case['name'], 'n':len(case['samples']), 'p50Ms':case['p50_wall_seconds']*1000,
                      'p95Ms':case['p95_wall_seconds']*1000, 'cacheColdMs':case['cold']['wall_seconds']*1000,
                      'validDeformation':case['deformation_witness']['valid'], 'resourceWindow':ranges(samples)})
    measurement_events = [e['unix_time'] for e in events if e['event'] in ('case_start','case_end')]
    summary['runs'][name] = {'status':benchmark['status'], 'cases':cases, 'fullRun':ranges(rows),
                             'caseWindow':ranges([r for r in rows if min(measurement_events) <= r['epoch'] <= max(measurement_events)])}

# No new Blender instance: observe the existing system briefly after probes exit.
counters = Counters()
read_only = []
try:
    for _ in range(40):
        time.sleep(0.5)
        read_only.append({'epoch':time.time(), 'memory':memory(), 'counters':counters.sample(),
                          'processes':[process_sample(40588)]})
finally:
    counters.close()
(ROOT/'post_probe_resources.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in read_only), encoding='utf-8')
summary['postProbe'] = ranges(read_only)
(ROOT/'measurement_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
