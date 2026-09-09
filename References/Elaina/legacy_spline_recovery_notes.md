# 旧 Spline IK 脚本恢复说明

这两份粘贴内容保留了你原来的结构：复制 FK 骨链为 SPIK 层，创建首／中／末三个 NURBS 控制点，以三个骨骼 Hook 驱动曲线，再通过 Local / Before Copy Transforms 叠加回 FK。当前 Character Designer 的裙子工具已采用同类结构。

`D:/Blender/Projects/Character/Elaina/ProfessionalEx.blend` 仍然存在，其中保存的 `Archieved_PhisicsBone` 与第二份粘贴内容非常接近。已校验当前文件的 SHA256 与前次读取一致，并提取出保留换行的原文。这能恢复脚本线索，但不能证明它就是你记忆中丢失的另一个文件或最终版本。

原始内容完整保存在 [legacy_attachments](legacy_attachments)：两份粘贴原文以及 `Archieved_PhisicsBone.original.py.txt`。它们未被执行。

修复版见 [legacy_spline_setup_repaired.py](legacy_spline_setup_repaired.py)。这是独立的旧骨链工作流恢复工具；完整裙子的自动拟合、权重、Collider 与烘焙仍使用 **Character Designer → Clothing**。

旧脚本需要修复的具体问题：

- 粘贴内容被压成单行，混入 Markdown 转义和 YouTube 标签链接，无法作为原样 Python 执行。
- `selected_pose_bones[0]` 和 `[-1]` 不保证是链首、链尾；需要按父子关系排序。
- `TestArm`、`Test`、`SPIK_CTRL_SHAPE`、固定后缀及大小写替换，会在真实对象名不同或 Blender 自动重命名时失效。
- Hook 通过切换 Edit Mode 和点选择顺序分配，依赖当前上下文；修复版使用明确的点索引和绑定矩阵。
- 复制骨骼时显式保留首尾、长度和滚转方向，避免新建临时骨骼的初始状态造成方向突变。
- 删除所有对象、删除当前骨骼集合、清除整批约束和示范占位按钮不属于生成控制系统的必要步骤。
- 缺少重复执行识别、输入检查、失败回滚和精确移除，会使分步运行留下半套设置。

这批附件没有 Cloth、Collider 或缓存烘焙部分，因此不能据此判定旧动画中断的具体原因。现版裙子的逐帧烘焙与独立副本验证继续保留，不因参考脚本而替换。

另一个明确的使用细节已修正：三个大圈支持 G／R／S；局部小菱形是单点 Hook 的位置控制，用 G 移动。原地旋转或缩放单个点不会改变曲线位置。已据此改正现版裙子面板的操作提示。

## 使用修复版

1. 在 Blender 的 Pose Mode 或 Edit Mode 中，选中同一条直线骨链的所有骨骼，至少两个。FK 骨骼需要处于局部初始姿态，且没有自身的动画、驱动或约束；骨链父级和其他骨骼可以已有动画；父级非均匀缩放产生剪切时会拒绝生成。
2. 在 Text Editor 中打开 `legacy_spline_setup_repaired.py`，按 Run Script。脚本创建独立的 SPIK 层、三个位置控制骨和一条 NURBS 曲线，保留原始 FK 骨骼及其权重。
3. 回到 Pose Mode，用 G 移动三个控制骨。再次运行时，会选中已有控制骨，不再创建一套。
4. 需要移除时，选中完整原骨链或一个生成的控制骨，在 Python Console 运行以下代码。已有控制动画或检测到外部依赖时，脚本会拒绝移除并说明原因。

```python
import runpy
recovery = runpy.run_path(r"D:\Blender\Projects\Character\X\References\Elaina\legacy_spline_setup_repaired.py")
recovery["remove_selected"]()
```

这是对旧脚本工作流的独立恢复，不用于覆盖已经完成绑定的 X 裙子。弯曲的 Rest 骨链、分叉链、共享或链接的 Armature，以及父骨缩放产生的剪切或反射，不在支持范围内；脚本会在创建前检查。需要处理剪切时，先准备无剪切的骨架副本。对象自身的非均匀缩放已纳入验证。生成的骨骼暂不支持改名后的自动识别；若已改名，会停止并提示，而不会按猜测删除。Armature 对象和曲线对象改名使用持久引用识别。

完整裙子仍使用 **Character Designer → Clothing → Skirt Setup**。本次 0.40.1 只修正控制提示；已有裙子无须重建。

## 已完成验证

Blender 5.2.0 LTS 的六组后台回归测试已通过，退出码 0，输出 `LEGACY_SPLINE_RECOVERY_ALL_TESTS_PASSED`。测试场景独立创建，未操作实时 X 场景。

- 创建时保留原始骨骼姿态、Rest 数据、蒙皮权重、无关约束和父级 Action；测试夹具初始矩阵最大误差约 `1.79e-6`。
- 三点 Hook 能驱动实际蒙皮；重复执行与对象改名后识别正确，重叠选择拒绝后保持原数据。
- 非中性、弯曲、已约束／关键帧／驱动的源骨链会拒绝生成；父级剪切拒绝后也没有残留。
- 在骨骼、曲线、约束三个创建阶段注入失败，均能回滚并恢复选择与模式。
- 精确移除能恢复原骨架；控制器动画、驱动引用和曲线依赖会阻止移除。七类移除依赖检查已通过，包含材质内嵌节点树驱动对生成控制骨的引用。
- 保存后用禁用自动脚本的新 Blender 进程重开，乱序评估 7 帧，与保存前矩阵的差值均小于 `3e-5`。这验证的是本修复版的原生骨骼动画持久性，不是旧文件的 Cloth 烘焙原因。

复查命令：

```powershell
& 'D:\Blender5.2\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python 'D:\Blender\Projects\Character\X\tests\test_legacy_spline_recovery_blender.py'
```

裙子操作提示补丁已打包为 `dist/character_designer-0.40.1.zip` 并安装，插件在 Blender 5.2 中注册／反注册／再次注册通过。打包时 24 个文件与源码及安装文件逐字节一致。
