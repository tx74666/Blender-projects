The projection recipe starts from the exact approved 0.77.11 inventory and changes
only two fragments of `_clean_skeleton`: snapshot native head/tail/roll, then restore
only those fields which parenting actually changed. It checks the resulting
function is byte-for-byte equal to persistent canonical `_clean_skeleton`. It does
not include the pending Dress changes or the newer evaluation-copy cleanup.

`probe_export_rest.py` must run in isolated background Blender. `--scope cosha`
needs only `--worker` and `--report` and reproduces the real Cosha hand/shin/thigh
native-axis case. Its old-worker result on Blender 5.2 was PASS, so this rebuilt
minimal fixture does not establish the failure. The protected current character
did fail: four right-side forearm/hand/shin/thigh Rest rolls changed by pi. The
reconstructed minimal geometry shares head/tail with the current character, but
its hierarchy and native matrices differ slightly. Preserve the exact saved
native matrices and character hierarchy for the decisive reproduction.
`--scope real-clean --blend <fresh read-only backup> --rig CoshaRig` compares every
retained bone's native Rest before/after control stripping, permitting only parent
remapping. `--scope real-export --blend <captured Export snapshot> --job <job.json>`
uses the exact Export collection and job inputs, overrides only the output stage,
captures every armature's cleanup Rest, and reports a real FBX receipt. No scope
ever saves a .blend, starts a second process, or deploys an add-on.

For the subsequent real FBX round trip, retain the captured all-bone Rest oracle
and also compare Basis, artist BlendShape deltas and weights after axis/unit
conversion. A skin oracle should pose the imported skeleton to the captured
author Rest world frames with Animator and ForearmCorrection disabled, then check
the skinned surface against the baked exported neutral surface. This catches a
bad exported bind frame which an imported-neutral-only comparison can conceal.
Repeat after a common rigid transform and one controlled wrist/ankle/shin motion.
Enable ForearmCorrection and the intended Unity animation separately to isolate
the companion runtime and Humanoid retargeting. Static Blender reimport alone
does not verify Unity Humanoid behavior or correction runtime.
