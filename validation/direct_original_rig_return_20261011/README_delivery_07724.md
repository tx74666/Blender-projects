# 原场景动画回汇交付：2026-10-11

已完成用户授权的原场景/Rig 动画回汇、保存与临时场景清理。实际运行 Blender 5.2.0 LTS、Character Designer 0.77.24；模型和 reasoning effort 未记录。

## 保存结果

- [X.blend](D:/Blender/Projects/Character/X/X.blend) 只保留 `Scene`；`Walk_N` 直接使用原 `CoshaRig`，346 根骨骼。当前为 Custom、Pose 模式、第 18 帧，自动插帧关闭，保存返回 `FINISHED`，dirty=false。
- 最终 SHA256：`e8d3013ef14e02ed76160a838e7d255490fd1b6ece340e7c3f9e33dc57a3377f`。
- 保留原骨色、5 个分组及其属性、全部 50 个控制器 widget 资产、6 个绑定网格、18 个材质、权重、作者 Shape Keys、原 Armature Rest 与 Forearm 校准。预览中的 Body 自动成员和 8 个已认证 FK widget 绑定按现有控制模式显示；这些 widget 资产仍完整保留。`Restore Main Rig` 原生验证能精确恢复原模式、动作/slot、NLA、姿态、帧和完整原资产状态。
- 删除 `Animation Worklist · Cosha` 及它独占的 `CoshaRig.001`、`Clothes.001`、`Cosha.001`、`Dress.001`、`Hair.001`、`Stocking.001`，以及 `Unity Source - CoshaRig` 集合。旧 Source/Custom 动作与恢复索引保留；清理前独占用户检查通过。

## 使用与恢复

动画 Worklist 已在原场景上连接。Source 是只读库动作，Custom 是本地可编辑副本。需要回到回汇前的作者状态时使用 **Restore Main Rig**；保留的 Custom 可以在 **Use Main Rig** 后再次接回，不需要重建场景。

备份均经原生保存和 SHA256 验证：[初始备份](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_before_direct_return.blend)、[应用前最新备份](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_before_apply_final.blend)、[删除临时场景前备份](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_before_cleanup.blend)、[旧 Source 备份](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/previous_source_Walk_N.blend)。最后一次保存的只读重开验证副本为 [artist_final_validation.blend](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_final_validation.blend)。

## 验证与部署

- 批准投影 159 文件、14 个所属 Python overlay，保留 0.77.23 包的既有修复。安装目录和 X/addons 已部署，`--check` 两处差异 0；现场 .23→.24 刷新保留 Scene、WindowManager、上下文、姿态和资产。
- 216 个纯测试通过。全原生隔离回归五轮各 59 个采样 ×184 个 Body/Hair 骨骼通过；Source/Custom、保存重开、两次恢复、保留 Custom 后再接回、外来引用拒绝均通过。最大矩阵分量误差 `7.338821887969971e-6`，最大骨头位置误差 `0.0015975545965657353 mm`。原始包和测试输入哈希未变。
- 现场原 Rig 全 59 采样通过并保存；最终保存副本重开验证持久会话、动作/slot、只读 Source、原资产哈希以及采样 0/29/58，通过且 artist/copy 文件哈希均未变。
- 隔离回归单次总 wall `586.1882262 s`、进程 CPU `544.59375 s`；单线程、包含完整保护检查及多轮保存重开，内存与其他项目负载变化。这是功能验证耗时，没有配对性能/FPS 收益结论。

证据：[全原生回归](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/isolated_report.json)、[Dress 拒绝检查](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/dress_guard_report.json)、[纯测试](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/pure_test_receipt.json)、[部署](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/release_deployment_receipt.json)、[现场刷新](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_refresh_receipt.json)、[回汇保存](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_direct_return_receipt.json)、[清理保存](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_cleanup_receipt.json)、[最终重开](D:/Blender/Projects/Character/X/validation/direct_original_rig_return_20261011/artist_final_reopen_report.json)、[源码/限制](D:/MyRepository/Blender-addons-by-Randy/docs/releases/CharacterDesigner_0.77.24_original_rig_return_20261011.md)。

## 范围与下一次入口

33 个 Dress 骨骼已验证包内为 Rest 静态，继续使用原手工 Dress 求值图；移动 Dress、恒定但非 Rest 的偏移、含物理录制的包会拒绝。原数据没有被断开骨连接，126 个具有平移的已验证 Body/Hair 骨只在本会话拥有的运动 Armature 副本上改变 connected 标志；完整恢复、跨重开和再接回已验证。

本次使用明确的历史 workspace/model 身份与当前真实 Rig 的严格 Rest 校验；当前 Unity 模型文件后来更新，后续 Sync 必须重新验证匹配的新模型身份。这次没有 Unity 写入、模型修复、Git Commit/Push。组合动画另用明确的新记录与身份。后续只对新 Rest/尺寸变化、动画 Dress、控制图变化、恢复/再接回异常或新组合/Sync 流程调查；不要重复已通过的整轮分析。
