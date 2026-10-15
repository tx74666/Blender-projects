# Artifact009 → 正常 GUI008 入口（2026-10-15）

状态：三个新源码已独立审查，纯检查/语法通过；本说明仅封印入口，未运行 Blender、未生成真实 Bake006/Artifact009 收据或候选 `.blend`，未验证 GUI FPS。既有 `READY_STAGE05_RUNNERS_V6.md`、V6 初始准入入口、Stage05 源码及已封印 007 均未修改。

## 顺序与必须保留的门槛

1. Root 按既有 V6 入口完成实际准入、Bone/几何验证及 Bake006，遵守 Console 实际 END、共享资源窗口和实时内存门槛。这里不另起一条初始准入流程。
2. 必须存在真实成功的 `x.private-helper-bone-bake/1` Bake006 收据。Root 审阅实际指标后明确选择该收据记录的 `exact` 或 `practical005`，并固定收据路径与 SHA256。没有真实收据或明确选择，停止；不能制作替代收据。
3. Artifact009 再跑完整 source/live/Bake 与 78 次原生 Action 重放，核对相同输入、Stage、策略、依赖和原始 Action/源场景/清理保护后，只写一个自有 Scene 到新的候选文件。`practical005` 仅适用于固定 source/live 几何筛选；Bake/live 与重复候选仍必须逐位一致。
4. 成功发布的候选及 Artifact009 收据才可交给独立新 GUI 进程的 GUI008。标准 `addon.register()`、`open_mainfile()`、load handlers/timers 自然运行；不 defer、不停用 handler、不手动调用 helper/core。验证 1–30 整数帧，每次 frame advance 后让事件循环运行，再读实际输出。
5. GUI008 PASS 后保留该预览 GUI，供 Root 后续测完整角色的正常视口播放 FPS。后台时间、序列化成功、GUI008 一致性 PASS 都不等于实时 FPS 通过；其他动作、子帧、物理仍未覆盖。候选不自动成为艺术家文件，也不自动部署。

## 依赖封印

下列路径均相对本说明所在目录 `D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor`；SHA256 为完整文件字节哈希。

| 文件 | SHA256 |
| --- | --- |
| `native_artifact_action_witness_008.py` | `c6881b78c9de8af661b6ecbf264e4e8a4f9861ce645246d9e8dccb1fc298b680` |
| `native_bone_bake_artifact_runner_009.py` | `67375ade603475bf0ba78d1db12b5863c067bebdbee8d723c3c317067730759d` |
| `native_artifact_reopen_gui_008.py` | `4f952e6a3da1c5a8b78902b9c419bca9edc8bcb7a358117240bd4ad4f05b8c31` |
| `native_bone_bake_runner_006.py` | `e4a776b283872ce4ea40f9d1d9c34e9ca16f6031491a70994c14290a4ca4a2c0` |
| `private_playback_native_runner_v6.py` | `3e8991008438b1174974b04c49be8cb14c5ded100949248c974773ae06a276d4` |
| `native_bone_support.py` | `a8a25ec0c009adc19bb6b11bbf5b20b594a1ef4f9db87c542261d503830d90c8` |
| `native_validation_support_v5.py` | `68451f7cc73d582da148b6a4efcbdf3596edaf4285310a3e40997273d70ff2ce` |
| `native_source_reference_witness_v5.py` | `e0a56ab2c38546a36dd90eaca1dc74ca1ad57da61bab7528b602144157ef8135` |
| `native_validation_support.py` | `3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a` |
| `BONE_ADOPTION_CRITERIA_005.md` | `de3dd16156b876db23f2f0e9aaeb70c7a1019ce51a991da588937ba400af7893` |
| `native_runner_dependencies_005_reviewed_v3.json`（原 V6 依赖入口，不改） | `6af6c2bfe15d99ac00717bae6f4a488d845dd2a984fc707f3e690abfa700dfa0` |
| `staged_20261015_05/source_manifest.json`（封印整个插件包） | `d62c3178ca6f0615fa4517440c157bba0ab2ced87cb64aa560ac1830197bac34` |

固定输入为 `D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend`，34,691,613 字节，SHA256 `40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721`。艺术家磁盘文件沿用 `D:/Blender/Projects/Character/X/X.blend`，执行时必须与实际已接受收据的磁盘 pin 相同；本说明不硬编造它的当前哈希。运行器还会记录/复验实际收据、脚本、witness、插件包与策略 pins。

## Artifact009 命令

只由 Root 在完成上述门槛后执行。下面两个 `ROOT_...` 必须改成实际审查结果；原样执行会在启动 Blender 前停止。输出和报告父目录必须已存在，目标文件必须全新，失败后不覆盖旧证据。

```powershell
$entry = 'D:/Blender/Projects/Character/X/validation/playback_performance_20261015/refactor'
$blender = 'D:/Blender5.2/blender.exe'
$artist = 'D:/Blender/Projects/Character/X/X.blend'
$savedInput = 'D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/input_saved_20261015.blend'
$stage = "$entry/staged_20261015_05"
$acceptedBake006 = "$entry/native_bone_bake_report_006.json"
$acceptedBake006Sha = 'ROOT_REVIEWED_REAL_SHA256'
$rootGeometryAcceptance = 'ROOT_MUST_CHOOSE_EXACT_OR_PRACTICAL005'
$artifactReport = "$entry/native_bone_bake_artifact_report_009.json"
$artifactOutput = "$entry/helper_baked_preview_009.blend"
if ($acceptedBake006Sha -cnotmatch '^[0-9a-f]{64}$' -or $rootGeometryAcceptance -notin @('exact', 'practical005')) { throw 'Root must pin real Bake006 evidence and explicitly choose its recorded geometry policy.' }
if (-not (Test-Path -LiteralPath $acceptedBake006 -PathType Leaf)) { throw 'Real Bake006 receipt is missing.' }
if ((Get-FileHash -LiteralPath $acceptedBake006 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $acceptedBake006Sha) { throw 'Accepted Bake006 receipt SHA differs.' }
if ((Test-Path -LiteralPath $artifactReport) -or (Test-Path -LiteralPath $artifactOutput)) { throw 'Choose fresh report/output paths; never overwrite evidence.' }
& $blender --background --factory-startup -t 1 --python-exit-code 1 --python "$entry/native_bone_bake_artifact_runner_009.py" -- --input $savedInput --artist $artist --addons "$stage/addons" --source-manifest "$stage/source_manifest.json" --accepted-report $acceptedBake006 --accepted-report-sha256 $acceptedBake006Sha --geometry-policy $rootGeometryAcceptance --root-geometry-acceptance $rootGeometryAcceptance --artifact-output $artifactOutput --report $artifactReport
```

退出码不替代报告验收。Root 应读实际报告的 `completed`、所有严格/source/cleanup/serialization gates、`artifact_published` 与 `artifact_publication_complete`，并核对真实文件 pin。任何失败保留报告及准确的 publication 状态；不要把候选存在误当成发布全部通过。

## 正常 GUI008 命令

在同一套路径变量下，先审核真实 Artifact009 收据并固定其 SHA，再执行。此命令创建独立工厂启动 GUI，不传入位置参数 `.blend`，不使用 `--background`；由脚本通过标准加载打开收据指定的候选，绝不打开艺术家文件。

```powershell
$artifactReportSha = 'ROOT_REVIEWED_REAL_ARTIFACT009_SHA256'
$guiReport = "$entry/native_artifact_reopen_gui_report_008.json"
if ($artifactReportSha -cnotmatch '^[0-9a-f]{64}$') { throw 'Root must pin the real successful Artifact009 receipt.' }
if (-not (Test-Path -LiteralPath $artifactReport -PathType Leaf)) { throw 'Real Artifact009 receipt is missing.' }
if ((Get-FileHash -LiteralPath $artifactReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $artifactReportSha) { throw 'Artifact009 receipt SHA differs.' }
if (Test-Path -LiteralPath $guiReport) { throw 'Choose a fresh GUI report path.' }
& $blender --factory-startup -t 1 --python-exit-code 1 --python "$entry/native_artifact_reopen_gui_008.py" -- --artifact-report $artifactReport --artifact-report-sha256 $artifactReportSha --artist $artist --addons "$stage/addons" --source-manifest "$stage/source_manifest.json" --report $guiReport --timeout 180
```

GUI 的验证 timer 异步写报告；PASS 后 GUI 继续存活，调用进程不会立即退出，应读实际 `completed`/错误/逐帧报告，不能等待退出码来推断 PASS。Python callback stderr 被记录，原生进程日志仍需查看。只清理自己的验证 timer，标准插件及其 handlers 保留；不保存文件。报告的 `gui_fps_verified` 始终为 false，完整模型 FPS 必须后续实测并单独记录。
