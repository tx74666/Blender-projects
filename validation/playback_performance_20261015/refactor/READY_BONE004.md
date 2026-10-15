New Bone004 runner copies preserve the original bone clip/synthetic runners and
all their existing source pins. They import field/isolation/select_scene from
the protected v4 frozen runner, so an EMPTY referencing an Image shares only
that readonly Image; writable object/animation/deformation data stays private.

`native_bone_preview_runner_004.py` SHA256:
`49fd87b87da91ef5e282c93c430ba0473b0d7ba4448b584800ad49442c00d9a4`.
`native_bone_synthetic_runner_004.py` SHA256:
`0ae1a6eeb875a76be1b4504808d0a6e2e0fcfcc69bb4e9f188bf6dfdf33fde02`.
Actual runner/witness dependencies are in `bone_runner_dependencies_004.json`.

The saved-clip Bone004 accepts `--admission-only`. It captures only the current
private saved frame, builds the disposable graph/helper backend, requires the
same basis/evaluated matrix oracle, compares strict fields and numerical
coordinate/normal metrics, protects/restores the source, and closes all owned
state. Both all-30 fields remain false and no ABBA blocks run. It reports exact
strict fields and coordinate/normal exactness separately; numerical differences
never become eligible automatically. The ordinary default remains the full
30-frame comparison and controlled ABBA after strict fields pass.

No formulas, metric definitions, strict other-field requirements, fixed matrix
bound or cleanup gates were relaxed. Original runner hashes remain
`154962c4...` and `2a43f657...`; bone metrics remain `a8a25ec0...`.

These files compile. The validation agent started no native/GUI job, edited no
artist scene and deployed nothing. Root chooses a reviewed staged package and
unused report paths before serially invoking native checks. A later helper-bake
source addition needs its own fresh stage; these file copies do not claim that
such a backend was measured or integrated.
