"""Inspect actual fbe6228777e7 typed modifier input interface in factory only."""
import json
from pathlib import Path
import runpy

base = runpy.run_path(str(Path(__file__).with_name('probe_nodes_modifier_properties52.py')))
modifier, socket = base['modifier'], base['socket']
report = {'interface': type(modifier.properties).__name__, 'sections': {}}
for name in ('inputs', 'outputs', 'panels'):
    value = getattr(modifier.properties, name)
    row = {'type': type(value).__name__, 'repr': repr(value)}
    if hasattr(value, 'bl_rna'):
        row['RNA'] = [{'id': p.identifier, 'type': p.type, 'readonly': p.is_readonly} for p in value.bl_rna.properties]
    try:
        row['items'] = [{'repr': repr(v), 'RNA': [{'id': p.identifier, 'type': p.type, 'readonly': p.is_readonly} for p in v.bl_rna.properties]} for v in value]
    except Exception as exc:
        row['iteration_error'] = repr(exc)
    report['sections'][name] = row
print(json.dumps(report, sort_keys=True))
