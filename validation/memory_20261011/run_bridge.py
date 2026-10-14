"""Execute only this task's vetted scripts through the verified artist port."""
import argparse
import json
from pathlib import Path
import socket

parser = argparse.ArgumentParser()
parser.add_argument('script')
parser.add_argument('output')
args = parser.parse_args()
root = Path(__file__).resolve().parent
script = Path(args.script).resolve()
output = Path(args.output).resolve()
if not script.is_relative_to(root) or not output.is_relative_to(root):
    raise ValueError('Script and output must remain in this task directory')
request = {'type': 'execute_code', 'params': {'code': script.read_text(encoding='utf-8')}}
with socket.create_connection(('127.0.0.1', 9877), timeout=5) as connection:
    connection.settimeout(45)
    connection.sendall(json.dumps(request).encode('utf-8'))
    payload = bytearray()
    while len(payload) < 4 * 1024 * 1024:
        part = connection.recv(65536)
        if not part:
            raise RuntimeError('Bridge closed before complete response; inspect before retry')
        payload.extend(part)
        try:
            response = json.loads(payload.decode('utf-8'))
            break
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    else:
        raise RuntimeError('Bounded response size exceeded')
output.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': response.get('status'), 'output': str(output),
                  'bytes': len(payload)}, ensure_ascii=True))
if response.get('status') == 'error':
    raise SystemExit(1)
