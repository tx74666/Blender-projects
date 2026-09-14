# Character Designer 0.57.1 — Unity 导出验收

2026-09-13，本地安装并刷新完成；未提交或推送 GitHub。

## 使用

Misc / Miscellaneous → Unity Export → Export / Update to Unity。

已在 X.blend 的 CoshaRig 中保存目标：
`D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha`

这是为当前 Unity 项目选择的默认目录，可自行修改。此次实际按钮验证导出到 `outputs/unity_export/LiveTest`，没有写入 Unity 项目目录。

导出静止模型 FBX、原生变形骨架、艺术 Shape Keys、贴图和清单。目录及额外物体按角色保存。后续更新保留 Unity .meta；拒绝覆盖无法确认归属或被外部修改的文件，已有导出更新前会另存备份。

## 已运行的检查

- 导出协调器 4 组：范围筛选、真实后台导出及回读、重复更新、取消、失败回滚、文件归属和 .meta 保护通过。
- Worker 7 组：修改器与 Shape Keys 对应、权重保持、附加骨架、单位、贴图及无权重诊断通过。
- UI、注册和配置保存测试通过；0.57.1 的测试使用 Blender Event 实际支持的字段，避免伪造 timer 属性。
- 当前 X 窗口实际点击导出成功。此前发现的 Event.timer 错误已修复并再次点击验证。
- 实际角色 FBX 回读：7 个网格、56 根原生骨骼、7 个艺术 Shape Keys、19 个材质、11 个贴图；控制器和辅助骨未混入。
- 回读后移动 Hips、左右手以及眼睛 Shape Key，实际网格能变形，恢复误差低于 2e-6。尺寸约 1.040 × 0.451 × 1.705 米。
- X.blend 保存并重新读取后，导出目录和 Hair / Dress / Jacket 额外物体配置仍在；原网格、权重、Shape Key 数据、骨架及姿势比较摘要一致。
- 源码、Blender 安装目录和 X 验证副本的 57 个文件全部一致；git diff --check 通过；RR Helper 未修改。

## 当前角色的实际限制

- Hair、Dress、Jacket 尚未绑定，导出后仍是未绑定网格。
- Shoes 的 Armature 修改器当前停用；导出遵守此状态，鞋子不会随该骨架变形。
- Cosha 原本有 2 个顶点未分配变形骨权重，工具只报告，不擅自修改。
- Blender 小臂校准工具的运行时额外校正不随本版导出；Unity 不会运行 Blender handler。
- Blue 和 Stocking Main 使用自定义 Shader，需要在 Unity 配置对应材质。
- Unity 实际导入、Humanoid Avatar、渲染、动画往返和运行时物理未验证。本版只导出静止角色，不包含动画导出。

## 证据与恢复

- 实际按钮结果：`LiveTest/Cosha.cdesigner.json`
- FBX 回读：`x_fbx_reimport.json`
- 原有无权重顶点：`x_source_unweighted.json`
- 保存及源数据比较：`saved_profile_check.json`
- 场景备份：`X_before_unity_export_0570.blend`

源数据保存前后摘要均为：
`918a9285ecc8e54076bbe1d62c87b8e917161444b761dc22d6e59750b9e89ba7`
