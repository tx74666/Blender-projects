# Cosha deformation repair — completed local delivery

Blender export now preserves native bone Roll, and Forearm Twist accepts proven
unrelated mesh edits while retaining conservative local-change rejection.
RandomRealm2 Character published the corrected FBX, refreshed the production
Avatar with its original GUID and validated current correction behavior.
The final import-recovery package is **0.77.14**, deployed to Blender 5.2 and
X/addons with zero differences at both targets.

| Gate | Result and evidence |
| --- | --- |
| Actual export | 217 retained bones, five meshes, 11 artist shapes and 19 ordinary-LBS poses PASS: [final_fbx_roundtrip_07712.json](D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/final_fbx_roundtrip_07712.json). |
| Fixed absolute Unity bind/front | 651 bone-world / 3,255 mesh-bind comparisons and four actual Animator Idle/Walk samples: [independent review](D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/unity_native_orientation_review_success_20261010.json). No common fitted yaw or 180-degree scene workaround. |
| Actual Animator/correction | [Strict native report](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/evidence/native-bind-corrected-20261009-211728-4b3c9fec/native.json>): all four owned Player/Source samples enabled, initialized and successful. |
| Current forearm mesh | [Current-model native validation](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/evidence/forearm-current-model-final.json>): bilateral twist / bent / raised / root-transformed checks; original mesh and fingerprint preserved. |
| Real reload continuation | [First successful Inspect](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/evidence/cosha-runtime-reload-inspect-20261009-214907-b034a82a/report.json>): actual nonce changes, automatic Drain completes, queues and SessionState clear, correct data name and six metadata identities remain. |
| Final disk delivery | [delivery_07714.json](D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/delivery_07714.json): frozen/installed 152 files, Unity importer, six publication files, five GUIDs and artist/Adventure hashes PASS. |

[0.77.14 release record](D:/MyRepository/Blender-addons-by-Randy/docs/releases/CharacterDesigner_0.77.14_unity_import_recovery_20261010.md)
records exact hashes, backup, source scope, native ownership rollback/private
fixture repair and limitations. [0.77.12 history](README_projection_07712.md)
retains the original Blender tests and native saved-scene evidence.
Character's [final Unity delivery](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/evidence/DELIVERY-FINAL.md>)
records final Avatar/source freshness, scene preservation, retained diagnostic
replay/CrashReporter evidence and normal compiler-server shutdown. The Unity
lease is released with mutations disabled; no work remains queued by this task.

The open Blender session remains 0.77.12; only the on-disk version declaration
and embedded Unity importer changed in 0.77.14. Its Python repair behavior is
unchanged. Artist X was already saved natively after protected calibration and
layout restoration. Unity Adventure's unsaved work remains intact; X never
operated Unity or wrote Assets concurrently with Character.

Scope is owned actual Animator previews, not Adventure Play mode: no existing
live actor was found during acquisition. SessionState preserves work across
assembly reload, not Editor exit. The pre-existing modifier-order surface
difference remains up to 11.67 mm on Cosha / 11.32 mm on Stocking in combined
poses; see [fidelity review](pipeline_fidelity_review_07712.json).
No FPS claim or Git commit/push is included.
