# 裙子一键设置：参考审计与实施建议

本轮已找到可复用的裙子工作，并完成保存文件的静态审计；尚未新增生产功能、运行内嵌脚本或测试模拟。原始 `.blend` 未修改。两个正在运行的 Blender 窗口有未保存标记，本报告未读取或修改其内存状态；正式绑定前须检查最新场景。

截图对应 Elaina 目录。以下只分析 Ex1 中的 `Armature_Elaina`，不把 `.001` 备份计算进去。证据：[Ex1 清单](Ex1_inventory.json)、[ProfessionalEx 清单](ProfessionalEx_inventory.json)、[X 清单](X_inventory.json)。

Ex1 已有完整的分层机制：可见裙子 `Elaina_Skirt.002` 有 1,920 点、1,792 面，只通过 Armature 变形；33 个组对应 Hips 和 32 根裙子 FK 骨骼。八个方向为 A–D × 左右，每链四节。裙子相关共 136 根骨骼：FK、Physics、SPIK 各 32 根，曲线控制 24 根，Parent、Track 各八根。

真正运行 Cloth 的是八个 `DressTar.*` 代理，每个仅 30 点、24 面。代理通过 Armature 约束跟随对应 `Dress*_Parent_*`，权重为 1；`Clothes_Pin` 固定组覆盖全部顶点，权重 0.2–1。Physics 骨骼朝向代理的四个采样组，FK 再叠加 Physics 的 Copy Rotation 和 SPIK 的 Copy Transforms。两层当前影响均为 1，并非互斥切换。

另外，16 点的 `TrackTarget` 由大腿权重驱动，经 Track、Parent 让裙根随腿运动；72 点的 `Elaina_Body_Col` 承担碰撞。八条三点 NURBS 曲线分别由三个 Hook 骨骼控制。原 SPIK 使用 `FIT_CURVE` 拉伸，不能直接套用现有插件的固定骨长默认值。

ProfessionalEx 是另一种方案：保留八组 FK 链，根部直接挂在 Hips；删除上述辅助层，在可见裙子上使用 Armature → Cloth，以 Hips 组固定腰部。实际 Collision 在 `Elaina_Body.002`；名为 `Elaina_Body_Collide` 的对象没有 Collision 修改器。

需要带入新设计的检查项：

- 两文件的 `DressA_FK_R.003` 均关闭 Deform，但对应组仍影响 317 点，最大权重约 0.987；其直接蒙皮贡献被禁用，应核实意图。
- Ex1 的代理缓存均未烘焙且过期，范围 100–120；ProfessionalEx 缓存为 1–250，与场景 100–120 不一致。两方案均关闭自碰撞。静态约束引用有效，不代表运动效果已经通过验证。
- 内嵌脚本存在 `Dress`、`TestArm`、`Armature_Elaina`、100–120、`Run` 等固定名称或区间。应提取机制，不能直接执行或原样移植。

保存的 X 文件很适合作为首版输入：`Dress` 是 **10 层 × 80 点**的完整闭合环带，共 800 点、720 个四边面；参考裙子为 **15 层 × 128 点**。两者都已通过层间邻接检查，详见 [X 拓扑](X_skirt_topology.json) 与 [Elaina 拓扑](Ex1_skirt_topology.json)。X 当前没有裙子权重组或 Armature 修改器，物体缩放约 0.729965，参考物体缩放为 1。骨骼位置须从裙子局部空间转换到目标骨架空间，碰撞距离和代理尺寸也须按实际尺寸计算，不能复制旧坐标。

建议首阶段做 **Clothing → Skirt Setup**：选择裙子和骨架，识别腰口、下摆及环带，生成腰部固定、环周骨链、纵向与环向平滑权重及原生控制。八链四节可作为参考预设，链数不应写死。提供一个生成主按钮；重复执行应识别已有输出，支持撤销，并保留材质、几何和已有非本工具数据。方向或骨盆识别不明确时，明确指出缺少哪项输入。

代码可借用 [hair_bones_rig.py](../../addons/character_designer/hair_bones_rig.py) 的批量预检、权重快照、失败回滚与生成归属机制，以及 [selected_bone_weights.py](../../addons/character_designer/selected_bone_weights.py) 的权重备份。头发的 Head 默认挂点和独立长条拓扑不能照搬；裙子需要专用环带分析与邻链混合。界面入口集中在 [ui_constants.py](../../addons/character_designer/ui_constants.py) 和 [插件入口](../../addons/character_designer/__init__.py)。

下一阶段再选择腿部跟随、轻量代理物理或直接 Cloth。物理需要独立处理固定、碰撞和缓存；参见 [Blender 布料示例](https://docs.blender.org/manual/en/latest/physics/cloth/examples.html) 与 [缓存说明](https://docs.blender.org/manual/en/latest/physics/cloth/settings/cache.html)。一键创建设置不等于所有姿势均无穿插。用户尚未回答优先偏向骨骼控制还是自动摆动，因此本建议仍是待确定的实施范围。
