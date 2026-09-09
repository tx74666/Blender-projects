from pathlib import Path

path = Path(r'D:\Blender\Projects\Character\X\addons\character_designer\forearm_twist.py')
text = path.read_text(encoding='utf-8')
start = text.index('        rings = detect_rings', text.index('def start_test('))
end = text.index('        if created_basis:\n', start)
capture = text[start:end]
capture = '\n'.join(line[4:] if line.startswith('    ') else line for line in capture.split('\n'))
capture = capture.replace('"target": target.name,', '"target": rig["target"].name,')
capture = capture.replace('"created_basis": created_basis}', '"created_basis": obj.data.shape_keys is None}')
helper = ('def _capture_record(obj, arm, rig, side, records):\n'
          '    """Capture this side from its own topology and weights, without writes."""\n'
          + capture + '    return record\n\n\n')
text = text[:start] + ('        record = _capture_record(obj, arm, rig, side, records)\n'
                      '        key_name = record["key"]\n') + text[end:]
insert = text.index('def start_test(')
text = text[:insert] + helper + text[insert:]
path.write_text(text, encoding='utf-8')
