# Pinned saved-model export validator 001

Prepared only. This entry has not launched Blender or produced an actual-model
FBX. Root inspects the script and uses the shared serial native window before
running it. Recheck available physical memory immediately before launch; do not
add a heavy job below about 200 MB, and slow/recheck near 98% usage. Do not overlap
Unity compilation/import, another background Blender test, or an offline build.

Input is exactly saved `X.blend`, 34,840,263 bytes, SHA256
`468bb6b297c56dd4b9c5f2dcd171ac240e31b9e87c4d6af998a1f64e76aafd29`.
The entry verifies every file in the frozen 190-file 0.77.43 projection before
opening input and again at the end. A new artist pin needs new explicit evidence;
do not edit the constant to evade a refused old input.

After confirming Blender 5.2 and resource ownership, use an unused run directory
and report path. This command is a prepared launch, not an executed validation:

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup --disable-autoexec -t 1 --python-exit-code 1 `
  --python 'D:/Blender/Projects/Character/X/validation/hair_export_worklist_20261015/validate_saved_export_001.py' -- `
  --run-dir 'D:/Blender/Projects/Character/X/validation/hair_export_worklist_20261015/actual_saved_export_001' `
  --report 'D:/Blender/Projects/Character/X/validation/hair_export_worklist_20261015/actual_saved_export_report_001.json'
```

No existing output is overwritten. An unsuccessful run keeps its local input,
job, log/report and partial output; use new names for any retry. The process
never calls `begin_export`, starts a nested worker, saves the artist, registers
the whole add-on, publishes through the coordinator, or accesses Unity Assets.

The script loads the frozen package in an independent namespace. It briefly
registers only the four existing model-export configuration PropertyGroups and
their Object pointer to read the actual saved include and simplified-material
choices, then removes exactly those registrations. It does not register Scene
Character Setup or substitute a guessed setup. Existing `collect_character`
must yield precisely `CoshaRig`, `Clothes`, `Cosha`, `Dress`, `Hair`, `Shoes`,
`Stocking`; a mismatch refuses the run. The observer checks targeted native
source state before/after config/capture and snapshot serialization.

Existing Hair, Dress and Forearm capture functions generate the same worker-spec
fields as `begin_export`. Saved filename/asset identity and material choices are
retained. Only the destination is a fresh local validation stage, so there is no
prior manifest and `had_forearm=False` follows the fresh-destination branch.
Production destination files and saved Unity material matches are not inspected
or published. No active artist preview is stopped: this is the saved-file state
in an unregistered disposable process.

`libraries.write` creates a persistent local snapshot with the actual model
snapshot roots. The same process reopens it, calls frozen
`unity_export_worker.export_job` directly, verifies output paths/FBX header,
uses the Hair verifier against actual FBX bytes and checks Forearm and Dress
binding/correspondence receipts. It then clears only its private process data
and uses Blender's real FBX importer to verify the six meshes, one armature,
exported bone inventory, vertex counts, artist Shape Keys and skin targets.
The final checks protect artist disk, the frozen package, validator/observer,
snapshot/job and actual output pins.

Acceptance requires process exit 0, `completed=true`, all protection checks,
actual sidecar/FBX roundtrip success, and review of retained warnings. The job
contains the required raw worker inputs once; the top-level report contains
pins, counts and compact proof summaries. No Unity import/Avatar/deformation,
animation/physics bake, unsaved artist changes, material appearance, or complete
world/rest numerical equivalence is claimed. This does not exercise production
manifest publication, prior/stale-file handling or material-match application.
