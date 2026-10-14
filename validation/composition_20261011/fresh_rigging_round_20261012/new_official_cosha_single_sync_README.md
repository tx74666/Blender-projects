# 新 Cosha 單條物理回匯入口

這是 Source 準備，尚未執行。腳本為 `new_official_cosha_single_sync.py`，SHA256 `0854aa755b0e50438d0be054f885aa57f68f67862e8de97f6e3b86f56f8f325b`，16150 bytes。Source peer 為 `new_official_cosha_single_sync_peer_0854aa75.json`。它沿用 exact `new_official_cosha_round.py`（`cfaa6dc580d69dbdc7c752078752f2a3cbe89f33ec02a60c5186a196fba4cdcb`），不改插件，不打開原 X.blend，也不遷移舊工作區。

先在獨立新窗口完成 public Setup → Connect/Add/Activate → 四個 Target/Hint 的真實 transform 和明確保存 → 真實 Undo/Redo → 保存、重開。選用 Walk Right reference 時，另量測下半身 pose 與 normalized BASE strip，並核對原 20 個輸入和 Return 不變。這一段的報告必須實際完成，單純 Source receipt 不適用。

第二段取得 fresh 單窗口及單 worker 資源範圍後，用另一個 factory/headful/disable-autoexec 進程啟動物理腳本。沿用正式 Prepare22e 的實體輸入、同一完整候選包、同一 control report/scene/Return；使用新的空 output child 及短 profile root（只含空 CONFIG、DATAFILES），環境 BLENDER_USER_CONFIG、BLENDER_USER_DATAFILES 必須精確指向這兩個目錄。profile 不得在 Unity project 內。

必填 CLI：prepared-report、protected-artist、source-freeze、package-manifest、control-report、control-harness，這六項各自另填 `-sha256`；另填 script-sha256、unity-project-root、output-root、profile-root，以及 `--confirm-isolated-headful --confirm-one-manual-sync-worker`。可以加 `--quit-on-completion`。全數使用當輪實際路徑和完整 SHA，不使用佔位檔案或把歷史權限視作 fresh START。

物理段重新打開成功 control trial 的獨立檔案，先讀 saved native cache，再讀正式 row/session。它保持 Custom base、Source、20 條 input 和控制器/顏色/分組 proof，選取這一個真實 row 後只呼叫一次現有 `worklist.sync(context)`。既有 Unknown 不會被改成 Known，也不啟動 changed_only queue。

腳本僅接管該 job 的 `animation._poll_action_export` timer。worker 仍是既有 exporter 啟動的正常 background 程序；每 tick 非阻塞等待。自然退出後先保存整個 worker temporary root，再 `poll_export` 和 `collector.export_finished` 各一次。歸檔失敗時仍嘗試正常取消、dispose 這個 exact owned job，分別保存錯誤。

成功須具備非空 FBX 和相鄰 metadata 的真實 SHA、原 Link identity 不變且 revision 僅加一、archive 的 actual result/selected slot/bones list、嚴格 14 字段 Return 等於控制段 DTO、20 local components 不變，以及空 Collect receipt error。報告保留真實 Unknown/dirty、launch proof 與 last_synced_receipt。成功後另存 `new_official_cosha_after_single_sync.blend`；不覆蓋控制段或 artist。

報告寫在當輪 output 下的 `new_official_cosha_report.json`，schema 為 `x.validation.new-official-cosha-single-sync/1`。natural window exit 由外部 launcher 實際確認，worker exit code 由此報告保存。任何失敗保留當輪檔案和錯誤，停止重試；不能把 publication 成功但 receipt 錯誤記為完整 Sync 通過。

Blender 物理回匯完成後，Unity Collect、Base Apply、Target Apply 仍各須 Parent 的實際入口、consumer 和 Undo 證據。新 Cosha 的獨立驗證也不表示原 X Rig 已回接完成。canonical Source、完整凍結包、實際安裝副本、目前 artist session 已載入版本須分開記錄。
