# Current cache FPS entry

`mesh_cache_current_gui_fps_probe_008.py` is a thin adapter over the frozen FPS005/006 classes and FPS009 timing core. Its final dependency seal is `mesh_cache_current_fps_dependencies_008.json`. Source readiness is separate from actual playback results. A completed current Full30, published artifact and same-PID GUI008 receipt are mandatory; missing or failed evidence refuses installation.

Root alone installs in the owned current cache GUI. The artist is never opened or measured by this entry. The artifact must derive from the same guarded SaveCopy010 as baseline011; the actual capture in this run has SHA256 `6fd14673d8acf03fd96b9856b1db09dd39a5492ae91ef3b68b49be80cd83a848`, length `34843358`, and snapshot receipt SHA256 `0e630be1a411994dabb689a80ad8c94fb3663d9924cc6c74693d3d71483dd6cc`.

Use exactly these eight CONFIG keys, replacing the observed private PID, actual artifact/GUI receipt pins, and an unused report path:

```python
CONFIG = {
    'expected_pid': OBSERVED_OWNED_CACHE_GUI_PID,
    'private_blend': ACTUAL_PUBLISHED_CURRENT_ARTIFACT_PATH,
    'private_sha256': ACTUAL_PUBLISHED_CURRENT_ARTIFACT_SHA256,
    'artist': r'D:\Blender\Projects\Character\X\X.blend',
    'gui_report': ACTUAL_COMPLETED_CURRENT_GUI008_REPORT_PATH,
    'gui_report_sha256': ACTUAL_COMPLETED_CURRENT_GUI008_REPORT_SHA256,
    'mode': 'MATERIAL',
    'report': UNUSED_DIRECT_REFACTOR_JSON_PATH,
}
import sys
sys.path.insert(0, r'D:\Blender\Projects\Character\X\validation\playback_performance_20261015\refactor')
import mesh_cache_current_gui_fps_probe_008 as probe
controller = probe.install(CONFIG)
```

Before installation, Root aligns and separately prewarms the full-body non-camera VIEW3D, requested shading, window/region dimensions, view transform, overlays, lens/clip and clip/FPS/sync settings. The probe requires the requested mode to be selected already. Normal Console installation converts its own area back to VIEW3D using the frozen core. It rejects camera/local views. Its fixed two-second warmup does not prove shader compilation completed.

Run two MATERIAL rounds, each with a fresh report path, only after the previous probe has closed and cleanup passed. Root then normally closes the owned cache window and starts the fresh baseline011 factory GUI, using the same snapshot. Baseline and cache can have different PIDs. Before comparing cadence, require:

- Cache `current_input` equals baseline `private_before`, including SHA256 and byte length.
- Both `current_snapshot_receipt` pins match.
- Both `comparison_view` dictionaries match and `comparison_view_after_exact` is true.
- Both reports completed successfully with exact state/context restoration, normal callbacks preserved, source/disk/receipt pins unchanged and full clip coverage. Record their actual GPU context metadata; unknown metadata does not turn a valid measured sample into a GPU claim.

Each round uses the unchanged normal `animation_play`, fixed half-open sixteen-second sampling interval, frame-change callbacks and POST_PIXEL callbacks. Frame-change cadence and changed-frame draw-token cadence are separate frequencies. Observed modulo-30 token gaps are minimum unseen-frame counts, not measured display drops. Appended pre-to-post spans are partial callback spans and are never inverted to claim FPS or GPU completion.

Outside timing, the adapter verifies the actual current mesh count, complete frame1 geometry/world/normals/attributes, declared animation/closure, current shader parameters/resources, the full Base/selection/Collection table, published dependencies and real snapshot provenance. During timing, its 0.1-second health poll only reads retained native bindings, literal cache paths, runtime flags/errors, current-layer membership/hide/select/active and Collection topology. It performs no hashing, path resolution, resource reading, solver call or full geometry proof in that window.

The shader proof covers graph/parameters and resource bytes, not rendered pixels or implicit coordinates. The snapshot covers the artist at capture time. Later artist edits, physics, subframes and other clips require separate evidence. This probe does not automatically adopt a cache or modify/save the artist.
