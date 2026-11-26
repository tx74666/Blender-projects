# Shared add-on development

<!-- cd-maintenance-owner-20261118 -->
## CD 維護分工（用戶 2026-11-18 指定）

用戶指定本對話（`01a1ea71-a5c1-7bf0-b904-da5ed3ad9615`）接手 Character Designer（CD）插件，負責後續功能開發、問題修復、驗證、版本交付與交接記錄。沿用下列正式原始碼、完整已核准投影及現場保護規則；共享前景與實際衝突操作仍遵守 Animation 優先指示。



<!-- formal-x-daily-entry-20261109 -->
Daily scene is now D:/Blender/Projects/Character/X/X.blend, natively promoted
from latest X2 RAM and normally reopened via the sole desktop X entry. Old X
latest RAM is archived under Archive/Retired_X_20261109_01; old X2 sources and
all resource directories remain. No stale old-X restore or whole-folder move.
Current-file handoff: docs/CURRENT_X_HANDOFF_20261109.md; source receipts are in
validation/x2_promote_formal_x_20261109/file_support01.169 plugin is unchanged;
managed production-owner limits remain. Reobserve current RAM before action.

<!-- cd251-loop-workflow-20261126 -->
Character Designer **0.77.251** 已安裝至 Blender 5.2 與 X，各 318 檔、0 差異。Prepare 支援整幀循環，預覽範圍按動作保存，減鍵支援普通 Repeat Motion Cycles。隔離熱刷新保留活動預覽及原動作，正式 X 的未保存工作由使用者保留。[發行記錄](<D:/MyRepository/Blender-addons-by-Randy/docs/releases/CharacterDesigner_0.77.251_loop_workflow_20261126.md>) · [磁碟交付](<D:/Blender/Projects/Character/X/validation/loop_workflow_delivery_20261126/delivery251.json>) · [功能驗收](<D:/Blender/Projects/Character/X/validation/loop_workflow_20261126/acceptance251.json>) · [完整投影](<D:/Blender/Projects/Character/X/validation/loop_workflow_20261126/stage251_02/projection.json>) · [前版交付](<D:/Blender/Projects/Character/X/validation/neutral_motion_20261126/delivery250.json>)。

<!-- cd114-compact-physics-20261029 -->

Current complete225/193py **0.77.114** extends approved113 by6changed/219exact.

Approved `D:/Blender/Projects/Character/X/validation/physics_compact114_20261029/stage114_01/projection.json`,

SHA `0df365bdfa6ab58006405703f71096d56c40dc599632c39480ff90d0be0a8e36`. Physics checkbox is in its header;

single Skirt CTL means Manual when pressed, Automatic otherwise. New unset

choices default Automatic; existing saved choices remain. Original/permissionOff

may choose without native writes. Completed Controls return/permission restoration

applies explicit pending choices through existing guards; refusal keeps intent/error

without undoing a completed return. Explicit Skirt On reconnects stoppedAuto.

Routine character/readiness/motion/Original hints hidden; real errors/recovery kept.

Missing support opens pinned author2.2.4 acquisition page, not automatic install.

Official ZIP and dual5.2/X deploy/check225/0diff;223pure, realSkirt10, nativeUILayout6,

private installer3rollback+success passed. Native01 pre-feature fixture C-crash kept;

exact cause unproven. Native02 lifecycle derivative passed, not a product change.

Tiny Original-marker/nativehelper checks are not full Original-session/artist

dynamics, loop/FPS/collision or complete artist author-array acceptance.

Artist14840 ALREADY114: fresh strict4module/144definition audit passed ONLY,

code_committedfalse. Unknown refresh time/initiator; no identity claim across it.

Object/CoshaRig/selected[]/frame25/dirtytrue retained within audit, physics RAM/native

flags exact; lower-left restored VIEW_3D. No agent artist physics action, scene/prefs

save, reload, SDK/timers, Unity or Git upload. Private processes exited; native01

crash is distinct from normal native02/layout/installer cleanup. Artist retained.

Entry `D:/Blender/Projects/Character/X/validation/physics_compact114_20261029/acceptance_summary114.json`,

SHA `4de18ca22c1e449d1598842b35797d11ac17e3fc5099da92ff4189aa5c1635b9`. Preserve earlier failures/recovery limits and pending console caution;

future releases extend this complete projection, not plain canonical/old installers.



User-authorized workflow cleanup2026-10-29; runtime/performance code unchanged by this cleanup. Unchanged original history: `D:/Blender/Projects/Character/X/validation/workflow_streamline_20261029/X_AGENTS_before.md`; historical "current" is past state. Read only relevant history when needed. Future releases update only the current block+separate release note, not append reports here.



## Latest completed checkpoint: Character Designer0.77.113



Complete225 files/193py; supersedes110/interim111/112,4changed/221exact versus110. Approved `validation/physics_checkbox113_20261028/stage113_01/projection.json`, SHA256 `726a19b2364da7098cc2866b0bcf13da118f140b8e83c740bb8ac34db044b0be`. Acceptance `validation/physics_checkbox113_20261028/acceptance_summary113.json`, SHA256 `bbcccfc9b16f156bdc832a1b046e872a622f2dc2faa7e4ac963e77d18d7b861a`.



Hair checkbox starts inactive Hair, pauses/resumes its owned solver; stopped Hair unchecked with master On. Routine buttons/help/three explanations removed; errors/recovery/Skirt guards retained. Master resumes existing sessions only. Pure130/private real-Hair native10/cleanup, officialZIP/dual5.2-X225/0diff passed. Tiny Original-marker fixture isn't full Original-session/artist dynamics/FPS/loop/collision acceptance. Keep native01/02 failures; v3 doesn't prove native02 cleanup.



Artist14840 ALREADY113: strict UI/service+synchronous identity/context/physics AUDIT ONLY, no code commit/reload. Unknown refresh time/initiator; no cross-refresh identity/full author-array claim. OBJECT/CoshaRig/selected[]/f22/dirtyfalse/VIEW_3D is historical. No agent artist physics/save/preferences/Unity/Git/SDK/timers; children exited. Fresh formal/preferences pins aren't old110 equality. Reobserve live identity/context/code before action.



## Source, parallelism and resources



- Read canonical `D:/MyRepository/Blender-addons-by-Randy/AGENTS.md`; runtime changes belong first in its `addons/`. X `addons/character_designer`/Blender installations are deploy copies. Assets/scene integration remain in X.

- Extend the latest complete approved projection with validated increments, retaining approved Body/Forearm while excluding unrelated paused candidates. No plain-canonical paused deployment or old installer/pending-summary replay. Canonical `docs/release_workflow.md` and `tools/prepare_release_projection.py` reuse complete-baseline/explicit-delta preparation; preview by default, new candidate only with `--apply`, no automatic approval/build/deploy/live installer. Use official `tools/build_releases.py`, `tools/deploy_local.py --project-addons D:/Blender/Projects/Character/X/addons`, then matching `--check`; verify active executable/version and its target too. Disk deployment isn't live refresh.

- Parallelize independent analysis, disjoint edits, staging/validation. Short windows only for same-file/data writes, competing input and same-Editor import/compile/Play/scene mutations; no whole-app/task reservation.

- Reread capacity/actual memory before heavy work. Only actual available below about200MB (209715200B) stops X work for memory; load/stage predictions and obsolete1GB/2GB thresholds aren't extra gates. Near98%, slow/recheck real conflicts, never percentage-only refusal. Keep quality/error checks; don't close user apps or discard work.



## Artist, saves and recovery



Protect latest unsaved geometry/topology/paint/weights/locks/bindings, Keys, Rest/pose, Actions/slots/NLA/drivers, SESSION/REFS/worklists/recovery and context/selection. Follow canonical weight-correspondence rules: rebuild isn't reweight/transfer/normalization/old-paint restore/calibration recapture; counts/indices alone don't prove surviving vertex identity. Never overwrite artist with private files or restore stale BasePose/history permissions/forge Original. Restore Main Rig remains user-deferred. Keep formal `validation/si01` and private `validation/sf01` scene-library dependencies.



Observe fresh scene authority; `tools/verify_file_pin.py` grants no permission. Save authorized completed scene work normally; verify native success/post-event state. Code-only updates preserve dirty work, don't authorize scene/preferences save/restart/fullreload/bake/export/Unity/Git. No expired-capability replay/reset flags. Preserve failures/phase limits; later proof doesn't fill old gaps. Normally close owned idle workers/SDKs/timers only; retain uncertain shared services.



Original20 return entry: `validation/composition_20261011/fresh_rigging_round_20261012/current_return_summary.json`; older `current_return_checkpoint.json` is historical. Relevant Ground85/BasePose96/101/legRest102/edit-mirror/CurrentRig103-104/physics107-113 failures and recovery remain indexed in the full archive. Old checkpoints are not new authorization.



## Trusted validation and relevant checks



Trusted X/agent scripts need no repeated permission. Canonical `tools/run_trusted_blender_validation.py`: `--enable-autoexec`, `bpy.ops.wm.open_mainfile(..., use_scripts=True)`, no disabling overrides. Fresh `BLENDER_USER_CONFIG` for all owned Blender; GUI adds TEMP/TMP+private `preferences.filepaths.temporary_directory`, verifies `bpy.app.tempdir`/recovery. `--user-startup`/`--user-config-source` copy/pin profiles; never overwrite/save artist preferences. Hashes are snapshots: preserve legitimate settings/back up before authorized recovery. Canonical `docs/trusted_blender_validation_preferences.md`, X `validation/pole_preferences_recovery_20261018/README.md` and `validation/gui_playback_20261023/shader01/result.json` govern details/old shared-TEMP limits.



Reuse fast tests/helpers. Layout alone needn't restart unrelated dynamics/FPS; state/default/solver/ownership changes need relevant native transitions/author/rollback proof. Complete mandatory protection/deployment checks; repeat only for changes/failures/gaps. Pinned harnesses unchanged, new autoexec/isolation derivatives identified. Fix harness errors without relabeling failures/weakening gates. Prepare/test/package, then short live update/UI window; reuse unchanged receipts, never stale authority.



## X playback-FPS branch: economically closed



Before separately authorized performance follow-up read `validation/forearm_pipeline_20261023/CURRENT_DIAGNOSIS.md` (keep one page) and `D:/Codex/資料庫/电脑与工作环境/Blender性能優化台帳.md`. **The existing X playback-FPS investigation is economically closed:30FPS not reached/hardware limit unproved; no further native/sampling/AB/micro-patches in that branch; its old reminders cancelled.** This does not prohibit other independently authorized work. Workflow cleanup changes no runtime/algorithm/parameters/quality/gates/benefit.2026-10-21 heavy round/`HEAVY_ANALYSIS_PENDING.md` completed; old reminderx PAUSED, superseded for that branch by cancellation. Light-only/waiting/2-hour reminders are historical, not authority to restart. ShoesAction removed/saved after user confirmation.



Historical performance entries under `validation/`: `performance_20261021/README.md`, `performance_round2_20261021/README.md`, `sync_latency_20261022/README.md`, `idle_playback_20261022/README.md`, `idle_followup_20261023/README.md`, `gui_playback_20261023/README092.md`, `forearm_hotpath_20261023/README.md`, `forearm_rest_scope_20261023/README.md`, `forearm_points_release_20261023/README094.md`, `playback_release099_20261025/current_delivery100_checkpoint.json`/README100. Diagnosis also indexes final PC2/CPU/inventory/Console/economic-stop receipts. Keep their scope/failures;103/102 historical delivery paragraphs aren't current baselines. Fixed100/c0159 measurements cannot mix with102/71dce/Idle.100 event/Play gaps remain incomplete: no fake terminal/replay/auto-downgrade. No repeated whole-history QA; don't add nested profiling times, invert guard durations intoFPS or call background frame_set/GPU cadence artist GUIFPS.



Timing tables: actualms/target-budgetms/gap, nesting; label measured reference/estimate/unproven goal, no silent loosening/hardware-limit claim. `validation/ms_standards_20261025/reporting_budget01.json` grants no quality/resource/artist authority. Record date/source-runtime/model-effort (unknown=unrecorded), comparable measures/limits/deploy-refresh-save/next trigger. X owns Character Designer, Builder6/Build WIP RR Helper, Unity owners theirs. Index raw owner evidence in existing Console database, no duplicate.



## Evidence retention



Keep concise conclusions/changes/input-version-hashes/replay entries; retain latest acceptance/failures/recovery/pinned sources/manifests/receipts/logs/dependencies/backups. No fixed-hash rewriting/age-deletion. Eligible compaction: `tools/compact_validation_report.py` preview+verified sourceSHA, lossless XZ `.validation-archives/`, restored bytes/hash/length verified, schema summary+original field paths/local archive. Archives excluded normal Git uploads; disclose remote-summary limits.2026-10-14 consent covered one Original-leave report only; others reviewed individually. No Blender/save/Git during compaction; all claims retained in original archive.

