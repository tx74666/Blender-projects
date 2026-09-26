# X Blender 内存检查 — 2026-09-26

结论：本次实测中，双视口的 Material Preview 是明显的内存开销来源。没有发现当前 Character Designer 主要 Python 缓存异常膨胀的证据。本次没有修改插件源代码。

## 同一 X 进程的视图对照

| 状态 | Private Commit，十进制 GB | 工作集，十进制 GB |
|---|---:|---:|
| 两个 Material Preview 视口，测试开始 | 5.244 | 0.917 |
| 两个 Solid 视口，5 秒后 | 2.233 | 0.927 |
| 恢复两个 Material Preview，5 秒后 | 5.352 | 0.956 |
| 最终：主视口 Material，左下辅助视口 Solid | 3.809 | 0.947 |

见 `viewport_probe.json`、`after_secondary_view.json`。辅助视口改为 Solid 后，相对于刚恢复双预览的样本，已提交内存减少约 1.54 GB。主视口材质效果、模型、骨架、动作、Shape Keys、渲染设置均保留。工作集会受 Windows 页面调度影响，不能把 Private Commit 下降直接描述为等量物理 RAM 释放。

检查最初的 OS 样本：X PID 2420 PrivateMemorySize64 为 5,132,349,440 bytes，Builder6 PID 16776 为 4,036,743,168 bytes。因此截图的约 1.24 GB 对 204 MB 并不能证明 X 的总私人内存配置量是 Builder6 的六倍。最终 X 的已提交内存也低于检查开始时约 1.32 GB。

## 图像与场景检查

- 基础网格总计 109,212 顶点；Shape Key 坐标估算 847,680 bytes，不包含其他对象结构和求值结果。
- 29 个 Image datablock；未发现巨型 8K/16K 纹理。24 个材质。
- Character Designer 的 forearm、hair selection 等主要快照缓存为空；RR Helper 的 PREVIEW_COLLECTIONS 为空。这不是对所有原生 Blender 分配的完整归因，也不能证明未来绝无内存泄漏。
- 三个仅通过 Fake User 保留、未分配物体的皮革材质，共 9 张干净的 packed 2K 图片，已执行一次 buffers_free。全部 Image、材质引用和 packed bytes 保留。随后再次检测这些缓存仍未加载。
- 图像释放前后 Private Commit 从 5,394,657,280 降至 5,244,370,944 bytes，约 143.3 MiB。

**测量扰动说明：** 初版检查脚本读取 image.size、channels 等属性，会触发 Blender 懒加载；检查过程中 Private Commit 增加约 262 MB。因此上面的图像缓存释放量不能全记作对原问题的改善。探针已修正为先检查 has_data，仅对已加载图片读取像素相关元数据。主要优化结论基于之后的视口对照实验。

## 当前留下的改动

- 当前 Modeling 工作区左下小视口设为 Solid，主视口保持 Material Preview。
- 已恢复右下 Asset Library 面板。
- 未覆盖保存 X.blend；视口配置随用户下次正常保存文件保留。恢复方法：左下视口使用 Z → Material Preview。
- 未清空撤销历史。撤销仍为 256 步、内存上限 0（不限额）。已向用户提出 1 GB 上限选项，尚未应用。此设置影响可保留的撤销历史长度，不是 Blender 总内存限制。
- 材质、图片、网格、骨架和动作 datablock 数量在缓存释放前后保持一致。

## 参考

- [Microsoft 工作集定义](https://learn.microsoft.com/en-us/windows/win32/procthread/process-working-set)
- [Microsoft PrivateUsage 定义](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)
- [Blender 5.2 图像 RNA 属性](https://github.com/blender/blender/blob/v5.2.0/source/blender/makesrna/intern/rna_image.cc#L474)
- [Blender 5.2 图像缓存与打包数据](https://github.com/blender/blender/blob/v5.2.0/source/blender/blenkernel/intern/image.cc#L661)
