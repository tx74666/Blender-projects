"""Prove typed Boolean modifier input read/write in actual Blender 5.2 hash."""
import json
from pathlib import Path
import runpy

base = runpy.run_path(str(Path(__file__).with_name('probe_nodes_modifier_properties52.py')))
modifier, socket = base['modifier'], base['socket']
value = getattr(modifier.properties.inputs, socket.identifier)
report = {'type': type(value).__name__, 'RNA': [], 'trials': {}}
for prop in value.bl_rna.properties:
    row = {'identifier': prop.identifier, 'type': prop.type, 'readonly': prop.is_readonly}
    if prop.identifier != 'rna_type':
        try: row['value'] = getattr(value, prop.identifier)
        except Exception as exc: row['error'] = repr(exc)
    report['RNA'].append(row)
for name in ('value', 'default_value'):
    try:
        before = getattr(value, name)
        setattr(value, name, True)
        after = getattr(value, name)
        setattr(value, name, False)
        report['trials'][name] = {'before': before, 'after': after, 'restored': getattr(value, name), 'success': type(after) is bool and after is True}
    except Exception as exc:
        report['trials'][name] = {'success': False, 'error': repr(exc)}
print(json.dumps(report, sort_keys=True))
