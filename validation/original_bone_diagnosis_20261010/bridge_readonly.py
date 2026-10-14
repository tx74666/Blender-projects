"""Send a vetted inspection script through the installed BlenderMCP protocol."""
import json
from pathlib import Path
import socket
import sys

code_path = Path(sys.argv[1])
request = {'type': 'execute_code', 'params': {'code': code_path.read_text(encoding='utf-8')}}
with socket.create_connection(('127.0.0.1', 9876), timeout=5) as connection:
    connection.settimeout(30)
    connection.sendall(json.dumps(request).encode('utf-8'))
    payload = b''
    while True:
        part = connection.recv(65536)
        if not part:
            raise RuntimeError('Blender closed the connection before a complete response')
        payload += part
        try:
            response = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        break
print(json.dumps(response, ensure_ascii=False))
if response.get('status') == 'error':
    raise SystemExit(1)
