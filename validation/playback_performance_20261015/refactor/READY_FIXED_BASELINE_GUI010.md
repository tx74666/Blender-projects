Minimal fixed baseline GUI entry: `native_fixed_baseline_gui_010.py`, SHA256
`421efa17f7ab048ea73cecc5fb04ca662f2d034991501382a42bf251ef09f914`
(9353 bytes). Independent source review, syntax, exact input/Stage05 pins and
AST checks passed. These checks imported no bpy and started no GUI/native work.
FPS009 remains unchanged at a6ce26f86c4fa6aee5dc58fc68f59010a12c9983324133f56e01e2ab2db471ed.

The entry accepts only an unused report path. Input and Stage05 are constants:
40644… /34691613-byte input_saved_20261015.blend, manifest d62c3178…bac34 and
all 162 Python source pins. It rejects an already opened/dirty/background GUI
or an artist/hardlink input. Standard addon.register then
open_mainfile(load_ui=False) preserves the new factory UI. It does not seek,
play, compute geometry, call a solver, defer/replace normal callbacks, save or
quit. A single observer timer waits for two naturally settled runtime states,
removes only itself and leaves the normal GUI/addon alive for Root.

Root's later launch entry, only after Console's actual END and its resource
gate, is:

```powershell
& 'D:/Blender5.2/blender.exe' --factory-startup --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_fixed_baseline_gui_010.py' -- --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_fixed_baseline_gui_report_010.json'
```

The report records PID, loaded fixed file, disk/stage pins, natural lifecycle
changes, saved frame/clip/sync metadata and factory UI structure before/after.
It does not perform an FPS sample or certify viewport comparability. Root still
aligns camera/view, viewport resolution and shading/material prewarm before
Console-installing FPS009 with kind=baseline, allow_fixed_baseline=true and
the observed owned PID. Keep baseline/Bake launch threading settings matched.

Artifact009's source has one libraries.write call, explicitly writing {scene};
it does not explicitly submit Screen IDs. GUI008 begins in a new factory GUI,
so the intended Scene-only artifact uses that layout; baseline's load_ui=False
now avoids the old input's saved layout. No actual Artifact009 file/receipt was
available during this source-only check, so its actual Screen inventory is not
claimed verified. The source-only basis and limitation are recorded in
fixed_baseline_gui_010_preparation.json. Compare actual factory UI snapshots
and FPS009's view/style/resolution fields before drawing performance conclusions.
