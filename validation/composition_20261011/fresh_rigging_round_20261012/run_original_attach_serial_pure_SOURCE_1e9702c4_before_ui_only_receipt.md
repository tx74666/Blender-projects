# R7 bounded serial pure runner — SOURCE only

No execution or syntax compilation has occurred while preparing this runner.
Building/Console hold remains effective. This file is not an ACTUAL_START.

The helper runs **core** first (19 Attach + 7 editing-data + 15 old Worklist =
41) and **ui** second (14 Attach UI + 68 old UI = 82). Each suite gets its own
fresh bundled Python process with `-B`, an explicit suite name and an audit
guard. No discovery of all tests, package registration, Blender, SDK, worker,
build, deployment, install or artist-file access is performed by the helper.
The seven Source pins are checked before/after each suite and on completion.

ResourceStart must be created by Root after Parent's actual fresh ACK. Its
exact SHA is passed on the CLI. Required document fields are:

- `schema`: `x.validation.resource-start/1`
- `scope`: `original-rig-current-pure-checks` for the new pure-only window, or
  `latest-original-artist-savecopy` for a separately approved combined window;
  `owner`: `Root`
- `status`: `ACTUAL_START`; `token`: exact `--scope-owner-token` argument
- `owner_thread`: `01a12751-d08f-7630-b790-18db26fe3186`
- `parent_thread`: `01a12305-aada-7273-b72c-54a41aad77e4`
- `created_utc`, `actual_start_utc`: identical explicit UTC-Z strings
- `deadline_utc`: explicit UTC-Z, later than start and at most 210 seconds later
- `pure_allowed`: genuine boolean `true`
- `worker_allowed`, `native_allowed`, `new_blender_allowed`, `build_allowed`,
  `install_allowed`, `deploy_allowed`, `artist_disk_write_allowed`: genuine
  boolean `false`

The pure-only scope requires genuine `sdk_allowed=false` and does not await a
future snapshot authorization. Only the separately approved combined scope
may authorize the one original SaveCopy caller after both phases; neither
scope authorizes any SDK call from this helper. SaveCopy always requires its
separate invocation owned by Root. No original save/snapshot is mixed into a
pure-test receipt.

Future templates only, **do not invoke under HOLD**:

```powershell
& 'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012\run_original_attach_serial_pure.py' --phase core --resource-start '<actual Root resource-start JSON>' --resource-start-sha256 '<actual lowercase SHA256>' --scope-owner-token '<actual token>' --output-root '<fresh owned ROUND/core directory>'
& 'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012\run_original_attach_serial_pure.py' --phase ui --resource-start '<same actual Root resource-start JSON>' --resource-start-sha256 '<same actual lowercase SHA256>' --scope-owner-token '<same actual token>' --output-root '<fresh owned ROUND/ui directory>'
```

Root verifies the final helper Source SHA before invocation. Each phase creates
an exclusive `r7_serial_pure_claims/<ResourceStartSHA>.<phase>.json`. UI requires
the same Start's actual successful core41 receipt and closed owned children.
The first failure consumes that phase's claim. No same-phase blind retry or
receipt overwrite is supported; an actual Source failure and later change need
a new reviewed Source state and a newly approved Start.

RAM is read from Windows `GlobalMemoryStatusEx` immediately before a phase and
each suite. Below 200 MiB, or at/above 97.5% (near 98%), it waits five seconds
and reads again. At least 200 MiB is required after that reread. All suites are
serial; the old 1 GiB threshold is not used. Deadline/source drift stops before
the next suite. An already started child is always awaited naturally; no kill
or terminate call exists. Normally the five tiny suites should finish below
30 seconds; resource rereads or a slow child can take longer and are reported,
never hidden by a guessed result.

The child audit guard rejects process launches, socket connections, real
`bpy`/`mathutils` imports, add-on `__init__`/registration and other candidate
source imports. The reviewed fake modules used by the tests remain allowed.
This is an explicit prevention boundary for the approved pure tests, not a
general-purpose operating-system sandbox.

Each suite retains exact binary stdout and stderr, its natural process PID/
exit/time, Source pin, actual unittest `Ran N`/`OK` counts and duration. The
combined log is stdout bytes then stderr bytes; it makes no chronological
interleaving claim. The aggregate log concatenates those completed suite logs
in suite order. Failure/interruption harvests actual child output after natural
exit. Skip, wrong count, nonzero exit or missing official stderr summary cannot
become PASS.

Future `receipt.json` uses `x.validation.r7-actual-serial-pure/1`, matching
`prepare_unified_package_r7.py.actual_pure_receipt`: exact `source_files`,
`suites[].test_file/raw_log/total/passed/failed/exit_code/actual_executions/
unique_new_cases`, `process_test_total`, `process_exit_code`, `process_raw_log`,
`execution_mode=SERIAL_PYTHON_B`, actual-run and unchanged-source flags.
`process_test_total` is explicitly the sum of fresh suite-process unittest
counts (41 or 82), not a fictitious combined unittest process. Editing/old
Worklist/old UI reruns add zero unique cases; only Attach19 and UI14 are new.

The helper's `actual_run` begins false and becomes true only after a real child
starts. It retains process handles through natural exit. A failed/pending
receipt cannot satisfy the R7 producer. The old preRun Source owner `66abfefb`
and every earlier Source draft remain immutable; no test PASS is inherited.
