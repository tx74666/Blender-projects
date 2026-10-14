# Latest original artist SaveCopy: Source only

This successor script has not executed. Root must receive a fresh original-X
resource/SDK scope and verify the actual process PID and full creation FILETIME
externally. Building currently owns resources. The script never starts a
process, opens another file, deploys, refreshes or registers a runtime.

The future one-call API is `run(expected_pid=..., external_process_filetime=...,
script_sha256=..., output_root=..., oracle_sha256=...,
runtime_manifest_sha256=..., scene_name='Scene', rig_name='CoshaRig')`.
Root supplies actual values, not a historical authorization. The output root
must already be a new empty child of this ROUND. It saves only
`artist_latest_before_rigging.blend` with `SaveAs(copy=True)` and writes its own
`artist_latest_snapshot_receipt.json`. It never overwrites an earlier snapshot.

Admission requires the live filepath to be original X.blend, its disk SHA to
remain `3cd5619d…`, and the already-loaded `character_designer` version to be
0.77.24. The actual cached module paths and physical SHA values must match the
immutable 0.77.24 projection. Missing or mismatched runtime identity fails before
SaveCopy. No Source 0.77.25 code is imported automatically.

A fresh actual Window override reads the original Scene/ViewLayer/setup Rig
without selecting, switching Scenes or modes. Light pre/post evidence includes
the context, native pointers, complete Worklist RNA catalog/items and identities,
raw Rig/MainRig session metadata, raw Rest, current pose/Action/NLA/time settings,
mesh/data/material/group/shape-key identities, modifier stacks, and all Action
slot inventories. Known metadata must remain equal. Unknown is kept explicit.

The only native operation is `wm.save_as_mainfile(..., copy=True)`. The script
requires FINISHED, a new physical snapshot and its hash, unchanged original
filepath/Scene/Rig/mode/frame/selection, and unchanged original disk SHA. Dirty
flags are recorded as serialization metadata. Original X is not saved, and its
unsaved artist state is copied rather than replaced with historical QA.

To reduce the original SDK call's time/resource cost, the full streamed
geometry/weights/shape-key/material/color/widget/forearm preservation oracle and
complete selected-slot motion fingerprints are deliberately deferred to a
separate disposable snapshot-clone review. The pinned existing preservation
oracle is recorded but not loaded or called here. These fields remain Unknown
and `full_preservation_verified` remains false; `completed` means only that this
minimal recoverable backup scope finished. It does not prove original-Rig
Rigging compatibility, runtime migration, user edits, export or Unity Apply.

If light introspection is unsupported, the receipt retains its reason. A valid
SaveCopy may still be an honest recoverable artifact while comprehensive
preservation remains unproved. No failed or partial receipt authorizes another
SDK call, a repair direction or edits to the artist.
