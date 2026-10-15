# Synthetic006 source-only 入口

保留 Synthetic005；新 Synthetic006 只改四行支持链引用，统一使用 source witness V6、bone support V7、FrozenV7 的现有 helper。原五种姿态、Subsurf0/1、fixture、矩阵/几何门槛、清理和 CLI 均未改。Stage05 source 与 Stage02 fixture manifest 保持原封印。此入口不替代保存角色的 FrozenV7/Bone 准入，也不阻塞它们。

- `native_bone_synthetic_runner_006.py` SHA256 `6dfc731c37e54103687e0dc78eac93866afe73f191f6460d2ac83ec1a0725ab1`。
- `synthetic_bone_dependencies_006.json` SHA256 `4c24bb5ff0c9e3e5c1e02774ce2fd1869f541354e0a3b475690aafe73d06144b`；封印新支持链、原005、几何 oracle、Stage05/Stage02 manifest，并记录完整参数。

Root 获得共享原生窗口后才执行；报告目标必须全新。此准备阶段只做编译/差分核对，未运行 Blender/GUI，未声称数值验收或 FPS。

```powershell
& 'D:/Blender5.2/blender.exe' --background --factory-startup -t 1 --python-exit-code 1 --python 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_synthetic_runner_006.py' -- --artist 'D:/Blender/Projects/Character/X/X.blend' --addons 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/addons' --source-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_05/source_manifest.json' --fixture-manifest 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/staged_20261015_02/fixture_manifest.json' --report 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor/native_bone_synthetic_report_006.json'
```

运行只生成独立 fixture，不打开 `.blend`；实际 PASS 仍需读取真实报告的矩阵、完整几何差分和清理结果。`completed` 不代表数值误差已被接受；报告保留 `numeric_error_acceptance_pending=True`，没有全角色播放/FPS 结论。
