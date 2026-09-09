X eye geometry and manual bone placement — 2026-09-09

The mesh supports reliable detection of each visible eye surface and its forward direction. It does **not** contain a closed eyeball from which an anatomical rotation center can be recovered. The measured evidence does not show a necessary pivot correction.

Read-only source: `X_left_foot_reset_preview.blend`, object `Cosha`, armature `CoshaRig`. Coordinates below are armature-local. Inspection used Blender background mode, disabled embedded scripts, and never saved or changed the source blend.

| Measurement | Left eye | Right eye |
| --- | --- | --- |
| Isolated component | 81 vertices, 64 quads | 81 vertices, 64 quads |
| Material | `Cosha_Eye` | `Cosha_Eye` |
| Visible patch centroid | `(0.049857865, -0.022685009, 1.849750067)` | `(-0.049857993, -0.022685009, 1.849750067)` |
| Surface forward normal, from PCA | `(0.518078314, -0.855333187, -0.000012066)` | `(-0.518078278, -0.855333209, -0.000012066)` |
| Existing pivot to patch center direction | `(0.493653969, -0.869603438, 0.009778573)` | `(-0.493655660, -0.869602477, 0.009778562)` |
| Existing eye axis angle from pivot-to-center ray | 0.22029 degrees | 0.22040 degrees |
| Existing eye axis distance from patch center | 0.00021871 | 0.00021882 |
| Existing bone tail distance from patch center | 0.00138037 | 0.00138045 |
| Existing eye axis angle from surface normal | 1.91949 degrees | 1.91949 degrees |
| Existing pivot depth behind surface plane | 0.05681092 | 0.05681099 |

The average polygon normals agree with the PCA normals. Each patch has eye-bone weights from 0.741379 to 1.0; six vertices also have `Head` weight. The components are shallow curved eye plates rather than complete spherical eyeballs. Surface depth relative to the best-fit plane spans about 0.002756 armature units.

The current eye axis already passes within approximately **0.17 mm in world space** of the patch center; its tail is approximately 1.08 mm from that center. The apparent outward orientation is supported by the geometry: the visible plates also face outward. It is not evidence that the bones were incorrectly aimed merely because they were placed manually.

A least-squares sphere fit places its center approximately **0.06814 units in front** of each patch, while the existing pivot is **0.05681 units behind** it. This happens because the plate is shallow/concave. That fitted sphere center is not a usable anatomical rotation center. Moving a bone head to the patch centroid would also make the eye turn around its visible surface rather than behind it.

Conservative implementation recommendation:

1. Detect each eye's weighted, disconnected `Cosha_Eye` patch automatically and use its centroid to size and position the visual target controls.
2. Keep the existing eye pivot. If exact automatic alignment is wanted, aim its native rest ray at the detected patch centroid; this is only a roughly 0.22-degree refinement. Preserving the current direction is also well supported by the measurements.
3. Use surface normals as a confidence check and the mean of the mirrored normals as shared face-forward; do not fit a sphere or infer a new pivot depth from these plates.
4. Validate left/right and up/down gaze using the actual deformed eye plates. The shared mask and individual targets can be made natural without modifying the current pivot. Any change to pivot depth would be an artistic calibration, not a geometry-derived correction.

Evidence and reproduction: `x_eye_geometry_audit.json` contains coordinates, topology, materials, weights, PCA results, and sphere-fit comparison. `audit_eye_geometry.py` recreates it with no save-mainfile operation.
