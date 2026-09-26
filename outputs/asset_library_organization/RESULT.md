# Asset Library organization — 2026-09-26

Completed and visually verified in the running Blender 5.2 X project.

- Procedural Material contains the original 21 material catalogs, preserving their UUIDs and simple names. Its source .blend is unchanged (SHA-256 checked).
- Created an empty Pose Library with the catalog hierarchy Pose Library / Crossa. No placeholder poses or animation data were created.
- Corrected Nodes to D:\Blender\Helper\Asset-Libraries\Costom\Nodes.
- Corrected Procedural Material to D:\Blender\Helper\Asset-Libraries\Costom\Procedural Material.
- Registered Pose Library at D:\Blender\Helper\Asset-Libraries\Costom\Pose Library.
- Preserved BlenderKit registration and all other catalog entries.
- Saved Blender preferences; did not save or change the character's pose/action data.

All Libraries initially retained the old material path's cached catalogs, even after refreshing. The legacy material catalog was also backed up and synchronized with the same 22 catalog entries. Temporarily refreshing that existing library at its legacy path, then restoring the configured helper path, resolved the stale catalog conflict. All Libraries now visibly groups the material categories correctly. No restart or library deletion was used.

Evidence: organization_manifest.json, live_configuration_result.json, cache_refresh_result.json. Original preferences and both catalog files are backed up in backups/20260926-205126.

Usage: basic single-frame poses belong in Pose Library / Crossa. In Pose Mode, use Create Pose Asset and choose the external Pose Library and character catalog. Double-click a compatible pose asset to apply it. Multi-frame animations are Actions and need the Action Editor/NLA workflow; Save Asset Catalogs saves classification, not a new pose.
