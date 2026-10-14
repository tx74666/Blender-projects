# Current thumb diagnosis — 2026-10-10

Scope: offline reads of the two captured JSON files only. No Blender/Unity operation, asset repair, runtime/code change, frame/Action switch, or save was performed by this analysis. The temporary live-read service lifecycle belongs to the parent investigation.

Inputs:

- `live_readonly.json`: SHA256 `4d15899a75959ede9ff67a3a3caa0e43f780adc131be6b328604449f7954371d`.
- `evaluated_readonly.json`: SHA256 `137e293ebbde5cb5094693ba2452819f85434c328b5d11f062118ed45a37ae0b`.
- Current returned scene: `Animation Worklist · Cosha`, frame 1, `CoshaRig.001`, Action `Cosha · Walk_N · Custom`. Source scene: `Scene`, frame 46, `CoshaRig`, no active Action. The two poses differ.

## Confirmed measurements

Both sides have all three thumb bones, matching parents and Deform enabled. Every thumb group has positive weights. All six thumb heads and Rest frames remain nearly equal between source/returned rigs; maximum head distance `8.3681e-7`, maximum Rest matrix component difference `3.8445e-6`.

Only the terminal thumb tails have a substantial difference: left `0.0383234918 -> 0.0314386450`, right `0.0383235030 -> 0.0314385369` Blender units, approximately 17.97% shorter. Their heads and Rest frames remain nearly unchanged. Full returned inventory has 217 bones and no children of either `thumb.03` or either `eye`; these bones have no current constraints.

The current mesh has 14,470 base/evaluated vertices. Its 728 recorded thumb-related vertices include 578 mixed-weight vertices. No positive weight references a missing returned bone, no vertex is unbound, and valid Deform weight sums lie in `[0.9999999180, 1.0000000671]`. An independent normalized LBS calculation agrees with evaluated coordinates: maximum error `4.0294e-7`, mean `1.8182e-7` in rig space; mixed-weight maximum `3.7958e-7`.

For each side, `thumb.03` weight >= 0.99 selects 63 vertices. All 63 actually have weight 1 on that bone with no other positive weights. Raw coordinates were transformed mesh -> rig -> Rest bone local; evaluated coordinates were transformed mesh -> rig -> Pose bone local. Pose/Rest bone matrices match the prior snapshot exactly, and mesh-to-rig transform changes are below `4.1e-8`.

| Side | Raw local Y reach | Evaluated local Y reach | Ratio | Maximum local point difference |
| --- | ---: | ---: | ---: | ---: |
| L | 0.0427990080 | 0.0427987988 | 0.9999951125 | 4.0294e-7 |
| R | 0.0427987307 | 0.0427987104 | 0.9999995255 | 2.6067e-7 |

Maximum pairwise distances are also unchanged within numerical error: L `0.0297323923 -> 0.0297324512`, R `0.0297324360 -> 0.0297323799`. This confirms the current distal thumb region undergoes rigid motion without material elongation.

The six thumb bones have 18 location and 18 scale Action curves, each with 59 recorded keys. Maximum recorded location deviation from 0 is `7.1526e-7`; maximum recorded scale deviation from 1 is `9.5367e-7`. Current location deviation is at most `4.1723e-7`, current scale deviation at most `7.1526e-7`. NLA is empty. These statistics concern key values and the current evaluated frame; they do not certify every interpolated frame.

Source `CD Forearm Twist.L.002/R.002` values are 1, but their maximum raw thumb-region delta is only `9.4317e-8`. The older keys with larger deltas have value 0. Current forearm correction does not explain a visible thumb elongation.

## Confirmed versus inferred explanation

Confirmed: imported/returned terminal bone display length differs; current thumb tip geometry is not stretched; bones/weights are present; current movement follows ordinary LBS and the active Walk pose.

Inference about the screenshot: shortened terminal bone tails leave more of the existing thumb mesh visibly beyond the bone, and the rotated Walk pose changes its apparent projection. These measurements support that explanation, but do not measure the screenshot camera/view projection or prove that every perceived shape difference comes from it. Bone-display reconstruction must not be mislabeled as an actual geometry or weight repair.

## Optional terminal display-length restoration assessment

For the four proven leaf bones (`eye.L/R`, `thumb.03.L/R`), restoring only source length along the current verified Rest Y axis would restore display extent and selection geometry while retaining head, axes, parent and bind frame. The current modifier uses vertex groups, no envelopes, and linear skinning; the independent LBS evidence depends on Pose/Rest matrices rather than tail length. There is no demonstrated deformation failure requiring this operation.

Future IK or controller construction may use terminal length/tail to choose endpoints, aim/control positions or widget scale. Therefore display-length provenance can matter before building those features, even though the current linear skin is unaffected. This is an assessment only; no direction was selected and no bone was modified.

Canonical `unity_runtime/ANIMATION.md` documents a reversible Unity packet import onto a matching existing native/CD control rig after strict bind and control-graph validation. `Link / Import` and `docs/animation_worklist.md` instead import the exact Unity model into an independent editing scene. Historical X had six finger Rest mismatches and used the matching-model route. Current compatibility of the artist rig with the latest packet requires the existing guard; matching bone names alone is not that proof.
