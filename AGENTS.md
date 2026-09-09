# Shared add-on development

For RR Helper or Character Designer requests, the canonical development sources
are under `D:\MyRepository\Blender-addons-by-Randy\addons`. Read that repository's
`AGENTS.md` and make plugin code changes there, even when this task starts in X.

This project's `addons/character_designer` is a validation/deployment copy.
Update it from the shared repository with its `tools/deploy_local.py
--project-addons D:\Blender\Projects\Character\X\addons`, and verify using `--check`.
Do not edit the copy first and copy changes back into the repository.

Character assets, scene work, and real-model integration checks remain in X.
