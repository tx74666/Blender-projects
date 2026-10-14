# Fresh Rigging 物理回汇 recipe（Source only，2026-10-12）

本文件只读当前真实 Source，列下一段正常 Sync/worker/Collect/Apply 的调用及实际证据。没有运行本文件内的任何 API，没有 Blender/Unity/SDK/worker/部署操作，没有生成 Link、WorkID、workspace 或授权。前一份 `worklist_native_recipe.md` 保留原 bytes；`native_round.py` 仍由 Rig owner 独占，本文件不编辑它。

## 1. 与 direct native 实验的边界

Direct 实验可以证明：真实 base native clock、两臂 Target/Hint 显式 key、carrier 20 个 curve/component、严格 Return DTO、Source carrier 只读、Custom draft 回滚/保存/reopen 的原生身份与本地输入。`capture_inputs()` 返回的是 control-only JSON，不是物理 FBX、Unity candidate 或 Apply 结果。它不能继承任何旧 12-case/217、410×298、3 publication、u7/948e 或旧 grant 成为本轮证明。

当前 `animation_rigging_contract.py:35` 的 Return **严格 14 个顶层字段**：schema、sourcePacketSha256、bindingsSha256、targetGuid、workItemId、newActionId、sourceAction、sourceActionSlot、targetInputAction、targetInputActionSlot、duration、sampleRate、loopTime、frames。每帧固定 Right、Left 顺序，controls 只有 targetPosition(3)、targetRotation(4)、hintPosition(3)，共 20 components。武器 display 的 10-field optional preview 和 preview parent matrices 均不是 Return channels。

当前实际 QA packet 没有 WorkID，目录 UUID/newActionId 不能代作工作项。当前 round 若仅获得 direct packet，没有本节 2 的真实 Prepared typed Link/model/workspace，就停留在 direct DTO 范围，不能伪造工作项启动物理回汇。

## 2. 前置输入与一次新的物理授权

必须由 Parent 提供本轮真实 Prepare 后、SHA 封存的 packet-adjacent `character_animation_link.json`、**该 Link 的 real WorkItemId**、model FBX+SHA、真实 workspace/route、approved complete runtime package，以及 disposable QA scene/rig。Link 必须是 `randomrealm.animation-link/1`；通过 `links.load_link()`（`animation_link.py:129`）检查 1 MiB small manifest、source packet 同目录与当前 full SHA，再通过 worklist 的 route/model/slot 身份检查，不能只比较 display name。

此 Rigging 路由是独立 full base-motion / editScope All，不能送进 legacy composition B / readonly A Source / NewAction 的其他出口。sourceOnly、compositionReferenceSource、needsRebuild、sealed DTO、clip GUID/LocalID、target GUID、prepare request、model SHA 都保持原守卫。`animation_worklist.add(context, clip_key, activate_new=False)`（worklist:365）和 `activate(context, item_id, 'CUSTOM')`（:584）只能在已经 connect/adopt 到真实 workspace 的新 QA scene 调用。不能在本段偷偷创建本地 catalog 或覆盖共享 workspace。

普通 Worklist 导入的顺序仍是 base import（仅 packet.rigging 时 native_timebase=True）→真实 Custom Action/OBJECT slot→native.import_inputs(real WorkID)。import 不把手的 solved pose 写入 base；Source/custom carrier 各自保持来源与 draft。移入物理段时应使用这个官方 Worklist row，而不是往 direct 实验的 Action 手工补 Link 指针、Row UUID 或 receipt。

Parent 必须另行授予 **本轮实际 Sync/worker 与 Unity Collect/Apply** 所需权限；旧授权不延续。资源按约 200 MiB / near 98% 重读与串行规则由本轮 host/Parent 实测，等待 Unity 编译/导入与其他重型阶段让位。本文件不读取资源，也不启动或终止任何进程。

## 3. 正常 Worklist Sync 的唯一一次 launch/proof

在 owned QA context、真实 row.side == CUSTOM、source/model/current Link 全认证后，调用现有 `job = worklist.sync(context)`（worklist:714），不要改用 direct animation_export 规避 row admission。已有 UI timer 是完成/dispose/receipt 的所有者；正常 UI 路径保持它运行。

该函数的实际链：

1. :727 的 `rigging.base_only(context, item.rig, action=item.custom_action)` 覆盖 target ensure、active Action、current workspace/Link route、fingerprint、association、export launch；普通无 Rigging 路径不导入新 native module。
2. :744 冻结 `collector.item_fingerprint(context, item)`；:745 冻结 `export_implementation()`，保留 fingerprint Unknown 语义及 `unchanged_proof()` 防重复。Collection 模式有自己的 exact queue token/proof callback，不伪造 `_collection=True`。
3. `links.begin_linked_export(context,rig)`（link:320）读取 current persistent native session，拒 Source carrier，要求 base Action/slot、real WorkID 与 saved Link 完全一致；:341 通过 `native.capture_inputs()` 冻结已保存 carrier keys 的 Return14。不是采样当前 composed deform 或未保存的 live Target pose。
4. :345 再进入 nest-safe base_only，再走 `_begin_linked_export()`，完整 sourcePacketSHA/modelSHA/active OBJECT slot/Link identity 检查。唯一新输出在 `packet-folder/blender_revisions/<actualLinkUUID>/action-<newUUID>.fbx`，不替换旧 pair。
5. exporter `begin_export()`（export:65）验证 Return 的两 Action/slot、clock、duration、loop；:89 再隔离 base。`_begin_export()` 的 snapshot 使用 `native.snapshot_base_refs()`（:182）临时遮蔽 owned input/session forward references，finally 恢复。基础 worker 只能持有 base snapshot，不烘两臂 IK 输出回基础 clip。
6. :191 启动 **正常 animation_export_worker.py**（factory/background/disable-autoexec、python-exit-code1、threads2）并持有 job/process/log。生成 job 是实际 worker launch；没有 fresh grant 不能执行。
7. worklist :753–755 在同一事件 turn 附加真实 Scene/item id、frozen comparison proof 与 implementation。不得根据重建的 current fingerprint 冒充旧 launch proof。

如果隔离 harness 必须同步等待，先明确接管此**单一实际 job**的冗余 timer（现有 composition_sync_acceptance.run_one:235 展示 exact-only unregister pattern），通过 `animation_export.poll_export(job)` 驱动已启动 job，再恰好调用一次 `collector.export_finished(job,result=published)`。不能同时让 UI timer 与 harness poll，同一 job 不能双 finalize。正常 timer 实现在 `animation.py:184`，它已自动调用 Collect completion。此处仅是调用 recipe，不创建新 runner/framework。

## 4. 必须留档的物理证据，不能仅 result.ok

Worker `export_job()`（worker:246）先验证真实 snapshot reverse dependency guard，再验证 local Rig/Rest、精确 selected slot、unsupported channels、source/native fps；:367–387 仅 selected Action/slot、NLA disabled、两个臂 FK/base-only 的 snapshot 状态上采样。:491 实际 FBX export FINISHED、完整非空文件；result.json 的 bones 是实际 name **list**，不是整数；:508–520 保存 action_slot、duration、source fps、sample/effective rate、samples、骨架 list、maximum_bake_matrix_error、source_curve_count、unsupported/warnings 与实际 FBX SHA。

`animation_export._publish()`（:217）原子写 **真实 FBX + adjacent .animation.json**，FBX 最后可见，不覆盖已存在文件；host sidecar 加入 action/actionSlot、source_package/source_package_sha256、fbx_sha256 与冻结 Return14 (`rigging`)。注意 worker `action_slot` 与 host published `actionSlot` 是不同实际字段，都要分别核，不猜 alias。Link `_revision_result()`（:271）认证 output directory、model 当前 SHA、FBX/sidecar SHA、source packet path/SHA，然后锁内推进 revision；revision 的变化只说明 publication，不自动说明 Collect receipt 成功。

本轮 report 至少封存：本轮 prepared Link before/after bytes+SHA+revision、worker job.json/animation.blend/log/result.json 的实际路径/SHA、process natural exit、new FBX/sidecar 的 bytes+SHA、新 Link outputs、冻结 Return14、base/input exact selected native slot、source packet/model SHA、原 base keys hash、输入 draft keys hash、原 artist/Scene/Rest/原 Actions/slots guards、preview finally-restoration。worker archive 在 temporary dispose 前保存（旧 helper `composition_sync_acceptance.archive_worker():175` 是可复用的实际文件归档行为；该 helper 的 run_one numeric oracle 属旧 Composition 专用，**不能拿来验证 Rigging row**）。

Collect `export_finished()`（collection:744）必须返回空 error string，且 item.last_synced_receipt 中是真实当前 publication。若返回非空，保留 `collection_receipt_error` 原文，不能仅 publication 成功就报告完整 Sync PASS。现有 composition_sync_acceptance.run_one:246–248 已落实这一 error 原文示例。

`collection._published_rigging():426` / `_receipt():450` 是当前严格回读：sidecar≤32 MiB（small Link 仍≤1 MiB）、metadata SHA、action/actionSlot、original capture/newDraft/WorkID/bindings/sourcePacketSHA、targetInputAction/inputSlot、exact clock 与所有有限 local channels。`contract.validate_export()`（:393）必须使用 actual frozen capture 与全部 caller identities；不能用只是同 shape 的 DTO。拒 unsupported mandatory/control channel、partial outputs、tamper 与不匹配 slot，不补 bake/fallback/新 tolerances。

## 5. Target-only dirty 的实测口径

先从 **同一真实 prepared Source baseline 或成功 last_synced_receipt** 取得旧 proof，再对唯一 allowed Target/Hint 做实际 native编辑 + `key_current()`。证明：base selected-slot `_motion`/curve full hash unchanged，source carrier unchanged；Custom input_motion_sha256 changed；base_action/base_slot、input_action/input_slot、capture SHA、initial input motion、WorkID/newDraft/fullPacketSHA 均 unchanged。`collector.item_fingerprint()`（:142）通过 `_with_rigging():129` 把 fixed rigging proof纳入原 fingerprint，不放宽普通 FK/dependency admission。

`scan_changes(context)`（collection:486）真实比较 `_same_proof()` 与现有 receipt；:532–538 将 Target proof change 标记 effective_inputs_changed/export_needed。若原 native base dependency proof因 preview NLA/其他真实状态是 Unknown，**保持 Unknown**、不制造 known/CHANGED；仅 explicit artist selection可 Sync。`base_only` 中取得的 frozen launch proof与普通 preview 图的 scan proof须按各自状态报告，不混成一个 pass。成功 Sync 后原输入、clock、implementation、physical hash全未变时 unchanged 防重复必须实际成立；不能只改 `sync_selected`或 UI label 充当 dirty oracle。

## 6. Unity Collect → base Preview/Apply 与 Target独立Apply

本节是 Parent-owned Unity Source入口指引，当前没有调用、编译或资产写入。真正 Collect 是 `D:/Unity Projects/RandomRealm2/Assets/Scripts/Editor/CharacterTuningAnimationLink.cs:1059` 的 `Sync(actual editingLink)`，不是 Blender Sync 同名事件。它核新manifest/revision/FBX/sidecar/source/model，再 :1083 调 `CharacterAnimationReturn.Import(fbx,targetPrefab,...,editScope:'All',composition:null,sourcePacketPath:actualPacket,expectedWorkItemId:actualWorkID,expectedSourcePacketSha256:actualSHA)`。

canonical embedded `CharacterAnimationReturn.cs:68` 入口在 :132–157 完整sourceSHA+rigging Return认证；:235–239 **拒基础FBX含Target/Hint channels**；:343 保存独立基础 Humanoid clip，:351–371 再保存独立 `.targets.anim` / GUID / LocalID / SHA。`CharacterAnimationRigging.CreateTransientCandidate():346` 只构建两Target local position/quaternion +两Hint local position20曲线。Collect Link :1106–1110 将这个独立 Target identity 纳入 exact RevisionInfo。全部sourceclip/controller/prefab是否变化仍由相应 Source guards核验；不能把旧 Base/Target provenance 丢进同一基础clip。

基础 candidate可经 current Worklist Preview+`CharacterTuningAnimationLink.ApplyRevision():647`（真实 target/Use-as/WorkID/revision）走已有 base用途，随后 `CharacterTuningAnimationWorklist.Complete():313` 仅接受实际 Applied result/同Undo group。它不表示手Target已Apply。

独立手输入入口是 `D:/Unity Projects/RandomRealm2/Assets/Scripts/Editor/CharacterTuningRiggingSource.cs:232` 的 `ApplyControls(target,actualRigPath,returnedControls,actualPacketPath,actualRevision)`：ResolveReturnedControls(:165)认证candidateSHA；:238–253 exacteditingLink/revision/packetSHA、真实parents/bindings；:257要求恰好20 effective channels与base same duration；:261要求已经配置的own control slot；:274–283仅新owned override、publish当前真实control use、原binding与source stamps不变，失败Rollback。它不默认改Prefab直接Transform值、runtime任意来源或基础clip；真实source/use由Parent显式路由。

**本次只读检索的 live Assets Source 尚未找到 ApplyControls 的 UI/Batch调用方（除定义内部认证），这是部署现况，不能据此说新 candidate 未实现。** Parent 随后明确提供 owner-reported candidate 事实：尚未部署到 live Assets 的 `AdventureCharacterWeaponTuningWindow.Rigging.cs` 已有 `Apply Viewed Controls` → `QueueAnimationLinkOperation` → `CharacterTuningRiggingSource.ApplyControls`。本 recipe 未读取/调用该 hidden candidate，也没有 candidate SHA或 native验收，故将其标为 Parent-owned/pre-native pending；下一UI部署需由 Parent 实测此独立入口，再分别封存base binding与Target binding、实际Undo/Repeat、dirty/Sourcehash保护与consumer效果。无 fresh Parent Unity授权时不能用这份recipe执行这一步。

Parent 报告下一Unity Prepare将提供首轮 actual Cosha + `Weapon_Blaster.prefab` 的真实 weapon preview输入；当前 direct packet.weaponPreview缺省。未来 source/display输入、显示几何认证与角色 runtime已装备是不同证明，不能把下一Prepare或武器prefab本身当成 Cosha当前已装备通过；Soldier mapping保留后续实际范围。

## 7. 交付与限制

未来要分开报告：direct native/control save结果；本轮真实Sync/worker+物理 pair/Collect receipt结果；Unity真实Collect两个候选；base Apply；Target Apply。只有最后对应阶段的真实文件/slot/输入/localchannels/consumer与Undo证据满足后才能说阶段完成。所有输出使用 fresh owned路径，旧工作项、共享workspace、old publication/artist/failed attempt与历史grant不动。本文件不提供/续用启动授权。

## 本次只读 Source pins

- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist.py` — SHA256 `bcddead36b21313b9a7991c6c1da784b582a29380cc8ed0c184b941b7e284c53`, 40384 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_link_source.py` — SHA256 `bbf0b65c8095df31f92ba378284f98a4d0be7d80835d6b2362cfe4402ded3b2d`, 13485 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_export.py` — SHA256 `659c6e8e6ddfd5f0e5179e8a3dcaf77c7714369daa1d432a99bd9bf22f32e9be`, 15476 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_export_worker.py` — SHA256 `87a4f850fd31583a55e7f610a46b6d3d35696d7f604986a0db371d3a088fe266`, 28660 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_link.py` — SHA256 `364307151184fc9a3b934f03cc4269609365491a7fabeb06c36ccd87e6455aaa`, 21500 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_collection.py` — SHA256 `8f3119ebdc89c0b783ce7fab58a4586b19d4f59d915e299ba521a071fae86c8c`, 45560 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation.py` — SHA256 `21bc2bdd62ab6cba661c31a0006319e487047385fcb7a3381f3943bf6be2b05a`, 37862 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_rigging_contract.py` — SHA256 `bff52cbe97530662fcee5e4ca248c1fe09e781f73588627cecda62c777d3c179`, 23545 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py` — SHA256 `b459668d166ef0b20b488414f3ae115aa53dd4bbeaec0645aea4ebba2e64d04d`, 78327 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/tools/composition_sync_acceptance.py` — SHA256 `db4d61e9deaa6833137507b49957178bc833bd5b83512fff1f809181ad49ab96`, 21223 bytes.
- `D:/Unity Projects/RandomRealm2/Assets/Scripts/Editor/CharacterTuningAnimationLink.cs` — SHA256 `437df1ff58e6e9a5aaa33b80f795b750628f10caa4e0a1e5de10aa1eecc8685e`, 232245 bytes.
- `D:/Unity Projects/RandomRealm2/Assets/Scripts/Editor/CharacterTuningRiggingSource.cs` — SHA256 `f7fa7c9537d116569c6ac9a69468e6bb5cf57c8de9fb93a08b2902881838bb90`, 46990 bytes.
- `D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_runtime/Editor/CharacterAnimationReturn.cs` — SHA256 `b065b5dbde90d04e74ea393e3c56ec26f2487c4514111860d17055c968755dcd`, 58824 bytes.
