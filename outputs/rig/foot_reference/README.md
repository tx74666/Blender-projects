# Rain foot reference audit

Source: `D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend`, object `RIG-rain`.
Read and exercised in a separate Blender 5.2 background process. No Rain or X file was saved. Embedded CloudRig and shading scripts were not executed; all native drivers remained valid.

## Two requested controls

- `ROLL-Foot_Control.R` is a remote foot-roll handle behind and above the heel. It is parented to `MSTR-Foot.R`. Translation, scale, and local Z rotation are locked. Local X rolls backward/forward; local Y banks the foot. The handle's own origin is not a deformation pivot.
- `FK-Toe.R` starts at the toe root / ball of the foot, with its tail at the toe tip. Its three rotation axes are unlocked. It has no direct bone parent; an Armature constraint blends between `FK-Foot.R` (weight `1-ik`) and `IK-Toe.R` (weight `ik`). Therefore this toe control works in either leg mode. It rotates the toe from the ball, independently of the ankle and foot.

## Foot-roll mechanism

- `ROLL-Foot_RollBack.R`: head at heel, parent `IK-TGT-Foot.R`.
- `ROLL-Foot.R`: head at ball, tail at ankle; parent RollBack. A Copy Location constraint moves its ball pivot to `ROLL-Toe.R`'s tail.
- `ROLL-Toe.R`: head at toe tip, tail at ball; parent RollBack.
- `IK-Foot.R` inherits `ROLL-Foot.R`; `IK-Toe.R` inherits `ROLL-Toe.R`.
- `FK-Foot.R` copies `IK-Foot.R` when IK is enabled. The visible toe control inherits either this FK foot or the IK toe as described above.

Rotation Transform constraints are local-to-local, ADD, with motion extrapolation disabled. Input/output values below are degrees, rounded; exact radians are in `rain_foot_audit.json`.

| Target | Input control channel/range | Output mechanism channel/range |
| --- | --- | --- |
| RollBack | X: -90 to 0 | X: -60 to 0 |
| RollFoot, normal roll | X: 0 to 135 | X: 0 to 118.2 |
| RollFoot, counter roll | X: 90 to 135 | X: 0 to -31.8 |
| RollFoot, bank | Y: -45 to 45 | Z: -25 to 25 |
| RollToe, tip roll | X: 90 to 166.5 | X: 0 to 169.3 |
| RollToe, bank | Y: -60 to 60 | Z: -10 to 10 |

The visible control itself limits X to -90 through +130 degrees. The separate piecewise transforms therefore continue to reference ranges larger than the accessible maximum.

Verified transform probes:

- X +15: foot rotates about ball approximately 13.133 degrees; toe stays still.
- X -15: heel pivot rotates approximately -10 degrees; foot and toe move together.
- X +100: foot rotates approximately 80.49 degrees; toe-tip pivot approximately 22.131 degrees.
- Y +15: foot bank approximately 8.333 degrees; toe-tip bank approximately 2.5 degrees.
- Z +15 via Python: handle rotates, but does not drive the foot. Normal UI locks Z.
- Toe X/Y/Z +15: toe and its stretch/deform descendants rotate 15 degrees; foot and ankle remain unchanged.

## Standalone wire geometry

`rain_foot_wires.json` exports raw vertices, edges, normalized vertices, bounds, original shape-object matrix, and display parameters. Normalization divides every coordinate by the largest raw dimension, preserving the mesh origin and axes.

- Foot Roll: `WGT-FootRoll`, 58 vertices / 58 edges, in local YZ plane. Shape scale `(0.043964956,)*3`, no bone-size scaling.
- Toe FK: `WGT-FK_Limb`, 32 / 32, in local XZ plane. Shape scale `(1.460000038,)*3`, multiplied by toe length `0.077872865`.
- Main Foot: `WGT-Foot_Parent.R`, 46 / 46.
- Both requested controls have no `custom_shape_transform`, zero custom shape rotation, and zero custom shape translation. Their bone frame provides the displayed orientation.

Existing canonical `addons/character_designer/ATTRIBUTION.md` identifies these Rain widgets as CC BY 4.0 and already covers heel-roll, foot-outline, and finger-ring silhouettes. Keep the existing credit when reusing this geometry:

**Rain Rig (CC) Blender Foundation | studio.blender.org**

Source listed in that attribution: https://studio.blender.org/characters/rain/v3/

No Rain rig objects, drivers, scripts, or rig implementation were copied into add-on source by this audit.
