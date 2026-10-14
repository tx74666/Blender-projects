# 2026-10-11 闲置后台内存检查

用户范围：只检查未使用、残留或无效的后台开销；保留正在绘图、对话、实验及验证的任务。

结论：本次没有找到归属和空闲状态均已确认、可以安全清理的进程。未终止进程、修改应用配置或改变 Blender 场景。系统压力与活跃任务并存；单次高占用不构成泄漏证明。

## 可比轻量采样

两次采样间隔 49.7 秒，所有后台工作继续运行。单位 MB 实为 MiB。工作集是当前驻留内存（可含共享页），PrivateMemorySize64 是私有提交量，包含可能被换出的内存，两者不能混作物理 RAM。

| 项目 | 20:00:59 | 20:01:49 | 说明 |
| --- | ---: | ---: | --- |
| 总可用物理内存 MiB | 295.20 | 538.95 | 容量 16158.8 MiB；系统占用 98.17% → 96.66% |
| Unity MCP 工作集 MiB | 145.98 | 145.98 | 17 条完整 stdio 链、85 个进程；私有提交 3397.02 MiB |
| CUA server 工作集 MiB | 176.59 | 176.59 | 42 个 server.mjs；私有提交 2072.27 MiB |
| CUA REPL 工作集 MiB | 97.27 | 97.27 | 17 个 REPL；私有提交 348.84 MiB |
| 活跃后台 Blender 工作集 MiB | 2189.16 | 3853.82 | PID 67856，另一聊天的 composition n16 recovery；私有提交 4974.10 MiB |
| Artist Blender 工作集 MiB | 120.12 | 89.46 | PID 27676；私有提交 4653.82 MiB，低驻留不等于已释放 |
| Codex app-server 工作集 MiB | 548.60 | 485.93 | PID 75624；私有提交约 2048.8 MiB |

49.7 秒内，42 个 CUA server 和 17 个 REPL 的 CPU 增量均为 0；85 个 Unity MCP 进程合计 CPU 增量 0.218 秒。所有候选 Codex/Node/Python/uv 辅助进程均有有效、时间关系正确的父进程。闲置连接仍可能服务现存聊天，CPU 为零不能证明没有用途。旧进程登记文件停留在 8 月 5 日且 PID 为空，不能作为当前清理依据；近期退出日志未提供残留清理失败证据。

## Blender 检查

Blender 5.2.0 LTS，现场 Character Designer 0.77.24、RR Helper 0.2.60；X.blend、Scene、Pose、帧 18、dirty=false。只查询元数据，无 mesh evaluation、frame_set、导出、渲染或场景写入。

- 当前 Character Designer Forearm 输入/输出缓存各 1 项、帧缓存 1 项；Hair selection cache 0 项，其余检查到的 UI 缓存为空。
- 未发现当前重复注册的 Character Designer handler，也未发现常驻空跑的导出 worker。导出 worker 按操作启动，完成/超时/载入/注销均有释放路径。
- 静态审计发现 Hair selection cache 缺少数量上限及 clear_cache 调用；Forearm 非官方删除对象的路径可能保留旧键。现场未证明存在这类死记录，Hair 缓存为空，未把潜在问题当作当前 GB 级占用来源，也未修改另一聊天正在开发的源码。
- Undo 为 256 步、memory limit 0；属于有用的作者工作历史。本次按用户收窄范围保留，不改偏好、不清 Undo、不清理作者资产。

## 证据与限制

- `process_before.json`、`process_after.json`：完整进程关系及内存采样，未记录原始命令行和环境变量。
- `helper_activity.json`：两次采样的候选连接服务 CPU 增量。
- `live_before.json`、`idle_inventory.json`：现场元数据和缓存/handler 清单。
- `snapshot.ps1`、`inspect_live.py`、`inspect_idle.py`、`run_bridge.py`：本次轻量检查脚本。

模型及 reasoning effort 未经运行元数据核实，记为未记录。多任务共享负载，采样仅覆盖约 50 秒，不是泄漏排除、长期增长或 FPS 测试。没有新增重型任务；没有插件补丁、部署或 Refresh；没有场景操作，artist 原本已保存且本次未重写。无可声称的优化收益；读数变化来自运行中的共享负载及换页。

下一次触发：任务结束后某个 worker 仍存活；明确已关闭聊天仍保留对应连接；或同一任务/同一场景在空闲时持续增长。届时先取得具体所属聊天、客户端断开与进程空闲证据，再关闭或修复其持久生命周期。
