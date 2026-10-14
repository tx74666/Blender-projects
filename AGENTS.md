# Shared add-on development

For RR Helper or Character Designer requests, the canonical development sources
are under `D:\MyRepository\Blender-addons-by-Randy\addons`. Read that repository's
`AGENTS.md` and make plugin code changes there, even when this task starts in X.

This project's `addons/character_designer` is a validation/deployment copy.
Update it from the shared repository with its `tools/deploy_local.py
--project-addons D:\Blender\Projects\Character\X\addons`, and verify using `--check`.
Do not edit the copy first and copy changes back into the repository.

Character assets, scene work, and real-model integration checks remain in X.

# Save completed scene work

The user asks that completed Blender scene operations be saved. After authorized
scene work, save the current artist `.blend` and verify Blender reports success.
Keep isolated test scenes separate. Saving does not authorize applying a pending
model repair or choosing a repair direction for the artist.

# Performance history and ownership

X owns Character Designer scene integration and its optimization records.
For follow-up Original20 return/integration work, begin with
`validation/composition_20261011/fresh_rigging_round_20261012/current_return_summary.json`.
It indexes accepted evidence. The older `current_return_checkpoint.json` contains
historical intermediate versions, processes and pending states; do not treat
those as current work. Observe the live artist identity again before new scene
operations. External file pins can be checked without Blender using the shared
repository's `tools/verify_file_pin.py`; file identity alone is not scene-operation
authorization.
Before another performance investigation, read
`D:\Codex\資料庫\电脑与工作环境\Blender性能優化台帳.md` and follow its
evidence links; target new symptoms or changed code rather than repeating all
previous checks. Append the date, source/runtime versions, verified model and
reasoning effort (unknown means unrecorded), comparable measurements, validation
limits, deployment/refresh/save state and the next investigation trigger.
Keep raw project evidence here and index it in the existing Codex Console
database. Builder6 / Build WIP owns RR Helper; RandomRealm2 owners retain their
project evidence and the existing Unity performance-history entry points.
