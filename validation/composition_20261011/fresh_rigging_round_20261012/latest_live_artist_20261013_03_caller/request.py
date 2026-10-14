import hashlib,json
from pathlib import Path
p=Path("D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\snapshot_latest_original_artist_current.py")
raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="e3f2b3a548021a575b8c68abbfa33c11764fd14353494583f24038dcd4f0d3b7"
ns={"__file__":str(p),"__name__":"x_latest_live_snapshot"}
exec(compile(raw,str(p),"exec"),ns)
kwargs=json.loads("{\"expected_pid\":14500,\"external_process_filetime\":\"134362924923204924\",\"script_sha256\":\"e3f2b3a548021a575b8c68abbfa33c11764fd14353494583f24038dcd4f0d3b7\",\"output_root\":\"D:\\\\Blender\\\\Projects\\\\Character\\\\X\\\\validation\\\\composition_20261011\\\\fresh_rigging_round_20261012\\\\latest_live_artist_20261013_03\",\"oracle_sha256\":\"260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d\",\"runtime_manifest_sha256\":\"c72a4b8a8b0988138f40542b1a3bb0b8313e9aaac7e4ab4bd3baa1f21c05c92b\"}")
kwargs["external_process_filetime"]=int(kwargs["external_process_filetime"])
result=ns["run"](**kwargs)
assert result["completed"],result
