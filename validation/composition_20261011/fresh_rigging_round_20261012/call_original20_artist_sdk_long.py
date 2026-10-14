import hashlib,json,socket,sys,time
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2]);port=int(sys.argv[3]);raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[4]
request=json.dumps({"type":"execute_code","params":{"code":raw.decode("utf-8")}},ensure_ascii=False).encode("utf-8")
with socket.create_connection(("127.0.0.1",port),timeout=5) as s:
    s.settimeout(1);s.sendall(request);payload=b"";started=time.monotonic()
    while True:
        if time.monotonic()-started>1800: raise RuntimeError("UNKNOWN SDK outcome; no retry")
        try:part=s.recv(65536)
        except socket.timeout:continue
        if not part:raise RuntimeError("UNKNOWN closed SDK response")
        payload+=part
        assert len(payload)<1024*1024
        try:response=json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError,UnicodeDecodeError):continue
        break
with (out/"sdk_response.json").open("x",encoding="utf-8") as stream: stream.write(json.dumps(response,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":response.get("status"),"error":response.get("error")},ensure_ascii=True))
sys.exit(1 if response.get("status")=="error" else 0)
