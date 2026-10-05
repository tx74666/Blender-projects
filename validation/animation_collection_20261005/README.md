# Animation collection: X evidence, 2026-10-06

The frozen Character Designer **0.76.3 R8 candidate** is locally deployed to
Blender **5.1.0** and X's validation copy. The artist X was saved under a later
direct user instruction. This folder keeps isolated motion tests separate from
that artist save. Model version and reasoning effort were not recorded.

| Evidence | Result and boundary |
| --- | --- |
| [R8 inventory](candidate_source_r8_inventory.json), [deploy check](deploy_check_51_r8.log) | 147 shipped files match both installations. Eight approved files differ from frozen 0.76.2; unrelated unpublished Dress changes are excluded. No Blender 5.2 deployment. |
| [Light checks](light_checks.json) | 182 checks passed, 24.382 s. Later R8 UI checks also passed; overlapping checks are not added into a unique total. |
| [Native R7](native_r7_20261005_214820/collection_native_qa.json), [diagnosis](r7_checkpoint_diagnosis.json) | Original overall failure remains: an inactive fixture scene had a stale evaluated matrix. Raw state matched; explicit ViewLayer evaluation matched. No tolerance was relaxed. |
| [Native resume](native_r7_resume_20261005_220620/collection_resume_native_qa.json) | 44 checks passed: independent Idle/Walk edits, separate save/reopen, serial publication, worker disposal, and repeated Sync with no new worker/output. The final private worklist file is in the same directory. |
| [Minimal activation fixture](activation_r8_success_v5/report.json), [UI](activation_r8_success_v5/report_ui.json), [rollback](activation_r8_rollback_v5/report.json) | Success/UI/rollback passed in isolated fixtures. This activation script was not applied to artist X, which already reported 0.76.3. |
| [Live audit](live_loaded_r8_audit.json) | 147 files, ten key function bodies, registration, four operators and six RNA fields match R8. Audit snapshots match. Overall report remains failed because its immediate post-save assertion failed. Activation/refresh were not performed; the earlier activation source is unrecorded. |
| [Live diagnosis](live_saved_state_diagnosis.json) | Recovered the exact original in-memory baseline. Final difference only `$.dirty: False -> True`; the inspected PG/Actions/poses/bindings/selection/mode/frame/handlers/classes/windows otherwise match. The first immediate failure's differing fields were not captured. Do not rewrite it as a complete post-save pass. |
| [Final artist save](live_final_save.json) | Geometry Nodes restored; native Ctrl+S displayed `Saved "X.blend"`, title had no star in two observations. 2026-10-06 00:53:13.945 +08, 32,254,503 bytes. No subsequent disk-reopen or full post-save audit. |

R8 ZIP: `candidate_source_r8/dist/character_designer-0.76.3.zip`, 1,096,203 bytes,
SHA256 `9df21c111412725b80e9b2ec885bc0d1c5fc78d60a010398a501b4a6faab6a35`.
Final artist SHA256:
`2b36fb936082cbe7a81dd29e1dba22b9f9fbefa935015bfb29cc37b5b496ca9a`.

Dense fixture timing is **not a before/after performance benchmark**. First Scan
89.479 s, final Scan 62.004 s; Idle Sync 77.943 s and Walk Sync 14.687 s. R8 gives
early scanning feedback, blocks repeated clicks and reuses the launch proof;
the scan callback is still synchronous, and Cancel waits for a running scan.
No CPU, FPS or GUI-latency improvement percentage is established.

Unity acceptance belongs to the Character chat. Its latest isolated
[two-motion Return report](<D:/Unity Projects/RandomRealm2/Logs/CharacterTuning/AW/Returns/918d4b34/pair-return-verification.json>)
passes actual Walk/Idle Sync, rendering, Apply and native Undo/Redo, with private
finalization and production/scene/selection guards. The prior failed WriteAtomic
report remains at `AW/Returns/aebf214a/pair-return-verification.json`; a separate
recovery report passed. Separate
[Visible acceptance](<D:/Unity Projects/RandomRealm2/Logs/CharacterTuning/AW/VisibleChanges/46df3c9b519f490a8bb46d9276944808/visible-change.json>)
also passed: saved private Controller slots match both candidates and the
comparison shows edited-forearm changes of 5.6655° / 5.8917° maximum for Walk /
Idle. Humanoid import still warns about discarded shin/foot translations;
this is not a lossless translation roundtrip. None of these private checks
applies either candidate to the production character.

All owned background Blender tests ended normally. GUI ownership was returned;
no Commit, Push, PR or external release was performed. Reuse these evidence
links on the next investigation; investigate new dependency/receipt/UI symptoms
rather than repeating the complete fixture run.
