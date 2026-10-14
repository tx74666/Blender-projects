# Original20 原場景回匯與保存驗收 — 2026-10-13

Blender 部分已完成：動畫控制資料保存在原 X.blend／Scene／CoshaRig，原工作窗口保留。最新保存版本 AEA53 已通過獨立原生讀回；本次讀回未改寫文件。全鏈 Unity 的 Collect／組合 Preview／Apply Viewed、兩輪原生 Edit/Undo與Edit/Redo穩態完整快照及指定AOC重新導入均已通過；資源lease已released。最終[原生全鏈驗收](D:/Unity Projects/RandomRealm2/.codex/task-staging/character-composition-20261011/generic-rigging-design/controls-only-verifier-candidate/r2/evidence/native-menu-validation-20261013.json) SHA754A4785，保留舊自動等待超時FAIL，不把它改寫為自動QA PASS。

- Character Designer：批准凍結／部署包 0.77.38，190 文件／158 Python；[投影清單](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/package_e51290d9/python_projection.json)，SHA 0d0678388250fca04ce53164628c9460d6d237a5664d6e14c5f79ea8b337e209。標準 enable／自然一次回調／disable／取消／受控失敗清理已驗證；正式部署與 check 已完成。新重開的 artist 進程內 add-on 版本未用 SDK 再核實；獨立 reader 使用精確凍結的 0.77.38。
- 真實原文件：D:/Blender/Projects/Character/X/X.blend；最新 SHA aea53ab4f324c7d99fdfe0ce40fc3d220b01d77b6c15671a5744e2bea86008f6，34686989 bytes。[最新保存備份](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/artist_current_saved_resume_20261013_01/artist_current_saved_before_readback.blend)與[備份回執](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/artist_current_saved_resume_20261013_01/backup_receipt.json)匹配。
- [独立讀回報告](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original20_artist_saved_readback_07738h_02/original20_artist_saved_readback_report.json)：SHA 69d68f4b0c9369dc2549bd81a77baf59a5b88c6f359e559a0162cd1db526b9ce；completed=true，open_mainfile=FINISHED。13 Actions 中原／恢复 11 Actions 的 slots、完整內容、屬性保留；另兩個 Controls20 Actions 與原 Rig 的 closed PAIR 保留。Pose ACDD 完整內容和 fake-user 持久；原 Body rows／header／catalog、觀測資產的 Rest／骨色／分組／widgets／修改器通過；20 通道與 BF59／Return14 數值、時鐘、身份通過。所有 Objects／Collections 的暫時武器 owner tags及 Rig session／refs不存在。
- [資源回執](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/resource_release_X_LATEST_SAVED_READBACK_07738H_02.json)：SHA dd3e00cb136797e727a7c58809f67b36034ca5eec8c69bfce2c8e9e18f2cbe59；reader PID41024／FILETIME134363478138868435，UTC06:50:13.8570329→06:51:13.3705323，59.5041097秒，retained自然 exit0／gone。最終只剩原 artist PID36396／FILETIME134363465953148764，有回應、無未保存標記；無本任務 child／SDK作業遺留，串行資源已交還。

## 保存履歷與驗證限制

[Writer04](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original20_artist_integration_07738_04/original20_artist_integration_report.json)保持原 completed=false／49F92B 記錄：全部保存前保護通過後，save_mainfile 返回 FINISHED，寫出 E418；同步 dirty 檢查拒絕，沒有執行其完整 live post_save_guard。[返回事件循環後實讀](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/original_saved_status_07738_01/report.json) B728 證明 dirty=false／同一 E418。之後原14500進程結束、文件另保存為 AEA53；來源未核實，保留最新工作，不覆蓋／再匯入。獨立 reader 嚴格讀回新 AEA53 與 writer 的原有資產／Actions／Worklist保護證書，沒有宣稱舊同進程完整 post_save_guard 通過。

原 FF34／05F3 中間狀態仍保留，4869 strict recovery FAIL不改寫；只有精確兩前臂 mute 恢復及兩個 source-owned false 欄位經獨立限定驗收，恢復後整棵資產對原 F9 before_assets 精確一致。單一 Pose 附加的 unused來源 Library允許重讀時省去；最新讀回確實不存在這個無引用來源庫，Pose保留，其他 Library／資產保護未放寬。

讀回 source [07738h2](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/verify_original20_saved_artist_readonly_07738h2.py) SHA78991de1fc35fa6dc3610ea38d08c73f3b0ef875152a7a3b7d30d3be4ae211b7：僅對三個外部回執 pin規範 Windows slash表示，物理SHA／bytes嚴核；沿用 F的完整讀回主體，補足唯讀 _sample需要的 capture.sampleRate。沒有save／frame seek／active session／worker／publication／場景修改。初次 pre-open 路徑拒絕記錄保留。

數值是功能驗證與整個驗收wall time，沒有配對性能或FPS收益結論；world／model全部等價、SKIP_SAVE瞬態反饋相等未聲稱。精確模型及 reasoning effort未記錄。新觸發僅限 Rig／Rest／修正器／控制圖／來源身份改变、保存後恢復異常或新的卡頓；先讀[簡短完成摘要](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/current_return_summary.json)，再按需查[完整歷史 checkpoint](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/workflow_cleanup_20261014/completed_checkpoint_before_summary.json)與既有證據，不重跑已排除的 Body／Gun整套。


## 2026-10-14 小範圍工作流整理

[簡短完成摘要](D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/current_return_summary.json)作為後續入口；完整歷史 checkpoint 保持原字節並保留獨立副本，所有原 FAIL 記錄仍保留。舊 PID、SDK、版本及中間 pending 欄位屬歷史觀測，後續新場景操作前重新觀察即時身份。

共享開發庫新增唯讀 [verify_file_pin.py](D:/MyRepository/Blender-addons-by-Randy/tools/verify_file_pin.py)：規範 Windows 路徑與 SHA 大小寫，仍嚴格核對三欄格式、物理 SHA-256 與字節數；分塊計算哈希。例：`python -B tools/verify_file_pin.py <receipt.json> --field inputs.writer_report`。8 項輕量回歸測試及三個真實外部回執 pin 通過。

沿用已驗證準備經驗，減少重複排查：

- 執行前核對接口與七個惰性 package 模組別名；不要直接重跑整套場景測試來尋找載入缺項。
- integration／reader 預建新的空輸出目錄；finalizer 自建目錄並要求該目錄事先不存在。
- 保存返回 FINISHED 後先返回事件循環，再讀 dirty／文件身份並做獨立讀回；同步 dirty 門的 FAIL 與後續證據分別記錄。
- closed PAIR 的 `_sample` 需要 action、slot 與 `capture.sampleRate`，保持來源時鐘。
- artist 已另存或 PID 改變時先保護最新內容、刷新身份；不重用舊 PID、舊文件 SHA 或同進程 finalizer 前提。

本輪只整理工具與驗收入口，沒有啟動原生測試、部署／刷新 add-on 或改写／保存場景；X.blend 與已驗收結果保持原有字節。這是工作流整理，沒有新的執行性能／FPS收益測量。來源版本仍為 0.77.38，Blender 驗收版本為 5.2.0 LTS；即時 artist add-on runtime 未新觀察，模型／reasoning effort 未記錄。下一輪僅在新身份／Rig／Rest／控制圖／修改器、保存恢復異常或新的卡頓出現時展開。
