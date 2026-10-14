# Standalone composition UI fixture — 2026-10-11

`tools/run_character_composition_ui_fixture.py` is a separate root-invoked
Blender entry. Importing it launches nothing. It opens only the immutable QA
seed saved by the official numeric fixture's explicit callback after numeric
and physical B proofs pass. The user artist file is never opened by this
runner. The numeric scope completes its own original-scene recovery first;
the UI process subsequently owns its intentional edits, Undo and save/reopen.
No runtime source, projection, deployment or release is changed by this tool.

Root invokes the tool inside its separately scheduled Blender process with
`--python <absolute runner path> -- --fixture <absolute actual fixture JSON>`.
Root still owns the verified executable, serial window, current memory read
and process lifecycle. Set `BLENDER_USER_DATAFILES` to an empty child of a new
UI evidence directory. Keep the fixture JSON outside that directory. Existing
reports, `.blend` files or cache files cause refusal before acceptance.

The strict fixture schema is `x.validation.character-composition-ui-fixture/1`.
Its exact fields are:

- `inputBlend`, `inputBlendSha256`: the original numeric driver's verified
  saved-artist input copy. Artist `X.blend` is rejected.
- `addonPackage`, `runtimeManifest`, `runtimeManifestSha256`: the same pinned,
  complete 167-file 0.77.25 projection used by numeric acceptance. The existing
  `verify_character_composition_native.runtime_projection` verifies and loads it.
- `numericReport`, `numericReportSha256`: the independently saved, completed
  native report, including original fixture path/hash and `qa_seed` receipt.
- `seedBlend`, `seedBlendSha256`, `sceneName`, `rigName`, `targetGuid`,
  `modelSha256`, `workItemId`: exact values from that receipt; `rigName` must be
  `CoshaRig`. Supply a real prepared B Work Item ID, never a row label or clip name.
- `evidenceDirectory`: the new directory for this process's cache and reports.
- `sessionHelper`: `{path, sha256}` for the pinned session acceptance helper.
- `sessionConfig`: required `createAWorkCopy` boolean, two to four distinct
  finite `seekSeconds`, and finite `poseTolerance` greater than zero and at
  most `0.0002`. Optional `rotationControl` and `aRotationControl` name exact
  native inputs; optional `aWorkItemId` is an actual existing UUID. The runner
  supplies the helper's output directory and `character_designer` module.
- `schema`: the schema above. Unknown fields and publication/output overrides
  are rejected.

The numeric report must prove prior Actions/assets and historical recovery,
and its seed receipt must pin the completed physical report and its hash.
The first two physical entries must be the same actual prepared SOURCE B
variants and fresh model as the numeric proof. Their two saved native item IDs
are authenticated separately from Work Item IDs.

The saved Rig retains every exact historical Scene membership plus the
official copied QA Scene. Both membership names and the native adoption owner
are checked; the original Scene is preserved. After loading the seed, the
runner verifies the exact target, current workspace/model, prepared Link,
readonly Source cache, sealed packet and 217-bone native scope. It explicitly
activates that row's Custom and proves its fresh native Action/slot association.
The linked-model API returns `(Path, digest)`; the runner unpacks it, checks
the digest against the fixture, and pins the actual file path. A changed model
still fails the canonical source helper before UI acceptance.

Run this UI process before Parent Collect/Prepare expands the shared workspace
catalog. The seed deliberately pins its original workspace bytes; that pin is
not replaced with a newer hash. The subsequent Raise stage has its own explicit
initial-snapshot and same-identity catalog-extension admission. The UI-edited
saved copies are never used as the Raise stage's collected Hold source.

`composition_session_acceptance.run` may then author the disposable B and
supported genuine A work copy, and save/reopen its active, closed and edited
fixtures. The caller keeps only plain IDs/reports across these operations and
never enters the numeric fixture's native-ID recovery `finally`. Disk hashes
for the immutable seed/input/runtime manifest/proofs/model/packet/Source caches
and all catalog Source/B Links are checked even when the session helper fails.
It starts no export worker or Source/B publication.

`composition_ui_run_report.json` records admission, helper results and exact
immutable file hashes. Native acceptance remains pending root's explicit
fresh window. `tests/test_character_composition_ui_fixture.py` has 21 passing
pure admission tests; these validate inputs, proof/ID/membership routing and
evidence ownership, and exercise the actual canonical model helper body for
tuple unpacking and digest/changed-file rejection. They do not claim Blender
UI, Undo or save/reopen success.

The adjacent X staging `standalone_ui_fixture_source_report.json` pins the
tool, tests and this handoff. No actual native IDs are generated in examples.
