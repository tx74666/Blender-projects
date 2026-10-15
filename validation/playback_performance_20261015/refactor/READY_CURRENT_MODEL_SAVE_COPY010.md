This one-shot entry is prepared only. Root must first observe the live artist
PID, loaded canonical path, disk SHA and idle state in the agreed resource
window. Preparing/importing the script creates no copy and performs no native
operation. It does not use protected_refresh.prepare(), seek, update, solver,
handler removal, add-on registration or preference changes.

Normal registered Forearm playback owners/handlers are accepted. Pending/busy
runtime, calibration preview/rollback markers, active Delta-live/Hair/Skirt
work, playback/render/edit mode and any dirty image are rejected unchanged.
Dirty images matter because native SaveCopy can automatically save them under
the existing preference, even with its image dialog disabled. Standard save
handlers remain installed and run normally.

Root supplies exactly these fields in the observed artist GUI Console:

```python
CONFIG = {
    'expected_pid': FRESH_ROOT_OBSERVED_ARTIST_PID,
    'artist': r'D:\Blender\Projects\Character\X\X.blend',
    'artist_sha256': FRESH_ACTUAL_ARTIST_DISK_SHA256,
    'copy': r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\UNUSED_UNIQUE_CHILD_DIRECTORY\current.blend',
    'report': r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\UNUSED_CURRENT_COPY_REPORT.json',
}
```

The new directory must not exist; exclusive mkdir owns that output namespace.
The JSON report is also opened exclusively before the operation. The artist
path must still be loaded and its disk SHA must match the fresh observation.

```python
from pathlib import Path
import hashlib, importlib.util
p = Path(r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\current_model_save_copy_010.py')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '0de04db4929e725446ee9ec0e9414b26894274776edda6ad28852d9b1b29c9d4'
spec = importlib.util.spec_from_file_location('_x_current_save_copy010', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
receipt = module.run(CONFIG)
```

It calls native save_as_mainfile(copy=True, relative_remap=True) once. This
captures current working state without adopting the copy as the active file.
Before and after it compares V9's declared registered/raw/Rest/pose/foreign
payload witness, Base hide/select/active state across all Scene View Layers,
Object/Collection visibility flags, protected context, dirty/filepath, native
ID inventory, standard handler identities, artist disk and helper/package disk
pins. Post-operation proof is attempted even if SaveCopy raises or cancels;
failure is reported and never repaired automatically. Normal callbacks can
change data on save, so copy=True alone is not proof of zero memory changes.

The receipt records actual Blender version, loaded add-on version and runtime
file metadata. The scope is not a full source-geometry/all-RAM or live-code
attestation. Package pins describe disk files. A successful new snapshot supplies a fresh input for
separate full-clip comparison/rebuild; it does not establish equivalence to the
old40644 cache, produce a GUI FPS result or adopt the cache in the artist.

Only pure fake tests were run during preparation:

```powershell
& 'C:/Program Files/Python312/python.exe' -B 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/test_current_model_save_copy_010.py'
```

Native reference checked: Blender5.2 wm_files.cc, normal save callbacks and
use_save_as_copy behavior at2102–2240 and3970–4090:
https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/windowmanager/intern/wm_files.cc
