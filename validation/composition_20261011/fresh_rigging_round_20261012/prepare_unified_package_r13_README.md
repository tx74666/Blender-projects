# R13 package procedure — source preparation

Producer SHA256 7a8cf4202c34d43ad6bd4555afa0d7944a8dbff35205c42e5d087c2ffcb4f023; 33605 bytes. Preparation was source-only; actual targeted checks and combined package build subsequently completed as recorded below. No Blender, SDK or deployment was performed.

Baseline is immutable R12 package_815751c3 / version0.77.30 / map815751c3 / freezeD0A0 / manifestEB54 / receipt3477 / ZIPE533 / post0DC4 / release9E09. R12 packaged successfully but Native11 failed; no release or native acceptance is inferred. Its cleanup was intentional and must not be labeled natural success.

R13 expects version0.77.31 and only three payload changes: unity_animation_rigging.py, unity_animation_original_inputs.py and __init__.py. Other187 files remain exact. Forearm54C3, GunUI38A3 and Worklist24BA are fixed. File/Python counts remain190/158.

Use prepare_unified_package_r13.py --capture-and-build --final-admission PATH --final-admission-sha256 SHA once. Existing separate inspect/capture/build modes remain for diagnosis/recovery. The combined mode validates common inputs once and retains capture/build source rereads, official builder, ZIP byte/CRC/duplicate checks, old dist preservation and final source checks. No extra inspection prerequisite.

The admission template is deliberately incomplete and rejected until replaced by actual values. Rebind schema/version, current native/original_inputs/init exact pins, full map and shipped bytes, real owner/peer proof pins, actual targeted pure receipt/log/count and actual syntax receipt. Source owners cover all five implementations; peers cover the two changed implementations. The existing generic source_scope_verified proof shape is unchanged.

Run the affected test groups only: test_animation_rigging_recovery.py for display/handoff and test_original_inputs_contract.py for view_body. Include any directly necessary compatibility group only if its new change justifies it. A fresh portable receipt must pin all six current runtime files plus the three feature tests including test_original_inputs_view_body.py (9 minimum); it may also record actual additional test inputs. Its actual_pure_tests must equal only the tests actually executed with failures/errors/skips0 and unchanged input pins. Prior R12 192 tests remain historical via the exact package baseline; do not relabel them as current or rerun the whole suite merely to refresh observer constants.

Separate syntax is exactly10 files: six runtime, the three affected test files and certify_original_legacy_base_clock_latest_saved.py. Raw log uses AST_COMPILE_PASS filename sha256 and SOURCE_ONLY files=10 target_imports=0 tests=0 native=0. Full158 runtime AST remains in the producer.

Reuse actual clock07 certificate: source9F3647…/24915, reportCC0C749F…/169608, external releaseC275D5…/1148, legacy30. Latest snapshot5387/artistCC9A are the scenario inputs, not the clock report pin. The package stores this as historical_clock_certificate; native independently verifies current scenario bindings. No clock rerun is required solely because these runtime source fixes do not alter clock certification.

Actual completion: targeted recovery17/reference20/sampling6/original_contract8/view_body7 =58 PASS, syntax10 PASS, natural Python exit0 at 2026-10-12T16:12:46.6589797Z. Single combined package build natural exit0 at 2026-10-12T16:14:59.9453538Z, 9.0835994s. Package package_c70d56ee; manifest7EEC1298, freezeFA14B10E, receipt230C4F11, ZIP71319606. Physical post-readback confirms190/158/5656938 bytes and187 unchanged payloads. Historical192 tests were not rerun or relabeled current. Native11 remains failed.
