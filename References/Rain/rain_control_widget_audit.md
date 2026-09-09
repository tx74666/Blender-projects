# Rain v3.2 control-widget audit (read only)

Source: `D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend`

- Blender: 5.2.0 LTS, opened with `--factory-startup --background --disable-autoexec`
- Armature: `RIG-rain`, 2166 bones, identity object matrix
- Source SHA-256 before/after audit: `D0EBAC00DCF5841F4A3F02F6576A065DF988C200B20BCAD8D05115D28F92AE5B`
- Rain was never saved. Tiny values below about `1e-6` are retained where useful but are modeling noise for reproduction.

## Pole line and arrow

Rain uses three bones for each visible pole arrow, not one static widget:

1. `IK-Line-Forearm/Shin.L/R` begins at the elbow/knee and ends at the pole. It is parented to the evaluated upper limb and has a World-space `STRETCH_TO` constraint targeting the pole. It displays `WGT-Pole_Line`.
2. `IK-Pole-Forearm/Shin.L/R` is the actual location-only pole control. It displays `WGT-ArrowHead`, but its `custom_shape_transform` is the DSP bone below.
3. `DSP-Pole-Forearm/Shin.L/R` shares the pole head, is parented to the pole, and has a World-space `DAMPED_TRACK` with `TRACK_NEGATIVE_Y` targeting the lower-limb bone. The arrow therefore stays aimed along joint-to-pole as the rig moves.

The pole rotation and scale channels are locked. The line and DSP bones are mechanism/display bones and should be non-selectable. Rain's rest pole distance is about `0.424797` for all four limbs. The DSP rest length is `0.052021891` for arms and `0.046198756` for legs.

Exact display settings: each `IK-Line-*` has zero custom translation/rotation, no transform bone, uniform custom scale `0.424796999`, and `use_custom_shape_bone_size=False`. Each `IK-Pole-*` has zero custom translation/rotation, scale `(1,1,1)`, `use_custom_shape_bone_size=True`, and its side-matched DSP bone as `custom_shape_transform`. The DSP bones have no shape of their own.

```python
POLE_LINE_VERTICES = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 1.0, -0.0000002806264945),
    (0.0, 1.0, -0.0000002806264945),
)
POLE_LINE_EDGES = ((2, 0), (0, 1), (1, 3), (3, 2))

ARROW_HEAD_VERTICES = (
    (-0.474555194, -1.0,  0.474554807),
    (-0.474555194, -0.999999940, -0.474555612),
    ( 0.474555194, -0.999999940, -0.474555612),
    ( 0.474555194, -1.0,  0.474554807),
    ( 0.0,          0.0, -0.000000048),
)
ARROW_HEAD_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 0), (3, 4), (1, 4), (4, 2))
```

The duplicated pole-line vertices only overdraw the same segment. Character Designer can use the visually equivalent `((0,0,0), (0,1,0)) / ((0,1),)` safely.

## Hand IK outline

`IK-Hand_Parent.L/R` both use the same `WGT-Hand_IK` object/data. Object transform is identity. Pose-bone custom-shape translation and rotation are zero; uniform scale is `0.101697966`; `use_custom_shape_bone_size=False`; no transform bone. The shared mesh works on both sides because the control-bone rest matrices are mirrored.

```python
HAND_IK_VERTICES = (
    ( 0.507616699, 0.071150608, -0.000000215),
    ( 0.497480452, 0.085770570, -0.097545192),
    ( 0.467504233, 0.127871066, -0.191341609),
    ( 0.418951690, 0.192710653, -0.277785063),
    ( 0.353838533, 0.273602426, -0.353553325),
    ( 0.274862766, 0.361968160, -0.415734798),
    ( 0.185380891, 0.445415586, -0.461939752),
    ( 0.089344025, 0.506406367, -0.490392625),
    (-0.009000459, 0.527022839, -0.500000000),
    (-0.105621733, 0.499436408, -0.490392625),
    (-0.197058186, 0.431743503, -0.461939752),
    (-0.280352741, 0.342119187, -0.415734798),
    (-0.352816731, 0.248339325, -0.353553295),
    (-0.411986977, 0.163004369, -0.277784944),
    (-0.455785364, 0.094863214, -0.191341534),
    (-0.482678682, 0.050729472, -0.097544953),
    (-0.491744846, 0.035423212,  0.000000268),
    (-0.482678592, 0.050729472,  0.097545460),
    (-0.455785334, 0.094863214,  0.191342041),
    (-0.411986917, 0.163004413,  0.277785450),
    (-0.352816433, 0.248339400,  0.353553653),
    (-0.280352324, 0.342119187,  0.415735006),
    (-0.197057813, 0.431743443,  0.461939901),
    (-0.105621301, 0.499436349,  0.490392774),
    (-0.008999976, 0.527022719,  0.500000000),
    ( 0.089344561, 0.506406069,  0.490392566),
    ( 0.185381427, 0.445415139,  0.461939573),
    ( 0.274863482, 0.361967742,  0.415734470),
    ( 0.353839159, 0.273601979,  0.353552878),
    ( 0.418952167, 0.192710176,  0.277784616),
    ( 0.467504442, 0.127870739,  0.191341296),
    ( 0.497480631, 0.085770361,  0.097544789),
)
HAND_IK_EDGES = tuple((i + 1, i) for i in range(31)) + ((0, 31),)
```

Rain's upper arm plus forearm length is about `0.418006346`, making its hand-widget scale about `24.3%` of arm-chain length. For a reusable plugin, preserve the normalized mesh and derive a uniform per-rig scale rather than copying `0.101697966` literally.

## First-finger-segment widget

`FK-Thumb1`, `FK-Index1`, `FK-Middle1`, `FK-Ring1`, and `FK-Pinky1` share `WGT-FK_Limb`. It is a 32-point XZ loop (Y is effectively zero). Most points lie on radius `0.409725934`, but the local-X cardinal points are extended to `-0.5` and `+0.5`. Those two ears produce the small visible bump on the back of the finger. On Rain's left index, bone local +X is approximately world +Y, i.e. the dorsal direction for the character's facing convention.

Equivalent clean generation:

```python
FINGER_VERTICES = []
for i in range(32):
    angle = i * math.tau / 32
    x = -0.409725934 * math.sin(angle)
    z =  0.409725934 * math.cos(angle)
    if i == 8:
        x = -0.5
    elif i == 24:
        x = 0.5
    FINGER_VERTICES.append((x, 0.0, z))
FINGER_EDGES = tuple((i + 1, i) for i in range(31)) + ((0, 31),)
```

All use no transform bone, zero rotation, `use_custom_shape_bone_size=False`, and local +Y translation `0.028` toward the distal finger. Index has local Z translation `0.003`; Ring has `0.002`; the others are zero. Left uniform scales: Thumb `0.046889067`, Index/Middle/Ring `0.027146302`, Pinky `0.019742765`. Right uses the same values but negative X scale to mirror.

## Root outline and roles

Both `ROOT` and `ROOT_Child` use the same identity-transform `WGT-Root`, with zero custom translation/rotation and `use_custom_shape_bone_size=False`. Uniform scales are `1.01` and `0.91`, giving two concentric selectable frames. Both controls have all location, rotation, and scale channels unlocked.

`ROOT` is unparented and parents `ROOT_Child` plus four dummy-parent branches. `ROOT_Child` parents the character's pelvis/property/locator branch and is a target of the hand, foot, pole, head, eyes, and thigh/upper-arm parent-switch constraints. In effect: outer/global transport plus inner character/space transport.

```python
ROOT_VERTICES = (
    (-0.461178720, 0.0, -0.461178720), ( 0.461178720, 0.0, -0.461178720),
    (-0.461178720, 0.0,  0.461178720), ( 0.461178720, 0.0,  0.461178720),
    (-0.443159282, 0.0,  0.443159282), (-0.443159282, 0.0, -0.443159282),
    ( 0.443159282, 0.0, -0.443159282), ( 0.443159282, 0.0,  0.443159282),
    ( 0.480463743, 0.0, -0.265761197), ( 0.480463743, 0.0,  0.265761226),
    ( 0.500000000, 0.0,  0.250185013), ( 0.500000000, 0.0, -0.250184983),
    (-0.265761197, 0.0, -0.480463743), ( 0.265761197, 0.0, -0.480463743),
    ( 0.250185013, 0.0, -0.500000000), (-0.250184983, 0.0, -0.500000000),
    (-0.480463743, 0.0,  0.265761226), (-0.480463743, 0.0, -0.265761197),
    (-0.500000000, 0.0, -0.250185013), (-0.500000000, 0.0,  0.250185013),
    ( 0.265761197, 0.0,  0.480463743), (-0.265761197, 0.0,  0.480463743),
    (-0.250185013, 0.0,  0.500000000), ( 0.250184983, 0.0,  0.500000000),
)
ROOT_EDGES = (
    (8,11),(10,9),(12,15),(14,13),(16,19),(18,17),(20,23),(22,21),
    (7,9),(10,3),(8,6),(1,11),(6,13),(14,1),(12,5),(0,15),
    (5,17),(18,0),(16,4),(2,19),(4,21),(22,2),(20,7),(3,23),
)
```

## Foot outline

The exact control hierarchy is `MSTR-P-Foot_Parent -> MSTR-Foot_Parent -> MSTR-Foot`. The unparented `MSTR-P-*` helper carries the driven Armature parent-switch constraint. The two visible descendants have no constraints and all TRS channels unlocked. `MSTR-Foot.L/R` uses `WGT-Foot_Parent.L/R`, a side-specific 46-point shoe-sole loop. Right is the X mirror of left; edges are identical. Object/data transforms are identity. On `MSTR-Foot`: custom translation `(0, 0.080000006, 0.026000002)`, rotation X `-pi/2`, scale `(-0.237634003, 0.237633690, 0.237633690)`, no transform bone, and `use_custom_shape_bone_size=False`. `MSTR-Foot_Parent` uses the same shape with translation `(0, 0.080000006, 0.042000003)`, rotation X `-pi/2`, scale `(-0.267634004, 0.287633628, 0.287633628)`, no transform bone, and `use_custom_shape_bone_size=False`.

```python
FOOT_PARENT_L_VERTICES = (
    ( 0.099234894,  0.871687770,  0.000727093),
    ( 0.194205865, -0.071024314,  0.000438197),
    (-0.186365515,  0.825411975,  0.000631400),
    (-0.007368974, -0.099799521,  0.000472580),
    ( 0.194076076,  0.578032792,  0.000023564),
    (-0.278784126,  0.530485034,  0.000021460),
    (-0.159259334,  0.173546672, -0.000034734),
    ( 0.210402682,  0.207939595, -0.000031146),
    ( 0.189964861,  0.628364623,  0.000021308),
    ( 0.173066407,  0.732698798, -0.000003148),
    ( 0.132744923,  0.832533777, -0.000075472),
    ( 0.038417019, -0.114003643, -0.000292528),
    ( 0.101531841, -0.113783777, -0.000094001),
    ( 0.160142154, -0.095507771, -0.000294212),
    (-0.120430134,  0.072465695, -0.000068591),
    (-0.099163838,  0.022602918, -0.000097153),
    (-0.037944019, -0.073271163,  0.000075338),
    ( 0.039580546,  0.889435172, -0.000213846),
    (-0.038276959,  0.885206699, -0.000079284),
    (-0.119038858,  0.861792743, -0.000274932),
    ( 0.206765726,  0.260585546, -0.000018355),
    ( 0.202150643,  0.366447002,  0.000004608),
    ( 0.199428171,  0.467522144,  0.000018613),
    (-0.228298619,  0.778306067, -0.000147301),
    (-0.273770511,  0.677303314, -0.000016196),
    (-0.283078045,  0.578685939,  0.000017398),
    (-0.255540878,  0.424573123,  0.000017627),
    (-0.221513256,  0.327776104,  0.000002502),
    (-0.179988638,  0.225336537, -0.000021708),
    ( 0.211478710, -0.038747311,  0.000076016),
    ( 0.223457947,  0.059776247, -0.000092626),
    ( 0.220201626,  0.108500011, -0.000064606),
    ( 0.156389371,  0.783612728, -0.000081165),
    (-0.256016791,  0.727344453, -0.000117335),
    ( 0.182560578,  0.685647905,  0.000012276),
    (-0.281778038,  0.633144438,  0.000004574),
    ( 0.197160974,  0.524336100,  0.000022641),
    (-0.269585460,  0.479019910,  0.000021530),
    ( 0.200832501,  0.417848617,  0.000012667),
    (-0.239865437,  0.377017140,  0.000011302),
    ( 0.203929767,  0.312606871, -0.000006503),
    (-0.200427473,  0.276034266, -0.000009422),
    (-0.140166104,  0.122850493, -0.000049585),
    ( 0.215601921,  0.158007219, -0.000045798),
    (-0.073479183, -0.023025773, -0.000221944),
    ( 0.219749227,  0.007535274, -0.000183419),
)
FOOT_PARENT_EDGES = (
    (4,8),(34,9),(32,10),(10,0),(3,11),(11,12),(12,13),(13,1),
    (42,14),(14,15),(44,16),(16,3),(0,17),(17,18),(18,19),(19,2),
    (7,20),(40,21),(38,22),(36,4),(2,23),(33,24),(35,25),(25,5),
    (37,26),(39,27),(41,28),(28,6),(1,29),(45,30),(30,31),(43,7),
    (9,32),(23,33),(8,34),(24,35),(22,36),(5,37),(21,38),(26,39),
    (20,40),(27,41),(6,42),(31,43),(15,44),(29,45),
)
FOOT_PARENT_R_VERTICES = tuple((-x, y, z) for x, y, z in FOOT_PARENT_L_VERTICES)
```

For a generic humanoid, the exact Rain outline can be normalized and X-mirrored, but its final X/Y scale should be derived from the detected foot/toe chain. Skeleton data has no reliable shoe width, so a conservative width-to-length default (about `0.35`) should remain adjustable.

## Foot-roll arrow and mechanism

`ROLL-Foot_Control.L/R` is parented to `MSTR-Foot`, uses identity object/data `WGT-FootRoll`, zero custom translation/rotation, uniform scale `0.043964956`, no transform bone, and `use_custom_shape_bone_size=False`. Location and scale are locked; rotation Z is locked; local X and Y are available. A local Limit Rotation constrains X to `[-90 deg, 130 deg]`.

The mesh lies in the local YZ plane. It is two incomplete circular arcs joined into a curved arrow. The last two vertices form the arrow tip/bridge.

```python
FOOT_ROLL_VERTICES = (
    (0.0,  0.499999821, -0.000000231), (0.0,  0.490392715, -0.097545438),
    (0.0,  0.461939812, -0.191342011), (0.0,  0.415734619, -0.277785212),
    (0.0,  0.353553355, -0.353553444), (0.0,  0.277785122, -0.415735066),
    (0.0,  0.191341475, -0.461939901), (0.0,  0.097545043, -0.490392804),
    (0.0, -0.000000121, -0.500000536), (0.0, -0.097545303, -0.490392804),
    (0.0, -0.191341788, -0.461939901), (0.0, -0.277785420, -0.415735066),
    (0.0, -0.353553712, -0.353553444), (0.0, -0.415734977, -0.277785212),
    (0.0, -0.461940259, -0.191341788), (0.0, -0.490393072, -0.097545020),
    (0.0, -0.500000179,  0.000000198), (0.0, -0.490393072,  0.097545415),
    (0.0, -0.461940259,  0.191341937), (0.0, -0.415734977,  0.277785450),
    (0.0, -0.353553712,  0.353553355), (0.0, -0.277785122,  0.415735513),
    (0.0, -0.191341430,  0.461940169), (0.0,  0.391893446,  0.391893089),
    (0.0,  0.353553981,  0.353552997), (0.0,  0.415735245,  0.277784556),
    (0.0,  0.461940438,  0.191340879), (0.0,  0.490392715,  0.097544335),
    (0.0,  0.389615744, -0.000000231), (0.0,  0.382129461, -0.076010473),
    (0.0,  0.359958023, -0.149099678), (0.0,  0.323953897, -0.216459095),
    (0.0,  0.275500059, -0.275500298), (0.0,  0.216458902, -0.323954105),
    (0.0,  0.149099439, -0.359958321), (0.0,  0.076010227, -0.382129550),
    (0.0, -0.000000095, -0.389616102), (0.0, -0.076010391, -0.382129550),
    (0.0, -0.149099603, -0.359958321), (0.0, -0.216459259, -0.323954105),
    (0.0, -0.275500417, -0.275500298), (0.0, -0.323953897, -0.216459095),
    (0.0, -0.359958380, -0.149099454), (0.0, -0.382129818, -0.076010257),
    (0.0, -0.389616102,  0.000000198), (0.0, -0.382129818,  0.076010436),
    (0.0, -0.359958380,  0.149099901), (0.0, -0.323953897,  0.216459066),
    (0.0, -0.275500000,  0.275500238), (0.0, -0.216458946,  0.323954046),
    (0.0, -0.149099261,  0.359958261), (0.0,  0.237160593,  0.237160176),
    (0.0,  0.275500357,  0.275499642), (0.0,  0.323953897,  0.216458440),
    (0.0,  0.359958380,  0.149098799), (0.0,  0.382129461,  0.076009601),
    (0.0, -0.170220375,  0.410949498), (0.0,  0.247122675,  0.369844228),
)
FOOT_ROLL_EDGES = (
    (1,0),(2,1),(3,2),(4,3),(5,4),(6,5),(7,6),(8,7),(9,8),(10,9),(11,10),
    (12,11),(13,12),(14,13),(15,14),(16,15),(17,16),(18,17),(19,18),(20,19),
    (21,20),(22,21),(24,23),(25,24),(26,25),(27,26),(0,27),
    (29,28),(30,29),(31,30),(32,31),(33,32),(34,33),(35,34),(36,35),(37,36),
    (38,37),(39,38),(40,39),(41,40),(42,41),(43,42),(44,43),(45,44),(46,45),
    (47,46),(48,47),(49,48),(50,49),(52,51),(53,52),(54,53),(55,54),(28,55),
    (56,22),(57,23),(51,57),(50,56),
)
```

Rain maps negative X rotation to a heel/back pivot (`-90..0 deg` becomes `-60..0 deg`). Positive X drives the foot pivot (`0..135 deg` becomes `0..118.2 deg`) and adds counter-roll after `90 deg` (`0..-31.8 deg`). Y bank `-45..45 deg` maps to Z bank `-25..25 deg`. Its reverse chain is approximately `IK-TGT-Foot -> ROLL-Foot_RollBack -> ROLL-Foot / ROLL-Toe -> IK-Foot`.

## Clavicle / shoulder arc

Current shoulder-only verification used the later on-disk Rain file with
SHA-256 `1BDC4A696079E479DDA2A3CDB93294A421C99C7D340511F5EBB58528298D1BFE`.
It was inspected read only in a separate background Blender process.

The arc in the shoulder screenshot is the shared custom shape on
`MSTR-Clavicle.L/R`, not a hand IK or upper-arm control. Both controls are
non-deforming, unconnected children of `FK-Chest_Child`, have no constraints,
use XYZ rotation, and leave all TRS channels unlocked. Their rest matrices are
X-mirrored and their `matrix_basis` values are identity.

Each side uses the same identity-transform object/data, `WGT-Clavicle`:

- `44` vertices, `44` edges, `0` faces; no modifiers or drivers;
- one closed wire outline made from two 22-point arcs joined at their ends;
- bounding box X `[-0.5, 0.5]`, Y `[0.233489, 0.680513]`,
  Z `[0.200244, 0.617273]`;
- the second arc is the first arc plus the constant offset
  `(0, 0.3557755, -0.1035641)`;
- zero pose-bone shape translation and rotation, no transform bone;
- uniform custom scale `0.14`, `use_custom_shape_bone_size=False`, wire width
  `1.0`.

The first normalized arc, ordered from X `-0.5` to `+0.5`, is retained below.
Create the second arc by adding the constant offset, keep the same X order, and
connect the two left and two right endpoints to obtain the exact closed band.

```python
CLAVICLE_ARC_A = (
    (-0.500000119, 0.233489260, 0.303807884),
    (-0.452380955, 0.255385429, 0.379028291),
    (-0.404761970, 0.272454798, 0.437666982),
    (-0.357142985, 0.286127359, 0.484636575),
    (-0.309523821, 0.297159553, 0.522535563),
    (-0.261904776, 0.306003600, 0.552917778),
    (-0.214285746, 0.312949568, 0.576779366),
    (-0.166666701, 0.318189800, 0.594781280),
    (-0.119047694, 0.321852505, 0.607363701),
    (-0.071428604, 0.324019670, 0.614808619),
    (-0.023809563, 0.324737132, 0.617273390),
    ( 0.023809491, 0.324737132, 0.617273390),
    ( 0.071428537, 0.324019670, 0.614808619),
    ( 0.119047567, 0.321852505, 0.607363701),
    ( 0.166666672, 0.318189800, 0.594781280),
    ( 0.214285657, 0.312949568, 0.576779366),
    ( 0.261904687, 0.306003600, 0.552917778),
    ( 0.309523731, 0.297159553, 0.522535563),
    ( 0.357142866, 0.286127388, 0.484636694),
    ( 0.404761791, 0.272454798, 0.437666982),
    ( 0.452380896, 0.255385429, 0.379028291),
    ( 0.499999881, 0.233489260, 0.303807884),
)
CLAVICLE_ARC_OFFSET = (0.0, 0.355775490, -0.103564069)
CLAVICLE_VERTICES = CLAVICLE_ARC_A + tuple(
    (x + CLAVICLE_ARC_OFFSET[0], y + CLAVICLE_ARC_OFFSET[1], z + CLAVICLE_ARC_OFFSET[2])
    for x, y, z in CLAVICLE_ARC_A
)
CLAVICLE_EDGES = (
    tuple((index, index + 1) for index in range(21))
    + ((21, 43),)
    + tuple((index, index - 1) for index in range(43, 22, -1))
    + ((22, 0),)
)
```

Rain's control is the upstream owner of both clavicle deformation and the
upper-arm roots, not merely a decorative shape:

```text
FK-Chest_Child
└─ MSTR-Clavicle
   ├─ STR-Clavicle
   │  ├─ DEF-Clavicle
   │  └─ DEF-COR-Clavicle_Front
   ├─ Root_Upperarm -> IK upper-arm branch
   └─ CT-FK-Upperarm -> FK upper-arm branch
```

`DEF-Clavicle` stretches to `STR-Upperarm1`; Rain then adds a tweak layer,
B-Bone scale drivers, a front corrective, and an FK hinge/space switch. Those
extra systems explain Rain's production deformation but are not required for a
first lightweight shoulder control.

## Character Designer recommendations

### Pole visuals

The full three-bone Rain mechanism is worth generating now because it is deterministic, has no handlers, and remains correct while the joint and pole move. Per existing pole, add only two owned non-deform helpers:

- `VIS_elbow_pole_line.L/R` or `VIS_knee_pole_line.L/R`: rest head at the evaluated joint and rest tail at the pole, parented to the upper source bone, `STRETCH_TO` the existing pole, line widget, all channels locked, non-selectable.
- `MCH_elbow_pole_aim.L/R` or `MCH_knee_pole_aim.L/R`: head at the pole, parented to it, `DAMPED_TRACK` with `TRACK_NEGATIVE_Y` to the lower source bone, all channels locked, hidden helper collection. Use it as the existing pole's `custom_shape_transform`.

The existing `CTRL_elbow_pole` / `CTRL_knee_pole` remains the only selectable control. Use the exact 5-point arrowhead, but use a clean 2-point line. Size the arrow from end-bone/character scale; do not hard-code Rain's DSP lengths. Register helpers and constraints with exact ownership so Remove/Rebuild/Undo remains transactional.

### Hand and foot shapes

- Replace the current hand octagon with the exact normalized `HAND_IK_VERTICES`; set `use_custom_shape_bone_size=False` and assign a derived uniform scale. Current target bones already follow the end bone's local Y/Z basis, which matches this widget's convention.
- A single normalized left-foot mesh plus negative per-side X scale is sufficient; two data blocks are unnecessary. Rotate the shape into the foot's local sole plane based on the detected end-bone/rest matrix, not a global `-pi/2` constant.
- Keep foot roll out of a widget-only patch. A minimal later implementation needs an owned `CTRL_foot_roll`, heel/toe/ball reverse-pivot helpers, and a final ankle target consumed by the existing leg IK and foot rotation constraint. Initialize every helper from the evaluated current pose, restore pose bases after topology changes, then validate upper/lower/end matrices for no pop before committing.

### One master control

Rain's two roots are useful for parent switching, but Character Designer can begin with one `CTRL_master`. A bone cannot move unrelated source roots without adding some dependency edge. The least invasive scheme is:

- parent all generated controls and mechanism helpers to `CTRL_master`;
- add one exact-owned `CHILD_OF` (or carefully tested before-original transform) constraint to each unparented source skeleton root, with inverse calibrated from the evaluated pose;
- preflight foreign constraints/animation, snapshot source and controls, evaluate, require no-pop, and roll back on any mismatch.

This preserves source parent pointers. If the constraint composition cannot be made exact for a particular rig, refuse rather than silently reparent source bones.

### Shoulder control prepared contract

For Character Designer's first shoulder pass, keep the useful upstream
semantics without copying CloudRig's corrective network:

1. Detect the shoulder automatically and conservatively, without adding another
   first-pass panel field. Accept only the analyzed upper arm's direct,
   side-matched, non-owned parent when its name confidently matches
   `shoulder`/`clavicle`/`collar` and it has a non-empty parent. If detection is
   missing or ambiguous, silently skip this optional control and keep the
   existing Arm IK unchanged; never guess a chest/spine bone as the shoulder.
2. Generate non-deforming `CTRL_shoulder.L/R` bones at the source shoulder rest
   matrices, parented to the source shoulder's existing chest parent. Do not
   reparent source bones or touch vertex groups.
3. Add one exact-owned, no-pop `COPY_TRANSFORMS` constraint from each source
   shoulder to its generated control, using `POSE -> POSE` spaces and
   `REPLACE`. The existing upper arm remains a child of the source shoulder, so
   both the current IK root and a future FK root inherit the shoulder naturally
   while world-space hand targets can remain planted. The dependency is acyclic:
   `Master -> source root -> chest parent -> CTRL_shoulder -> source shoulder ->
   upper arm`; the two-bone IK ends at the upper arm and does not write back to
   the shoulder.
4. Reuse one owned `WGT_Randy_Shoulder` object for both sides. Start at about
   `1.49 * source_shoulder.length`, Rain's scale-to-clavicle ratio, with an
   implementation test on X before choosing the final multiplier. Bone rest
   orientation supplies the right-side mirror; do not create a second mesh.
5. Keep location and rotation available. Treat scale as a deliberate product
   decision: Rain leaves it open, but a lightweight rig without its B-Bone and
   corrective layers should initially lock scale unless deformation tests prove
   it safe.
6. Make the new bones, widget, source constraints, and registry records part of
   the same Build/Remove/Rebuild transaction under schema 3. Schema 1/2 rigs
   remain removable as-is and require an explicit Rebuild to upgrade; updating
   the add-on must not silently alter an existing rig. Each Arm record carries
   `shoulder` and `shoulder_control`: both populated means the complete optional
   shoulder inventory is required, both empty means the existing four-role Arm
   remains valid, and any half-filled state is corruption.

Required tests: left/right detection and mirrored widget reuse; missing or
ambiguous shoulder detection safely skipping the option while Arm IK remains
unchanged; Build and Rebuild no-pop; shoulder motion with a planted hand IK
target; source shoulder/upper-arm follow; exact Remove/Undo/Redo recovery;
foreign-constraint refusal; and protected mesh, shape-key, modifier,
vertex-group, action, and driver fingerprints.
