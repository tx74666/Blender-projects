# X 播放優化交付（2026-10-15）

**CD 0.77.41 已正式部署、在原 artist 窗口刷新並完成原生保存；完整模型的鞋子 Mirror 合併開關優化已採用。** 舊 X 聊天已繼承並歸檔。此次採用沒有刪除 Cosha／Shoes、減少面數、停用骨骼／細分或關閉修正輸出。

當前 task 的本地索引已記錄模型 `gpt-6.1-sol`、reasoning effort `ultra`。原生環境為 Blender 5.2.0 LTS／artist PID 24416。測量輸入是 `input_saved_20261015.blend`，SHA256 `40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721`，34,691,613 bytes。較早 round3 的版本 ABBA 使用另一保存輸入 AEA53／34,686,989 bytes，兩者不能混作同一現場測量。

| 已核實結果 | 口徑與限制 |
| --- | --- |
| .41 的同次 Rest 現讀快照與有序精確權重 Matrix 復用 | round3 同進程單線程版本 ABBA 約減少 5.3% 背景求值時間；123 純測試、6 套原生驗證和 128 熱幀輸出相同。完整現讀引用／ownership／Rest 與拒絕順序保留，沒有跨幀正向證明快取。 |
| 當前窗口 .40→.41，Material 3.676→4.296 Hz；Solid＋側欄關閉 4.655→5.735 Hz | 各版本、各模式 2 次順序採樣，暖機 2 秒＋測量 16 秒。8 份指定報告皆正常完成、回調例外 0、評估／顯示涵蓋全部 1–30 幀，全部恢復與輸出證明通過。時間、負載和幀分布改變，不能把觀察差額全歸因於版本；不是受控 GUI ABBA。Forearm 平均約 87→65 ms，仍是主要成本。 |
| Shoes.Mirror.use_mirror_merge `True→False` | 完整 .41 模型、同進程單線程 8×8 熱幀 ABBA：80.5708→77.287075 ms，約少 3.28 ms／4.08%，屬小幅收益。1–30 每個整數幀的完整求值坐標、拓撲、loops、UV、材質索引、法線、權重、attributes、物件矩陣及 Forearm／pose 全部精確相同，inventory／Rest 與 L/R191 健康。不是對日後新拓撲／所有動畫的全域等價證明。 |
| 採用 MergeFalse 後最後 GUI 驗收 | Material 4.406863 Hz、frame evaluation 中位 102.7228 ms；Solid＋側欄關閉 5.627202 Hz、中位 109.1328 ms。兩份均完成、例外 0、全 30 幀覆蓋、全部恢復／managed 坐標與 raw channels 相同。這是最終可用狀態的觀察，沒有足夠證據另聲稱 GUI 增益。 |

最後 Material 的原生評估約 102.7 ms，其中 Forearm 均值約 60.5 ms；觀察 4.4 Hz 約對應 227 ms 的變幀時間尺度。其餘間距混合 redraw／draw／排程等成本，本輪沒有獨立分離 CPU 與 GPU。Material／Solid 的差異只是顯示模式的實測觀察，內含函數時間互相重疊，不能相加推算剩餘成本。兩個已採樣 CD panel draw 均值各約 0.055–0.059 ms；Wiggle pre／post 回調各低於 0.03 ms，Auto-Rig Pro 的 layer 回調約 0.013 ms，均無例外，這些回調不是本輪主要 Python 成本。

使用者的「4.5→10→30 FPS」實際操作是原生 Delete Cosha，再 Delete Shoes，最後 Ctrl Z。私有 .40 原生診斷的求值中位為完整模型 131.47535 ms、Delete Cosha 44.04445 ms、再 Delete Shoes 9.4892 ms；Delete Shoes 單獨控制為 105.27405 ms，Cosha 仍健康。**Delete Cosha 移除了當前 Scene 的唯一 Forearm owner，因此成本下降同時包含修正器不再執行，不能當成保留模型的優化收益。** 此次沒有證明刪鞋導致校正失效或 mute；不可沿用先前假設冒稱結論。

在全部私有案例先 Delete Cosha 後，Shoes 完整／Mirror 停用／Armature 停用／兩者停用分別為 32.33225／10.62365／17.1215／7.67185 ms。這只定位原生修改器成本，停用 Mirror 會減半拓撲、停用 Armature 會失去變形，均未採用。採用的只是經精確輸出證明目前無作用的 Merge boolean。

.41 的 190 檔批准投影已部署 Blender5.2 與 X/addons，兩處 check 差異 0。原 artist 的 v3 刷新回執完成，12 個內容 component 完全相同、完整 owner／L/R191 保留，task helper 已釋放。MergeFalse 的現場採用回執完成，只寫入上述一個 boolean；實際全內容符合預測 12 components，當前 frame21 求值 Shoes 與完整 Forearm／pose 匹配私有基線，context／dirty／callbacks 不變，4 個 owned modules 已清理、poll timer 已離開，errors 空。

最終 v4 原生保存已完成：`save_mainfile=FINISHED`；保存後即時 dirty=true，下一 event-loop 證明 dirty=false。12 個保護 component、context（檔案路徑另嚴核）、完整 owners 與 callback identities 相同，4 個 owned modules 已清理、poll timer 已離開、errors 空。原 Hair 文字仍保留在當前未提交的 Console 輸入 buffer，本轮没有执行该指令。最终现场为暂停 frame21／Object Mode／active Cosha／无选择、Material／侧栏恢复。

- `final_save_receipt`: [completed final-save receipt](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/final_save_07741_20261014T193850Z_78209ee53556/final_save_receipt.json)
- `final_artist_sha256`: `ad5bf8ecbfe45d1ca9041c2d3608f0defe68c605e8ad10cd87a95bc946d5ae92`
- `final_artist_bytes`: `34,845,822`
- `final_dirty`: `false`
- `final_save_status`: `COMPLETE`（外部 SHA256／bytes 再核對與回執相同）

保存證明範圍為原生保存與跨保存完整 in-memory 內容、context 和外部檔案 pin；本輪沒有獨立重開最終 artist 讀回，也沒有 Undo-stack 保留證明。保存時 managed 坐標與最後已發布的 output cache 相同，保存腳本未獨立重算全部修正數學。原生收尾觀察與完成狀態見 [closeout_native_observation_20261015.json](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/closeout_native_observation_20261015.json) 及 [current_work.json](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/current_work.json)。

最終 artist 磁碟為 ad5bf8ec／34,845,822 bytes，採用 boolean 已保存。固定測量輸入 40644／34,691,613 bytes 保留原字節。已驗完整保護 SaveCopy 為 `refresh_07741_20261014T184749Z_eb541cbd852e/artist_unsaved_before_07741.blend`，SHA256 `ff7b9caa4e87fed74751fdac9222775ea4f184f8e912e432a57d0601125d066a`／34,852,496 bytes。最初 profiler 回調失敗、兩份刷新 preflight 失敗，以及 final-save v3 因 Console history 型別 admission 失敗的原件保留；v3 沒有呼叫保存 operator，也沒有執行待輸入的 Hair 指令。

| 固定證據 | SHA256／bytes |
| --- | --- |
| [current_window_summary.json](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/current_window_summary.json) | `029c79f20aed49fa741c050d30333b99113b6d64a399197cafe37008784975bf`／19,217 |
| [v3 refresh receipt](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/refresh_07741_20261014T184749Z_eb541cbd852e/refresh_receipt.json) | `c1e2aa7675826ceb5b1a884eb353e79891291f180748760a0e38a16edea567c8`／51,637 |
| [native deletion report](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/native_delete_report_20261015.json) | `b8785f44d9e5ac09e898c8ffdbd08e524465283ccadd4987ae2c84dc47f3fb12`／83,076 |
| [native Shoes modifier report](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/native_shoes_modifiers_report_20261015.json) | `40812c265ff6fcde568592e478f12b9688e3ed90154bbef04dfa411bb1997617`／19,593 |
| [native MergeFalse differential＋ABBA](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/native_shoes_merge_report_20261015.json) | `f8de14c1a26f2dcab033ac42bcb07bda19194da4e3d47110a782d2935a21098f`／33,154 |
| [live MergeFalse adoption](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/adopt_shoes_merge_20261014T192131Z_a2027c58a0ed/adoption_receipt.json) | `c12f8fbc8979ec62b96cb04eb4747fc6a4bccaf397c08f6a41af78023c5d50d7`／50,241 |
| [final Material sample](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/response_material_1792005970067231100.json) | `c8b2cd148114a1ece2e97a3f993d2dfbf43e345e0d905885dbb2a7f88f70282e`／44,642 |
| [final Solid sample](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/response_solid_panel_closed_1792005989622372500.json) | `379eb9a968b3b66c4bb37a068ec9435a26693c702861fcdb3539cdf607af417a`／48,584 |
| [completed final-save v4](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/final_save_07741_20261014T193850Z_78209ee53556/final_save_receipt.json) | `cd5f54204a19c85ea00dacc0f606a4aa7ca221580f166843da9491a4eb3e5f24`／47,753 |
| [failed final-save v3 admission](D:/Blender/Projects/Character/X/validation/playback_performance_20261014/round4/final_save_07741_20261014T192834Z_15c1805b8f8c/final_save_receipt.json) | `1b2540b51810bd43941fc9c2ba2fd2025334753d84ef3c07b6f3bdcd3c84bdee`／2,615 |

本輪已完成，原 artist 保留，沒有本任務殘留的背景 Blender／native／GUI／重型作業；已向 Character 發送 END，Unity 未改動。原始證據與失敗／恢復依據保留，沒有 Git staging／commit／push。既有性能台帳的同一播放條目與既有 .41 release 已更新，沒有新增重複條目。

優化停止於已驗證的小幅收益。下一次針對新 Rig／Rest／saved references／權重／拓撲／Merge 平面或新動畫輸出改變，以及可穩定重現的剩餘停頓採樣；既有 .40 immutable JSON 計畫已完成，沒有重新開快取分支。若再考慮 inverse／condition 快取，先測各 stage 的 inclusive cost、inverse attempts 與 unique exact linear matrices。鞋子日後若需要鏡像縫合，重新啟用 Merge 並驗證。
