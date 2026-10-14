Historical 0.77.12 saved-scene/export evidence follows. Final disk delivery and
Unity acceptance are complete in [README_delivery_07714.md](README_delivery_07714.md).
The already-open Blender Python session remains 0.77.12; 0.77.14 changes only the
version declaration and embedded Unity importer, with identical Python behavior.

Character Designer 0.77.12 is built, deployed and running in the saved artist
session. Root completed the official ZIP build and deployed the same frozen
projection to Blender 5.2 and X's project add-ons. Both deployment checks reported
0 differences. The live operation refreshed the runtime to 0.77.12 and verified
all 152 deployed package files before applying the protected fresh Forearm pair.

The official package is
[character_designer-0.77.12.zip](<D:/MyRepository/Blender-addons-by-Randy/dist/character_designer-0.77.12.zip>),
SHA256 `a325332216dca755c72a977cf59dab5d616ed125bfe0dc4b5582dfb97169dd87`.
The deployment destinations are
`C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/character_designer`
and `D:/Blender/Projects/Character/X/addons/character_designer`.

[release_projection_07712.json](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/forearm_roll_07712_runtime/release_projection_07712.json>) locks exactly 152
package paths. Its SHA256 is
`2c6e63bfe3919a2ed224da69aede0456315fcde35c49db187fcdf5872b8e34a6`.
The official release resolver accepted the complete inventory and version
0.77.12; all 130 Python files passed AST parsing.

Relative to the hash-locked approved 0.77.11, exactly eight files differ:

- `__init__.py`: only the version declaration.
- `unity_export_worker.py`: existing isolated native head/tail/roll preservation.
- `forearm_twist.py`, `forearm_twist_cache.py`, `forearm_twist_topology.py`:
  exact support-ID and incident-connectivity proof, healthy legacy backfill,
  conservative rejection of stale legacy/local changes, safe Setup recapture.
- `forearm_twist_edit.py`: retain newly captured proof during manual loop addition.
- `body_calibration_ui.py`: Setup opts into the cancellable repair path.
- `unity_forearm.py`: prepare validated metadata copies during export capture;
  no scene metadata or sidecar schema changes.

All six Forearm canonical file diffs against the approved baseline were reviewed
and contain only this task's repair. The recipe locks their complete reviewed
byte hashes and verifies the Roll input differs in only its worker file.
Pending Dress/Cloth, worker cleanup, other canonical changes and Unity runtime
changes are excluded. Recipe, receipt and reviewed patch are preserved beside
the candidate. The recipe refuses overwriting an existing candidate.

The existing stale recovery test removes `support_topology` when simulating a
legacy record with a mismatched full hash. It still requires Paused, preserves
artist data, and rejects re-enabling before a valid proof is restored. The scope
suite proves unrelated edits are accepted and local edits are rejected. Six
non-Blender scope tests and the following frozen-package Blender validations
passed. The runner hash-validates the projection and preloads it so the fixtures
cannot silently import other canonical runtime changes.

| Evidence | Verified result |
| --- | --- |
| [native_forearm_scope.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/native_forearm_scope.log>) | 9 cases PASS: support proof, legacy migration, cancellable recapture, rollback and export refusal/preservation. |
| [test_forearm_twist_recovery_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_recovery_blender.py.log>) | Recovery, stale disable/enable guard, paired ownership refusal and Undo/Redo PASS. |
| [test_forearm_twist_setup_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_setup_blender.py.log>) | 11 tests, OK. |
| [test_forearm_twist_cache_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_cache_blender.py.log>) | 7 cache/invalidation/live-state cases PASS. |
| [test_forearm_twist_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_blender.py.log>) | 14 fixture/lifecycle/ownership/FK-hand cases PASS. |
| [test_forearm_twist_follow_runtime_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_follow_runtime_blender.py.log>) | 9 tests, OK. |
| [test_forearm_twist_ownership_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_forearm_twist_ownership_blender.py.log>) | 11 tests, OK. |
| [test_unity_forearm_blender.py.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/test_unity_forearm_blender.py.log>) | Blender FBX/sidecar export fixture, correspondence and unsupported-input refusal PASS. This does not establish Unity runtime correctness. |
| [fresh_actual.log](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/fresh_actual.log>) and [fresh_actual_report.json](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/fresh_actual_report.json>) | Protected actual artist backup: fresh paired capture/commit, native response and complete artist-data preservation PASS. |
| [protected_fingerprint.log](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/protected_fingerprint.log>) | Saved backup/native protected fingerprint PASS. |
| [saved_actual_verification.json](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/saved_actual_verification.json>) and [saved_actual_verification.log](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/saved_actual_verification.log>) | Factory-startup read-only reopening of final X.blend: PASS, exit 0; installed 152-file projection, saved pair records and protected artist fingerprint verified. |

The real old deployed worker failed the retained-bone Rest comparison:
[real_old_roll.json](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_old_roll.json>)
and [real_old_roll.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_old_roll.log>)
record approximately pi-radian Roll flips on `forearm.R`, `hand.R`, `shin.R` and
`thigh.R`. The report also retains connected-finger Rest/head/tail changes and
small hair numeric mismatches; the four large flips are not its only differences.

The fixed worker preserves all **217 retained bones**, with no missing bones or
Rest mismatches:
[real_new_roll.json](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_new_roll.json>)
and [real_new_roll.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_new_roll.log>)
are PASS. The actual captured Export job also passes that same 217-bone cleanup
gate and produces a real FBX receipt in
[real_export_new.json](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_export_new.json>)
and [real_export_new.log](<D:/Blender/Projects/Character/X/validation/character_export_fix_20261009/real_export_new.log>).
Its isolated FBX SHA256 is
`9c8fca0bc6c16b84d2b0f66f855a55a544a29d8a8258d6d18d22e8d9849a0851`.
These background checks preserved their input files and did not save a .blend.

The foreground operation and layout restoration both completed native saves:
[live_fix_receipt.json](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/live_fix_receipt.json>)
and [layout_restore_receipt.json](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/layout_restore_receipt.json>)
both have `status: SAVED` and `save_result: FINISHED`. The live receipt confirms
runtime `[0, 77, 12]`, original key identity/coordinates/state and geometry,
weights, native Rest, raw pose, constraints and actions preserved. The four
unrecorded artist keys were not adopted or deleted. The live save's intermediate
SHA was `f1cee21a518ce06ca191dc61decc1563efac3534aa989b1b01321b64f1e46fc8`;
the later layout-restoration save is the final
[X.blend](<D:/Blender/Projects/Character/X/X.blend>) SHA256:
`17a9312f6ec7f3ec0d709ca89fb2bc918aa94856af0fef544c3ce6ca83bded86`.
The protected backup remains
`15e3593a16ccd53a85690e3f9c862a2338b58317291e43a9a8cda7acdd25eebb`.

[verify_saved_actual.py](<D:/Blender/Projects/Character/X/validation/forearm_twist_fix_20261009/verify_saved_actual.py>)
subsequently reopened this final X.blend read-only with factory-startup. Its
PASS report confirms the installed runtime/source matches the frozen 152-file
projection, the protected fingerprint for original geometry, weights, native
Rest, raw pose, actions and all 12 original shape keys is unchanged, and
`CD Forearm Twist.L.002` / `CD Forearm Twist.R.002` have complete saved records.
No trial poses, exports or scene save were performed by this verification;
the artist and backup file hashes remained unchanged.

The Unity Avatar-ownership candidates compiled offline under Root's serial run
with Unity 6000.5.9f1's bundled DotNetSdk: **0 errors, 233 CS0649 warnings**.
[STAGED-HANDOFF.md](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/STAGED-HANDOFF.md>)
records the exact three candidates and repair order;
[compile-result.json](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/offline/compile-result.json>),
[restore.log](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/offline/restore.log>)
and [build.log](<D:/Unity Projects/RandomRealm2/.codex/task-staging/character-avatar-owner-20261010/offline/build.log>)
are historical offline evidence. Character subsequently published the corrected
bundle and source candidates as sole Unity writer, completed native compilation,
ownership/injected-rollback validation, idempotent five-fixture private-Avatar
repair and same-GUID production Avatar refresh. Four strict actual Animator
Idle/Walk samples and current-model correction checks pass. Independent absolute
bind/front and original-mesh disabled-correction provenance checks pass.
Adventure remains unsaved with its original handle, roots and previews preserved.
The final 0.77.14 actual reload continuation and disk delivery are recorded in
[README_delivery_07714.md](README_delivery_07714.md).

The independent binary FBX bind/skin and reimport ordinary-LBS roundtrip now
passes on both the protected pre-calibration export and the final saved-model
export: `real_fbx_roundtrip_explicit_parent.json/.log` and
`final_fbx_roundtrip_07712.json/.log`, each native exit 0. All 217 retained bind
frames, five mesh Basis/weights, 11 artist shapes and 19 requested poses pass.
Earlier non-PASS diagnostics remain retained: the ID-library snapshot needed
all loaded dependencies linked and a depsgraph update before world-matrix
comparison; deep pose chains needed explicit desired parent matrices when
converting to native pose basis. Source Rest error is now zero; test thresholds
were retained. Final correction-owned `.002` keys are explicitly excluded, with
Forearm correction runtime disabled for this ordinary-skin comparison.

`final_export_07712/forearm_sidecar_verification.json` separately passes the
final FBX/sidecar binding and structural checks: 64 source samples, 428 baked
subdivision stencils, maximum self-check 1.62e-7 below 3e-6. Final staged FBX
SHA256 is `0e88a931b3943aef7ae1b59e12b1340479afc71dcd47c690e88cb574c3a9342c`.
`production_bind_comparison.json` independently diagnoses the old Unity FBX:
forearm.L, hand.R, thigh.L and shin.R X/Z bind axes differ by approximately 180
degrees from the captured author Rest. This diagnoses the former production
input; Unity now uses the exact corrected publication bundle.

These export gates establish ordinary LBS separately from the subsequent
native Unity Animator/correction acceptance. The combined-pose source-modifier-order diagnostic reports maximum
surface differences of 11.67 mm (Cosha) and 11.32 mm (Stocking) between source
linear Armature-before-Subdivision and baked-Subdivision-before-linear-skin.
This fidelity limitation remains visible alongside the native Unity comparison;
it is not included in the ordinary-LBS PASS claim.

For Unity publication use `published_export_07712`, not the raw worker stage.
The shipped 0.77.12 `unity_export._publish` has now run natively on a hash-verified
copy of the worker outputs, producing the complete `.cdesigner.json` manifest
and file bundle. `publication_receipt_07712.json/.log` reports PASS / native
exit 0, original files and artist X unchanged, all published content hashes
verified, and no Unity Assets writes. Manifest SHA256 is
`eeb8ff545f9c2d954d8ba1ecc355309c4e0f2f3bc3c40da5cd35c4f604ad9bec`.
The user explicitly authorized X/Character coordination. Character completed
Unity deployment/validation after the fresh Building handoff; X owns canonical
source, frozen projection, independent static oracle and local add-on deployment.
