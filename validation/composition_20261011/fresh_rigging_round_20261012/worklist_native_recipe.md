# Fresh Rigging round：worklist / Link Source recipe

此文件只整理已存在 API；未执行 native、Blender、SDK、Sync、worker、Apply 或场景保存。`native_round.py` 由 Rig owner 独占，Root 管理实际 source package/content pins 与 START。

## 当前实际输入与阻断

Cosha Walk_N packet：
`D:/Unity Projects/RandomRealm2/Logs/CharacterTuning/TwoArmComposition/923c041bf09342249800cd4454c884d5/Cosha.Player/Walk_N/rigging/Cosha_Walk_N.cdanim.json`

只读 JSON：2,338,484 bytes；targetGuid `3207a6768cff4594fb4b180b85f70a37`；218 packet bones、59 frames、duration `0.9666667`、sampleRate `60.0`、loopTime `true`；Rigging previewEnabled `true`；weaponPreview absent，不能声称枪显示已验证。

**packet 顶层和 rigging 都没有 workItemId。** Native `import_inputs` 内 `_uid` 要求非空 UUID，Return 同时要求 WorkID 与 newActionId 不同。Root 必须明确传入独立 QA caller identity 或真实已有 Link 的 WorkID。不得把 QA 目录 `923c…` 或 input newActionId `bdd8d9f6604f4c539c5f3143d0e10642` 猜成 WorkID；独立 QA WorkID 也不能冒称 Unity 已准备的 worklist route。

当前 round 的 Rig owner已明确：直接导入 base+输入，Return 仅本地控制 DTO JSON；不 Sync、不开 worker、不 publish，不造不存在的 Link/workspace。WalkRight、Soldier 仅使用 Parent 明确提供的各自 packet/context/pins；不要沿用上述 Cosha identities。

## 当前 round：最小直接入口

以下调用属于未来获 START 后的 native 脚本，本次未执行。

1. `ua.load_package(packet_path)`（unity_animation.py:55）得到 `_path`、完整原始 `_sha256`；再 `rigging_contract.validate_capture(packet['rigging'], packet=packet)`。Root提供的 packet SHA 必须在前后都相同，不能改 packet 增加 WorkID 或复用旧 scope。
2. Rig 必须由明确 identity/expected name 在 isolated clone 原 Scene、ViewLayer 中唯一解析；local Object/Armature，不能猜第一个 Armature。`ua._mapping(rig, packet, context.scene.unit_settings.scale_length)`（:173）严格验证现有骨名、parent、Rest、实际 Unity↔native 尺度及安装的原 rig controls；不加 Cosha/Soldier chain。
3. 如果 `body_original_mode.active(rig)`，UA importer会拒绝（unity_animation.py:515）。仅可由脚本 owner在 disposable QA 内显式采用现有 Original transaction，保存并恢复其全部原状态；不要绕过 importer/validate_target。无真实 workspace 时不要调用 Worklist Adopt 来假造主 Rig 记录。
4. 使用 `source._import_action(context, rig, packet, 1, native_timebase=True)`（animation_link_source.py:35）或同等的 `ua._import_package_action(..., start_frame=1, native_timebase=True)`（unity_animation.py:494）。只有真实 Rigging route 选 native clock；不要用普通 `import_test_action` 默认 Scene clock。失败恢复由现有 UA transaction负责。
5. 导入结果是 `PreviewResult.action`。先 `target.restore_import_preview(context, rig, result.action)`（animation_worklist_target.py:715），恢复 UA 临时 preview/Original Rest；必要 translation copy仅由真实 adoption路径认证保留。不要把仍有 ACTIVE_KEY 的 UA preview当 Rigging base。若本次UA import确实创建必要translation copy，direct路径恢复原data后不能自动宣称base evaluation等价；须报告这个真实边界，由owner选择已有且认证完整的Main Rig adoption路径或停在失败，不绕过connected/Rest validator。
6. 只对该次新建 QA Action调用 `worklist._clean_action(action)`（animation_worklist.py:157），去掉 UA临时恢复 refs、保留 native timebase marker；不要清理旧 artist/Source Action。绑定 `ad.action=action; ad.action_slot=worklist._slot(action)`（:173），保持 exact OBJECT slot，随后调用：
   `session = rigging.import_inputs(context, rig, packet, base_action=action, base_slot=slot.handle, work_item_id=explicit_work_id, source=False)`（unity_animation_rigging.py:387）。
   inputAction必须不同于 baseAction，独立 native slot；import按 packet.previewEnabled显示，不改 Prefab RigWeight。
7. `rigging.activate(context, session, edit_role='BASE'|'RIGGING', enabled=False|True)`（:881）。`enabled` 是明确 native Tweak 编辑标志；实际 preview enabled来自capture，不要把两者混淆。BASE限制covered arms；RIGGING只原Target/Pole输入。不写FK base来模拟Target，不替换solver target或Parent。
8. 需要保存真实用户Target/Hint编辑时，唯一写键入口 `rigging.key_current(context, session)`（:1015）。`capture_inputs`只读已存 carrier key，不能把未写键的live输出或骨矩阵伪作已保存输入。
9. Return保存前：
   `dto = rigging.capture_inputs(context, session, source_packet_sha256=packet['_sha256'], work_item_id=explicit_work_id, source_action=session['base_action'], source_action_slot=session['base_slot'])`（:1093）。
   返回20-field控制DTO；用 pure `animation_rigging_contract.validate_export`以真实base/input两Action名称+slot、新draftID、完整packetSHA再次验证，然后在 fresh output_root独占写JSON。不得把 Source clipAim 与顶层base Walk_N混成一个clip；不得加入weapon、clip-baked C或已Apply标志。
10. `with rigging.base_only(context, rig, action=session['base_action']): ...`（:1115）可验证独立 base admission/curve/hash；它隔离preview与IK并精确恢复，不授权导出。baseAction、inputAction、Rest/SceneClock/locks/display/NLA/原constraints需分别比对，不能以姿态截图代替身份/曲线保护。

### 关闭和只读/Custom复用

- `rigging.restore_owned(context, rig)`（:1273）关闭 owned preview并保留成功carrier/draft。重选相同Custom base后 `import_inputs(...source=False)`应复用同 `_INPUT_REF` native carrier ID/slot，不生成等内容替代。
- `source=True` 对 local QA Action只能证明 native输入carrier的只读策略；不能声称 Worklist linked read-only Source。完整Source比较必须有单独已认证的linked baseline、cache SHA与原始Action/slot，且输入carrierSource/Custom严格分开。实际所需cache写入须在Root授权的owned QA DATAFILES/output内，不能使用artist Source cache。
- Worklist事务已有 `_capture_rig`（:231）/`_restore_rig`（:248）/`_finish_rig`（:274）。Native的 `_capture_owned`（:1315）→close→failure `_restore_owned_state`（:1449）或success `_finish_owned_state`（:1401）必须配对；武器存在时原显示IDs暂存，failure恢复exact IDs/Scene link，success仅经 unchanged remove_context删旧owned display。restored token finish是no-op；不要留下悬空token或通过clone重建旧几何。
- 当前packet无weaponPreview，所以本round不能验证武器token几何边界；仅验证存在的两臂输入/关闭身份。
- 所有成功、失败、采样异常和Return保存异常都要finally关闭本次session、恢复导入前selected/active/mode/Scene/frame/FPS/Rest/data/Action+slot，并记录恢复失败；不吞错或保存原artist `.blend`。只写获授权的 isolated clone/output。

## 若以后真实提供 Link/workspace：复用原 worklist，不在本轮伪造

- `worklist.connect(context, exact_workspace_path)`（:99）读取真实工作区；`workspace.load_workspace`（animation_workspace.py:325）验证schema、workspace/model SHA、prepared route。
- `workspace.row_key(clip)`（:93）获得真实 key；`worklist.add(context, key, activate_new=True)`（:365）完成 `_prepared`（:131）、Link/packet/model/route认证、base先导、Custom身份、Input carrier导入、Source linked cache，以及失败exact新ID清理。
- `worklist.activate(context, item.item_id, 'SOURCE'|'CUSTOM')`（:584）包含baseline cacheSHA与route重验，close原preview→新session→opaque token成功/失败收尾；别绕过这些API直接改item.side。
- `worklist.remove(context, item.item_id)`（:688）保留Source/Custom Actions，正常closeownedpreview；`adopt_main_rig`（:281）/`restore_main_rig`（:298）只在真实workspace Main Rig transaction成立时用。
- `worklist.sync(context)`（:714）只允许当前CUSTOM；它在 `base_only` 内执行 target ensure/action/route/fingerprint admission，再 Link捕获Rigging control DTO、独立base snapshot，并启动真实worker。**本round绝不调用它。** `links.begin_linked_export`（animation_link.py:320）同样启动worker，不能当作只读capture。
- `links.publish_linked_revision(...)`（:301）只消费真正已完成owned FBX+metadata、锁定当前Link、推进revision；不是纯Return本地保存或raw control DTO的替代。`collector.export_finished(job, result=...)`（animation_worklist_collection.py:744）仅在真实publish返回后写receipt，必须保留实际error，不得伪造launch proof/result。
- 已有 `composition_sync_acceptance.run_one` 是旧Composition B真实physical oracle，依赖preparedB spec；不可拿来运行无Composition的Rigging packet，不能继承旧217/12cases/3pub当新native结果。

## 保护范围和现Source版本

- 此recipe没有生成 Link、workspace、Source cache、Return或QA场景，没有读取共享workspace/原artist内容。
- `animation_worklist.py` caller bcddead36…；`animation_link_source.py` bbf0b65c…；weapon95519565…均保持原样。新rigging nativeAPI b459668d…由独立owner固定，Root package/content pin为准。
- 当前尚缺显式QA WorkID；所有未来 native、matrix比较、Target响应、BASE/INPUT local save、旧输入复用及资源/自然退出验收均pending，不能从Source recipe推断PASS。
