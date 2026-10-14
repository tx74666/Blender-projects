# Arm Flat IK bend repair — 2026-10-09

Character Designer 0.77.11 fixes the selected Arm Flat preset's IK application through explicit `stable_ik_bend` and side-specific, Rest-compatible `stable_ik_seed` metadata. The artist Arm Flat asset was tagged, applied atomically to both arms and saved natively in X.blend by `finish_live.py`. The runtime was refreshed to 0.77.11 and the original editor layout restored, with a second native Save confirmation.

Native Blender 5.2 reproduction confirmed that applying the old FK-authored Arm Flat and retracting either Hand IK yields posterior dot about 0.323, downward Z about -0.946. The asset contains a 5.7 mm downward shallow elbow bend. Literal pose matching correctly reproduces that plane; it becomes unsuitable for this intended flat preset's future IK motion. Replacing only Pole angles or changing the generic near-straight threshold does not fix it.

The opted-in IK application uses verified reference source frames and the existing stable roll-frame matcher. It permits at most 2% shoulder–wrist reach and 3 degrees of upper/lower adjustment, and preserves the authored wrist within 1e-5. Real-model correction is about 7.5 mm and 1.68 degrees. Subsequent 2%, 15%, and 30% hand retractions give posterior dot about 0.982; clearing visible controls gives about 0.984. Pole angles are preserved, including the verified right-side -pi correction. Ordinary assets, FK, BLEND, deeply bent poses, and Original retain their exact matching contract.

Evidence:

- `../arm_pole_20261009/asset_apply_probe.json`: old behavior reproduced without control reset.
- `../arm_pole_20261009/asset_apply_intent_probe.json`: healthy reference candidate.
- `../arm_pole_20261009/asset_apply_dirty_intent_probe.json`: retaining contaminated source frames is insufficient.
- `real_candidate_verified.json`, `fresh_candidate_guard_native.log`: seven full-character cases, including normal/mirror IK, both FK sides, ordinary exact asset, Original, and atomic both-arm application. All PASS; protected checkpoint and artist files unchanged during isolated runs.
- `synthetic_07711_native.log`: 15 new native regression tests PASS, including connected Fist location/rotation/scale/B-Bone preservation on normal and mirrored applications.
- `capture_native.log`: 27 existing capture tests PASS.
- `pose_weights_native.log`: 14 existing pose/weight workflows PASS.
- `stable_ik_seed.json`: six historical verified source frames from the 2026-10-08 real-character checkpoint. No new Rest calibration is inferred.

Release is a complete 152-file projection of shipped 0.77.9 with only `control_pose_assets.py` and version changed. `release_projection.json` SHA256: `199b46ab6a5972b426a1daf3be9df03de4903cc270b294da20995523e59dea22`. Blender 5.2 installation and X/addons deployment both verified with zero differences. No held Cloth/Direct Dress or unrelated RR Helper edits shipped. No Git commit or push.

Artist operation and refresh/save status must be taken from `backup_receipt.json` and `live_fix_receipt.json`, when present. The successful live receipt confirms the saved operation. A 0.77.10 attempt was rolled back without saving when its unrelated-channel guard detected dormant connected-finger locations being cleared. Version 0.77.11 avoids rewriting unkeyed native arm descendants that already match their target world matrix; this preserves those artist channels while retaining final matrix verification. Isolated tests do not test actual Asset Browser mouse events or native Undo.

Final read-only reopen verification: `saved_artist_verified_07711.json` and `saved_artist_07711_native.log` PASS using frozen 0.77.11. The saved metadata, six reference sources, protected data and unrelated raw channels match the fresh backup. All 36 hand retraction/control-reset checks passed across saved current, normal, mirrored and atomic reapplication cases. Artist and backup SHA256 remained unchanged; process exited 0.
