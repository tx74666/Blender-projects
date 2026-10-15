Stage03 is a new source seal for the Blender 5.2 compositor API fix. Stage02,
`native_frozen_report_002.json`, v2 and its witness remain original protected
evidence. Report002 failed during Scene copying after all 30 source golden
frames; its failed candidate was not a performance result.

Stage03 source manifest SHA256:
`f619021f7252af04001ae9e7380bab66cda073756a9e34d7db1db61687b157af`.
193 package files were copied exactly; 161 Python files are sealed. Scene builder
SHA `dcf7e5bcdbc58ae5e85800654619c66abb443f91952f1f8d0e9575cbc36276e5`.
Fixture manifest SHA `89285391212babbeed8559101723f249742f9b7c06b916ac05dcdda2d5f1c9f0`.
Stage receipt SHA `cf4f1faeaf88914d343420d9be617f9bd9cb7b816d65247510770d5a72c896ca`.

The new standalone `private_playback_native_runner_v3.py` adds progress at golden
and candidate frames 10/20/30 and initial read-only source Action/slot/NLA layout
metadata. The exact comparison, timing and cleanup gates are unchanged. V2 SHA
`e24adcc2...`, witness SHA `3994f582...` remain unchanged. No validation agent
native job, GUI action, addon deployment or artist save was started.

Root owns serialized execution. First run `scene_builder_smoke_003.py` with
Stage03. This tiny factory process opens no `.blend`, registers no addon, and
checks Cube/Material/World/compositor/nested-group remapping and source pointer
protection, cleanup, source seals and artist disk pin. An unused report path is
required: `native_scene_smoke_report_003.json`.

After that actual smoke passes, the full run uses v3, the same fixed input404,
Stage03 package/manifest, and an unused `native_frozen_report_003.json`. The
commands are the Stage02 commands with the corresponding stage/script/report
names replaced. Bone runners continue importing the unchanged v2 helpers and
use Stage03 only after root decides the frozen proof permits further testing.

The v3 initial animation layout observes native ID pointers/UIDs, current Action
bindings, slots, track/strip frame ranges, blend/influence/time settings and
scene timebase. It contains no FCurves and authorizes no helper bake or adoption.
All new scripts compile. No new native/FPS result is claimed by preparation.
