# R7 Source draft — original Rig Attach

This producer has not been compiled, inspected, captured or built. Building's
human-priority HOLD permits only Source authoring and physical file reading.
Do not run Python, AST, subprocesses, inspect-only, capture, build, Blender,
SDK, workers, installation or deployment until Root explicitly releases that
scope. Source preparation does not create or reserve a resource window.

The final destination is the existing original X.blend Scene/Rig. Preserve its
modifiers, design, materials, colors, Bone Collections, custom shapes and
controllers. Independent scenes are isolated tests. This producer does not
repair Rest, weights or native hierarchy, silently rebind old workspaces/rows,
or edit/save the artist.

## Exact candidate scope

R5 remains the complete shipped baseline: 188 files and 156 Python files.
Only animation_worklist.py and animation_worklist_ui.py may differ; the other
186 payloads must be byte identical. Native c5, init d66 and version 0.77.25
remain fixed. R6's unbuilt only80af preparation is historical ancestry, not
a captured package or transferable PASS/claim.

| Final file | SHA256 | Bytes |
| --- | --- | ---: |
| animation_worklist.py | d4de3eff83abd01e74ec7c92a67ea62be0314cda757cc83ac2663e9308b13aad | 53135 |
| animation_worklist_ui.py | e57c2f51b072ca1aa949d80fcec57265a91edf053f60bc34a9d5e396c0c44a9c | 43229 |
| test_animation_worklist_rigging_editing_data.py | f53bcee59ca3845a0567e414cd024b010d18ba10996777d86e1103033de26f68 | 14112 |
| test_animation_worklist_rigging_attach.py | be52410c4c954d5ec9b80424b1deb350355230d3db2f3daf19510a2700c95b8f | 30907 |
| test_animation_worklist_rigging_attach_ui.py | d7f6444b640f8d057aa8657f32a50653832b092a0223bb2ba4e4a690151fabd9 | 16155 |

The feature Source-pin subset grows from 19 to 23: one existing core pin is
replaced, and UI runtime plus three focused test pins are added. Regression
test pins/logs remain separately bound by actual pure receipts; their cases do
not increase cumulative unique counts.

## Required final admission

Every mode requires --final-admission and --final-admission-sha256. There is no
fallback to d4/e57 drafts, an old test total, or a guessed success. Even
inspect-only rejects missing, unexecuted or stale actual pure receipts.

Root must provide a newly authored, immutable admission with schema
x.validation.unified-r7-final-source-admission/1. It must bind the following
real inputs after actual checks. No such admission or PASS is created by this
draft.

- passed, source_only, final_source_stable and final_destination_existing_X_Rig
  must be true; native_execution_performed must be false. These attest the
  completed Source admission only, not original-Rig or native acceptance.
- current_sources contains exactly the five final file names in the table,
  each with an exact path/sha256/bytes record of its canonical file.
- source_owners contains core and ui exact receipt pins. They must bind their
  matching runtime and focused test Source. A previously closed Source-scope
  receipt with passed=false stays false; it is not interpreted as a test PASS.
  Actual testing is admitted only through the separate pure_receipts below.
- source_peers contains root and parent exact receipt pins. Root must bind
  the two runtimes and two Attach/UI focused tests; Parent must bind the core
  runtime and Attach test, with a real independent Source review. The
  historical editing-data owner/peer binds the unchanged f53 test separately.
- pure_receipts contains core and ui exact actual serial run receipt pins.
  Their required normalized schema is specified below. A summary without
  bound raw execution logs is rejected.
- unique_cases must contain historical_R5=262,
  historical_80af_editing=7, actual_final_Attach=19, actual_final_UI=14,
  regression_unique_additions=0, cumulative_total=302 and
  all_cumulative_cases_run_against_current_candidate=false.

The existing core pre-run owner 66abfefb and Root Source peer 7b389f20 have
passed=false and zero actual tests. UI-ready ae81a08a explicitly says checks
pending. Those immutable values must be preserved. They may authenticate
finished Source scope, while separate, completed real run receipts are still
mandatory before any R7 mode is admitted.

The real Parent core peer is
`D:\Unity Projects\RandomRealm2\.codex\task-staging\character-composition-20261011\generic-rigging-design\source-peer-r7\x-core-d4de.json`,
SHA ae1ac00c60515453fd55be5470bb615a7760b11cc41ef17ba4143d348b8f6c33,
3459 bytes. Only its exact known schema
randomrealm.character-rigging-worklist-core-source-peer/1 has a dedicated
reader. It requires SOURCE_PASS/Source-only flags, explicit false overall
native/test results, zero review run counts and no live/product/artist writes.
Only core and testDraftActuallyRead path/sha256/bytes fields are normalized:
absolute paths resolve to canonical spelling, SHA becomes lowercase, and
physical SHA/bytes must match the current core/Attach pair. The test draft
executed flag must remain false. Parent JSON is retained unchanged; no wrapper
or generic receipt normalization is created. Native, Root and UI proof readers,
actual pure gates and package scope remain unchanged. This compatibility edit
has not been compiled or exercised under HOLD.

## Actual serial pure receipt format

The normalized receipt schema is x.validation.r7-actual-serial-pure/1. Root
must derive it from actual serial Python -B executions and retained logs,
never fill it from this draft's planned totals. Required fields are passed,
source_only, actual_run and source_pins_unchanged_after_run=true;
native_execution_performed=false; process_exit_code=0;
execution_mode=SERIAL_PYTHON_B; source_files; suites; process_test_total; and
an exact, nonempty process_raw_log pin.

Each suite records file, exact test_file pin, total, passed, failed, exit_code,
actual_executions, unique_new_cases and a nonempty exact raw_log pin. Total
and passed must match, failed/exit_code must be zero, and actual_executions
must be at least one. All fields represent the real completed execution.

| Receipt | Required suite | Actual total | Unique additions |
| --- | --- | ---: | ---: |
| core | test_animation_worklist_rigging_attach.py | 19 | 19 |
| core | test_animation_worklist_rigging_editing_data.py | 7 | 0 |
| core | test_animation_worklist.py | 15 | 0 |
| ui | test_animation_worklist_rigging_attach_ui.py | 14 | 14 |
| ui | test_animation_worklist_ui.py | 68 | 0 |

Core process_test_total must be 41; UI must be 82. Core source_files must bind
the final core, Attach test and editing-data test. UI source_files must bind
the final core, UI runtime and focused UI test. Regression test Source is
bound by each suite's actual test_file pin. The new-origin compatibility
mechanism is part of the final nineteen focused Attach cases; do not add a
different new-origin suite or count the existing fifteen cases as new.

The future actual run scope is 123 cases. The cumulative 302 includes older
Source-bound provenance and must never be described as 302 cases newly run
against R7. The seven current editing regressions do not count again: their
seven cumulative additions already come from the actual historical80af log.

## Preserved evidence and future build

R5 actual native result remains FAIL at add_activate. The full report and
traceback, failure_scene.blend, retained-handle launcher/logs, natural exit,
original artist file/process guards and actual release are mandatory exact
pins. The old resource token never authorizes a new test. Native c5 reference
20 and recovery12 receipts/logs remain unchanged historical evidence.

After final real admission, future capture writes unique new R7 artifacts
and refuses overwrites. Future build uses the official pinned resolver and
builder, verifies frozen/canonical payload equality, checks both resolved
rename targets remain inside repository dist, preserves the old R5 dist ZIP
by a normal verified rename, and compares every one of the 188 ZIP entry
bytes with the complete manifest. Duplicate and directory entries fail;
testzip must return no CRC error. These functions are authored, not executed.

There is no version/init change, deploy/install, Git action, native/SDK/GUI
call, worker, old workspace rebind, or artist write in this preparation.
