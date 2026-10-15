These are source-only current-model baseline entries. No GUI, snapshot, Native
run or FPS result was created by preparing them. Root alone launches a NEW blank
factory GUI after observing resource ownership and memory. The current-cache
GUI is normally closed first; this route does not switch a loaded cache GUI.

The input must be the actual successful guarded current SaveCopy010 receipt,
its SHA, and the actual copied .blend SHA and byte length. The immutable007
load_snapshot gate validates the real010 producer and protection flags before
the baseline constructor imports bpy or opens anything. Old40644 evidence is
not upgraded and cannot stand in for this receipt. Both baseline and cache
must explicitly trace to the SAME current copy SHA/bytes and receipt.

1. Verify `current_model_baseline_dependencies_011.json`, then launch the same
   verified Blender executable/settings used for the current-cache GUI:

```powershell
& $RootVerifiedBlenderExecutable --factory-startup --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_current_baseline_gui_011.py' -- --snapshot-report 'ACTUAL_COMPLETED_SAVE_COPY010_REPORT' --snapshot-report-sha256 ACTUAL_RECEIPT_SHA --input-sha256 ACTUAL_CURRENT_COPY_SHA --input-bytes ACTUAL_CURRENT_COPY_BYTES --report 'ABSOLUTE_UNUSED_BASELINE_STARTUP_REPORT.json'
```

   Startup011 SHA is
   `6be987d7fa9f8926ce87bbd8102b2ae057e3c25f32512d0ea1399031595240f0`.
   It compiles sealed010's class/source-pin helper in private globals bound to
   the real current input and Stage06, without changing old constants/files.
   It normally registers/opens with load_ui=False, selects the saved Source
   View Layer once, observes two naturally ready ticks, calls normal private
   frame_set(1), yields, then observes two ready ticks before V9 readonly proof.
   No private solver/defer/manual callbacks are called. Only its own observer
   timer is removed; the standard add-on and private GUI remain alive.

2. Independently observe the new private PID, completed startup report SHA and
   native log. Root sets and checks matching non-camera PERSP/ORTHO full-body
   VIEW3D, window/area/region size, view location/rotation/distance, lens/clip,
   shading/overlays, sidebars and clip/sync/FPS settings against the cache run.
   The baseline must already be in requested MATERIAL shading before install;
   prewarm separately until Root is satisfied. The2s warmup is not proof that
   shader compilation or texture upload finished. Do not change GPU preferences.

3. In that PRIVATE GUI Console, use this exact CONFIG shape:

```python
CONFIG = {
    'expected_pid': FRESH_ROOT_OBSERVED_BASELINE_PID,
    'private_blend': r'ACTUAL_GUARDED_CURRENT_COPY_BLEND',
    'private_sha256': ACTUAL_CURRENT_COPY_SHA,
    'private_bytes': ACTUAL_CURRENT_COPY_BYTES,
    'artist': r'D:\Blender\Projects\Character\X\X.blend',
    'addons': r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\staged_20261015_06\addons',
    'source_manifest': r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\staged_20261015_06\source_manifest.json',
    'source_manifest_sha256': '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0',
    'mode': 'MATERIAL',
    'kind': 'current-baseline',
    'report': r'ABSOLUTE_UNUSED_BASELINE_FPS_ROUND1.json',
    'snapshot_report': r'ACTUAL_COMPLETED_SAVE_COPY010_REPORT',
    'snapshot_report_sha256': ACTUAL_RECEIPT_SHA,
    'startup_report': r'ACTUAL_COMPLETED_STARTUP011_REPORT',
    'startup_report_sha256': ACTUAL_STARTUP_REPORT_SHA,
}
```

```python
from pathlib import Path
import hashlib, importlib.util, sys
p = Path(r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\current_model_private_gui_fps_probe_011.py')
assert hashlib.sha256(p.read_bytes()).hexdigest() == 'a130ac3a263165d0b9691f976d86c94daef7ea6532ad0b11e6311d39f40b39e3'
sys.path.insert(0, str(p.parent))
spec = importlib.util.spec_from_file_location('_x_current_baseline_fps011', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
controller = module.install(CONFIG)
```

   Wait for completion/own cleanup, verify the first report, then install a
   second round with only a NEW unused report path. Keep the private window
   untouched. Each round uses unchanged009 normal animation_play, appended
   frame markers, POST_PIXEL callback, fixed2s+16s half-open clocks and native
   restoration. Frame-change and changed-token draw Hz remain separate; token
   gaps are not GPU completion/presentation/dropped-display-frame counts.
   Optional actual GPU metadata is sampled before timing; absence is unknown.

The FPS constructor removes exactly the two old baseline/baked admission
branches, substitutes V9 at its two literal import/path sites, and uses the
actual current receipt/startup gates. Original009 globals and fixed baseline
hash remain unchanged. Its full-state proof changes only stored_actions to
the existing V9 Reader: complete actual Actions including unused, author
select flags, slots/layers/curves/15-field bulk keys/raw/setbits and the original
Scene/Rig animation_data scope, hashed one payload at a time. Native bookkeeping
exclusions are explicit. This is a process-local proof, not portable reopening.
The same representation is used before/after. All mesh/key/rig/registered proof
and the measurement/restoration machinery retain the original methods.

Hot polls use only the verified filepath literal, PID/context identity and
native runtime/Scene/ViewLayer/Object/clip/sync/FPS reads. No path resolution,
file hash, Action or geometry proof runs in the hot window. Endpoints restore
frame1, shading/sync and normalized VIEW3D context and verify complete data,
disk/package/dependency/receipt and standard-handler identity scopes. Source
Cosha and Shoes visibility and the unchanged009 clip/local/quad-view gates
still apply. Only own timer/frame markers/draw/stderr observation are removed.

Report `comparison_view` contains the requested portable view subset. Apply
the same pure function `comparison_view(cache_report['before']['context'])`
to the actual current-cache report and require equality before comparing Hz.
Different private PIDs are expected; window/scene/native pointer identities
are intentionally excluded from this subset. ROOT still visually checks the
same full-body view and settings. A mismatch invalidates the comparison.
Subframes, shader pixel equivalence, physics and automatic30FPS adoption remain
unclaimed. Later artist edits require a NEW current copy and new comparisons.

Pure preparation only:

```powershell
& 'C:/Program Files/Python312/python.exe' -B 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/test_current_model_baseline_011.py'
```
