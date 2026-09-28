# Build project snapshot

`Build.blend` is a byte-for-byte copy of the saved working scene
`D:\Blender\Projects\Build\WIP\Builder6.blend`, published alongside `X.blend`.
It does not include changes that have not been saved in the open Blender window.
Use Blender 5.2 for this scene.

## Refresh before uploading

1. Save `Builder6.blend` normally in Blender.
2. Double-click `Sync-Build.cmd` in this repository.
3. Review the files in GitHub Desktop, commit, and push.

The script reads `tools/build_sources.json`, checks source and copied-file hashes,
copies the listed dependencies, then refreshes `Build.blend`. It skips identical
files. It never saves the live Blender session and does not commit or push for you.
The local sync receipt is in ignored `.codex-package/build-sync-receipt.json`.
If new external assets are introduced, update the dependency list after checking
the scene; the script does not discover new dependencies automatically.

## Dependency audit, 2026-09-28

The saved scene is 134,917,531 bytes. Its SHA-256 at first publication is
`121729484a436dad4caa53d74e6ff2aaa5c9cc4e3eef328ad277ea665c8f8085`.
Static inspection found 124 image datablocks: 110 packed and 14 external.
Of the external images, nine files exist and five references were already missing
in the working source. This audit did not open or render the scene in Blender.

Seven existing relative textures are included at their original `//textures/`
paths, so they resolve next to the repository's `Build.blend`:

- `BuilderMat_OuterWall_Stone_Interior_Image2_PBR_normal.png`
- `BuilderMat_OuterWall_Stone_Interior_Image2_PBR_roughness.png`
- `Material_001_basecolor.png`
- `outer_wall_stone_exterior_image2_final_basecolor_2k.png`
- `outer_wall_stone_interior_image2_final_basecolor_2k.png`
- `wall-005-outer-wall-stone-exterior-normal-2k.png`
- `wall-005-outer-wall-stone-exterior-roughness-2k.png`

Two images use absolute paths in the original scene. Backup copies are included
under `textures/BuildExternal/`: the Hub_Floor_Circular_A `icon.png` and
`Marble_Floor_Tiles_BaseColor.png`. The scene's original paths are preserved.
On another computer, use Blender's File > External Data > Find Missing Files and
select `textures/BuildExternal/` to relink these two files if needed.

The five missing references are under
`assets/models/modern-privare-h_892f1641-cd40-4133-a347-bf9ba13e38be/textures/`:

- `image_1_286330(NORMAL).png`
- `image_1_286330(NORMAL)000.png`
- `image_1_286330(ROUGHNESS).png`
- `image_1_286330(ROUGHNESS)000.png`
- `image_1_286330(ROUGHNESS)001.png`

They were not deleted by this cleanup, and no substitute textures were invented.
Static path inspection alone does not establish whether they affect visible materials.

The five linked nodes (Array, Randomize Transforms, Smooth by Angle, Lava, and
Wavy Marble) have Blender's `ID_FLAG_LINKED_AND_PACKED` flag. This marks those
datablocks and their dependencies as packed independently of an entire library
file, per [Blender's ID definitions](https://github.com/blender/blender/blob/main/source/blender/makesdna/DNA_ID.h).
The full external node/material libraries are therefore not duplicated here.
The scene uses Blender's built-in font.

## Upload scope

Only root `X.blend` and `Build.blend` are allowed as main scene uploads.
Necessary textures, references, project scripts, and existing add-on sources/tests
are retained. Generated previews, task artifacts, validation outputs, local
recovery backups, and old add-on ZIPs are ignored. Their original local copies are
preserved; removing them from the current Git tree does not erase old Git/LFS history.
