import hashlib,sys,types
from pathlib import Path
p=Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/inspect_original_registration_graph_07736.py');raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='7d2405a53a3de5f0dbaef7cd84c81dac49e2b68971f86dc7c63f3883a560267b'
assert 'x_original_registration_recovery_07736' not in sys.modules
ns={'__file__':str(p),'__name__':'x_original_registration_graph_probe'}
exec(compile(raw,str(p),'exec'),ns)
holder=types.ModuleType('x_original_registration_recovery_07736')
holder.observed_namespace=ns
holder.source_sha256='7d2405a53a3de5f0dbaef7cd84c81dac49e2b68971f86dc7c63f3883a560267b'
sys.modules[holder.__name__]=holder
print('Task-owned Python diagnostic references retained; no CD registry/scene mutation.')
