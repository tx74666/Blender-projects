"""Run one vetted task script through the local Blender bridge, with bounded read time."""
import json, socket, sys
from pathlib import Path
code_path=Path(sys.argv[1]).resolve()
if not code_path.is_relative_to(Path(__file__).resolve().parent):
    raise ValueError('Only vetted task scripts are permitted.')
request={'type':'execute_code','params':{'code':code_path.read_text(encoding='utf-8')}}
with socket.create_connection(('127.0.0.1',9877),timeout=5) as connection:
    connection.settimeout(1200)
    connection.sendall(json.dumps(request).encode('utf-8'))
    payload=b''
    while True:
        part=connection.recv(65536)
        if not part: raise RuntimeError('Bridge closed without complete receipt; inspect state before retry.')
        payload+=part
        try: response=json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError,UnicodeDecodeError): continue
        break
print(json.dumps(response,ensure_ascii=True))
if response.get('status')=='error': raise SystemExit(1)
