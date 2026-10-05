# Hair Motion evidence and documentation correction draft — 2026-10-04

This is a review draft in X Validation. It does not update canonical documentation, release notes, central records or installed assets. It records the successful concurrent native Unity run completed at 2026-10-04T14:10:10.8509952Z and preserves the earlier sequential result as separate historical evidence.

## Proposed current status for `docs/hair_motion.md`

Replace the opening `Status:` paragraph with:

> Status: Real-character Blender preview and unbaked FBX/active-sidecar export are verified. Unity isolated fixtures passed full-32 native conversion/persistence and concurrent focused dynamic-independence checks, followed by all-32 finite fixed-root sampling. Official Wiggle installation and the open artist scene's Character Designer 0.76.1 refresh/configuration/save remain pending. These checks do not claim equal-time or physical equivalence between Wiggle and Magica, or a per-component performance result.

The following is the supporting evidence summary for the documentation/release update:

Character Designer Hair Motion has verified real-character Blender preview, ordinary unbaked FBX plus active sidecar export, and Unity native full-32-strand conversion and persistence in isolated fixtures. The real Hair source has 32 independent four-bone chains, 128 segments, and Front 10 / Side 8 / Back 14 groups. Reciprocal synchronization shares settings while the physical chains remain disjoint.

Unity 6000.5.9f1 native lifecycle verification passed explicit imported binding, four-strand transient preview and exact restoration, Undo/Redo, injected late rollback, all-32 committed capture, save/publish/reopen, and preservation of enabled state, settings, selection, colliders and stable identities. The author baseline is archived and quarantined; application remains explicit. Dress physics is outside the Hair change.

The final native PlayerLoop run used two focused four-strand copies concurrently for 96 shared actual frames, stopped all eight, then sampled all 32 strands for 60 frames: 8×96 + 32×60 = 2,688 samples. `Passed`, `NativeChecksPassed`, `NativeIndependentResponseValidated`, `ExactNativeStageScheduleComparable`, `ContextPreserved`, `FilesPreserved`, `PlayStartSettingPreserved` and `BuilderLeaseReleased` are true; `Error` is null. The focused copies shared actual frame/reset/input and measured native timesteps/update/skip schedules. Changing only one strand's gravity produced maximum geometric-tail response difference 0.02753540128469467 m; the other three strands' maximum difference was exactly 0 m. All measured positions were finite; maximum fixed-root error was 2.604774635983631e-7 m.

Preserve the earlier sequential 4→4→32 run and its original `Passed:false` report. It completed the same 2,688 samples with finite fixed roots and successful preservation, but its focused runs had different actual native timing, so it did not prove independent response. The later concurrent PASS supersedes that limitation for this explicit focused native test; it does not retroactively change the sequential flags or raw report.

`PhysicalEquivalenceValidated`, `ExactTimeScheduleComparable` and `RenderFrameScheduleComparable` remain false. The latter two compare measured Unity time to the recorded Blender 1/30-second source schedule, separately from the successful comparison between the concurrent native copies. Source/Wiggle differences remain index-aligned diagnostics, not equal-time trajectory evidence. Solver coefficients are not interchangeable; physical equivalence is not a completion prerequisite. Particle origins differ, and measurements use the authenticated geometric endpoint without adding an end bone. The 96 prepared inactive native configurations also make this functional QA, not a clean per-component performance benchmark. Gameplay isolation and the owned one-cycle Builder lease prevent ordinary author-save workflows from contaminating this QA.

The successful lifecycle run preserved Adventure dirty=true with 46 roots. The later Play QA context was Billiards clean with one root and returned to sole Billiards. These are separate runs with a human scene change between them; no claim is made that Adventure is currently loaded or was restored/saved by the later QA.

## Proposed 0.76.1 release-status correction

Keep the existing 0.76.1 Reconcile Strands change and 16-test Blender 5.1.0 result. The local 144-file package was deployed and checked for Blender 5.1, Blender 5.2 and X. Its ZIP SHA256 is `52fed6e515892bbe84a2d0a1702719b9750d11d0848cfd3bf9c95a640983ca2e`.

Replace the blanket “remaining Unity native integration checks are still pending” statement with: “Unity full-32 native lifecycle and concurrent focused dynamic-independence checks passed in isolated fixtures; all 32 strands also completed finite fixed-root PlayerLoop sampling with context/files/start-setting preservation and lease release. Official Wiggle installation and the open artist scene’s 0.76.1 refresh, configuration and save remain pending action-time approval and verification. No Wiggle/Magica equal-time or physical-equivalence claim is made.” Local deployment does not establish the version currently loaded in an open artist session.

The actual published consumer fixture was exported by Character Designer 0.76.0; 0.76.1 changes only reconciliation-button availability. Do not relabel that existing export as generated by 0.76.1. It records `bake_anim=False`, `simulation_baked:false`, 32 exact retained chains and an active hash-bound sidecar. The sidecar's original `conversion_validation:pending` declaration remains unchanged; later Unity evidence is recorded separately.

## Evidence and source provenance

| Evidence | Exact path / identity |
| --- | --- |
| Real Blender Head-input preview and exact restoration | `D:\Blender\Projects\Character\X\Validation\hair_motion_20261004\real_hair_preview_validation_51_headlocal3.json`; SHA256 `e77db2307671820d39ce45f79a6551dc4c74df69202e5deb843a1c1dbebf0883` |
| Native ordinary export and roundtrip | `D:\Blender\Projects\Character\X\Validation\hair_motion_20261004\character_consumer_ea1a4e078c074b46885222978263d933\character_consumer_validation.json`; SHA256 `7cf27b8ab234e2d16a2d80466d718c74e8a34956c5aab41599828827b11c7005` |
| Published FBX / sidecar / active manifest | Same consumer folder, `published\Cosha_HairValidation.{fbx,hair-motion.json,cdesigner.json}`; FBX SHA256 `603648483019bc847df8d1e36e21a4a236739a6a3a395425220ddef6051b753c`, manifest SHA256 `3bd901bc38486b6ff6fa9667c8e60c4e2da3ca455e020ab511b62bdf336498c7` |
| Pure reader, separate Runtime DTO / Editor reader assemblies, 38 checks | `D:\Blender\Projects\Character\X\Validation\hair_motion_20261004\unity_parser_actual_fixture_split38.json`; this is not native physics evidence |
| Full32 native lifecycle pass | `D:\Unity Projects\RandomRealm2\Logs\CharacterTuning\HairMotion\native-lifecycle-20261004-115839-0506100.json`; SHA256 `beb25e7c119b66596ec6e4fdd99a420d3c18fa4d4454ab3a6e7e3dbcce3ccefa` |
| Sequential 2,688-sample dynamic report | `D:\Unity Projects\RandomRealm2\Logs\CharacterTuning\HairMotion\native-play-1d32735017a84c1a8ea7216e73bcfe3f-final-5e9981d98f674860bf78c156ab9c28a1.json`; SHA256 `0795095f280ecd6bbb81b45916261d50fd89ebdc94a72756a9a41c555cf750ca` |
| Final concurrent 8→32 dynamic PASS, 2,688 samples | `D:\Unity Projects\RandomRealm2\Logs\CharacterTuning\HairMotion\native-play-537cc03b542243898eabc2645653958a-final-ef81022ad2004c18b47aa72ca7680f0f.json`; SHA256 `0ab87144ccfb404a81f18faf083717a07a46a1870d4181bb53808fcebeb3a9fa` |
| 0.76.1 UI regression result | `D:\Blender\Projects\Character\X\Validation\hair_motion_20261004\hair_ui_0761_20261004_1811.log`; `HAIR_MOTION_UI_TESTS_OK 16` |

The sequential run used formal `Assets\Scripts\Editor\CharacterHairMotionPlaybackVerification.cs` SHA256 `b6c068e6c8b0b15f94a24bb4a2f239462f81c903fe1a6559ffde478faba36f49` and `SceneBootstrapper.cs` SHA256 `ac4bffffead76545b39e186a0c1e792a12290c1612f10a333a2842559497e5ea`. Its deployment provenance is `D:\Unity Projects\RandomRealm2\Docs\PendingPatches\CharacterHairMotion_20261004\UrpOriginalSources-20261004-133852-c32f9111\deployment.json`; that preparation-time record's `nativeCompile:pending` predates the successful native run.

The final concurrent run used formal Playback SHA256 `4eac0e51932b39bfaae6aee8f2cf3f9639936d0e9a609234913e53de8f79aba8`; Bootstrap remained `ac4bffffead76545b39e186a0c1e792a12290c1612f10a333a2842559497e5ea`. These hashes were read from the actual Assets files after the run, not inferred from a staging filename.

`CharacterHairMotion.integration.sha256.json` in the same staging folder still describes `uncompiled_staging`, no Assets modification, and an older patch. Preserve it as historical evidence; do not use it as a current formal-source index or attach its hashes to newer native results. Any final formal index must snapshot actual deployed file hashes and link the matching lifecycle/final concurrent reports. Do not replace earlier raw reports, mark sequential `Passed:false` as passed, or merge different scene contexts into one preservation claim.

The remaining artist installation/refresh/configuration/save requires its separate action-time approval and verification. Canonical documentation/release edits proposed above and any central-record append have not been applied by this draft.
