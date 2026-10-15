The new source-only probe is `private_gui_fps_probe_009.py`, SHA256
`a6ce26f86c4fa6aee5dc58fc68f59010a12c9983324133f56e01e2ab2db471ed`
(33590 bytes). Authoritative preparation seal:
`private_gui_fps_probe_009_dependencies_v4.json`, SHA256
`fa08817f49cad6dde583512bbcd416ad666b5bb60e950396c68a8e70ea55c761`.
The earlier unrun dependency draft is retained and superseded. No previous
profiler, addon, artifact, stage, actor or native evidence was changed.

Compilation and eight retained pure-check groups pass. The pure checks import
no bpy and perform no GUI/native work. They cover explicit PID/mode/baseline
admission, required baked receipt configuration, event-based 30 Hz math,
duplicate draw-token filtering, exact fixed-window boundaries, empty rates,
and absence of open/save/register/deformation calls in the entry source.
Actual native APIs, timer cleanup and playback cadence remain unverified.

Root runs this only after Console's actual END, in a NEW owned private GUI
process. It does not launch/open/save anything or register an addon. The normal
staged addon must already be loaded, naturally settled and error-free. The
Root-supplied PID, current private blend path/SHA and stage manifest SHA must
match. The canonical artist and its hard links are rejected.

For a baked candidate, a pinned completed GUI008 receipt must match this PID
and exact artifact file, complete all 30 geometry/Action frames, have removed
its own timer, retain the standard handlers and report successful lifecycle/
cleanup/source protection. The current standard handler identities must still
match its settled snapshot. Its artifact/source chain and verifier/portable
helper pins are checked. That GUI artifact/receipt does not exist at source
preparation time; no acceptance is inferred from this file.

An independent baseline private GUI instead needs kind="baseline", explicit
allow_fixed_baseline=true and exactly the known 40644… /34691613-byte input.
It is never a fallback when baked admission fails.

Prepare CONFIG with these JSON-safe fields:

- expected_pid: Root's previously observed private-process integer PID.
- private_blend, private_sha256, artist: actual absolute paths and expected
  private file SHA; artist must be the canonical X/X.blend boundary.
- addons, source_manifest, source_manifest_sha256: the actual immutable stage.
- kind: "baked" or the explicitly authorized "baseline".
- mode: "MATERIAL" or "SOLID"; no object/modifier/collection visibility control
  or sidebar-hiding option exists.
- report: an exclusive unused .json path within this refactor directory.
- Baked only: gui008_report and gui008_report_sha256, with
  allow_fixed_baseline omitted/false.
- Baseline only: allow_fixed_baseline=true and the exact fixed input pin.

After CONFIG is populated, Root's source Console entry is:

```python
from pathlib import Path
import hashlib, importlib.util, sys
_fps_path = Path(r"D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor\private_gui_fps_probe_009.py")
assert hashlib.sha256(_fps_path.read_bytes()).hexdigest() == "a6ce26f86c4fa6aee5dc58fc68f59010a12c9983324133f56e01e2ab2db471ed"
sys.path.insert(0, str(_fps_path.parent))
_fps_spec = importlib.util.spec_from_file_location("_x_private_gui_fps009", _fps_path)
_fps = importlib.util.module_from_spec(_fps_spec)
_fps_spec.loader.exec_module(_fps)
_fps_controller = _fps.install(CONFIG)
```

Use the verified Root PID in CONFIG, not a value inferred by the probe itself.
The owned timer returns its source Console area to VIEW_3D, captures the saved
frame/subframe/context and full evaluated scene meshes/keys/rig pose/Rest/raw
channels/Actions, checks visible Cosha and Shoes and the existing 1–30 clip,
then sets only the requested shading mode. Local/quad view is rejected. Other
mesh visibility, clip/style, render engine, view transform, viewport dimensions
and UI settings are recorded. Keep the owned window/context unchanged until
the report closes; sample overhead and full proof extend beyond the hot window.

Only two own frame markers are appended after existing standard handlers and
one target WINDOW/POST_PIXEL callback is added. No existing handler/function is
wrapped, reordered or disabled; no manual helper/core/deformation solver or
runtime defer is used. Normal screen.animation_play runs with 2 seconds warmup
after confirmed start and a fixed 16-second sample. There is no file hashing,
geometry/Action proof or report I/O inside that hot window.

The report separates frame-change Hz, POST_PIXEL callback Hz, consecutive
changed-scene-frame-token draw Hz, frame histograms, full 1–30 coverage and the
appended-pre-to-post span. This last span excludes earlier standard frame-pre
callbacks and cannot be interpreted as total frame CPU cost. Draw callbacks
observe a scene-frame token at POST_PIXEL; GPU completion, OS presentation and
pixel identity are not measured. No FPS is calculated from solver/eval time.
The sample does not automatically declare the 30 FPS goal achieved.

The probe stops its own playback, removes only its callbacks/draw/timer, returns
to the original frame/subframe with normal evaluation, restores original shading
and sync state, then checks exact full model/Action/context restoration and
standard handler identities. It does not repair mismatches by assigning actor
poses/keys, save, open a file or disable the normal addon. Disk/stage/helper/
receipt pins and Python stderr are checked outside timing. Dirty state is
observed only. Callback errors, lost context/ownership, incomplete frame coverage
or failed restoration keep completed=false; native process stderr still needs
Root's independent inspection.

Run the retained pure checks with the ordinary Python interpreter only:

```powershell
& 'C:/Program Files/Python312/python.exe' 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/private_gui_fps_probe_009_pure_checks.py'
```

Material preview compilation/cache completion is not measured. Two seconds of
warmup do not prove compilation complete. Root prewarms the same fixed input,
view/camera, resolution and shading before any baseline/Bake comparison. No A/B
process/scene framework or automatic launch is provided.

Source review fixes: normal animation_play omits the sync keyword and honors
the saved Scene playback policy. Standard callback identities are checked again
after frame restoration and full proof, including proof failure paths.
