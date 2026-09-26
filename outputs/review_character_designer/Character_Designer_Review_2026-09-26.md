# Character Designer 整體健檢 — 2026-09-26

檢查版本：0.61.62，共用原始碼 `D:\MyRepository\Blender-addons-by-Randy\addons\character_designer`，Git HEAD `3dad87c`。Blender 5.2.0 LTS。使用者沒有特定症狀，本次目標是找出可重現的設計、資料一致性及性能問題。

確認 6 項問題。最優先是拓撲鏡像的動畫資料保留，以及前臂校準後的即時更新成本。未修改插件程式、未部署、未提交 Git，也未存回現有角色場景。重現腳本和報告保留在本目錄。

**1. [P1] 拓撲鏡像會使 Shape Key 動畫和驅動器失去連接**

位置：[topology_symmetry.py:916](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/topology_symmetry.py:916)，呼叫處在 1356 與 1445。

`_populate_shape_keys()` 在新 Mesh 上重建 Key 資料，只移轉座標和部分屬性，沒有移轉原 Key 的 animation_data，也沒有事前拒絕帶動畫的操作。正常執行公開的 Topology Mirror 後仍回報成功。

重現：帶有 ArtistExpression 動畫及另一個驅動 Shape Key 的既有測試模型，操作前有 Action 和 1 個 driver；操作後新 Key 的 Action 為 None、drivers 為 0。原本第 1 幀 0.2、第 20 幀 0.8 的表情值，變成兩幀都是 0.8。原資料仍暫存在無使用者的舊 Mesh 上，但當前角色已不再使用它。

建議：完整保留動畫資料、Action slot、NLA、drivers 及相關 ID 引用；無法保證時先拒絕操作並保留原資料。Repair Selection 共用相同重建函式，也需要涵蓋。

證據：[重現腳本](D:/Blender/Projects/Character/X/outputs/review_character_designer/topology_review_probe.py)、[實測結果](D:/Blender/Projects/Character/X/outputs/review_character_designer/topology_review_probe.json)。

**2. [P1] 前臂校準後，每次更新都在命中快取之前重做昂貴的網格驗證**

位置：[forearm_twist.py:817](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py:817)。`_calculate_object()` 260–265 每次先做 `_prepare_runtime_records()`，817–828 重做骨架、左右對稱與拓撲準備；輸出快取判定直到 356–358 才發生。depsgraph callback 452–455 沒有先篩掉無關更新。

真實歷史測試場景：`outputs/rig/fixtures/X_forearm_ranges_0555_preview.blend`，Cosha 3,795 個頂點、已有雙側前臂校準。獨立背景 Blender 中每組暖機 3 次，再對未改動的同一 depsgraph 量測 7 次。

| 狀態 | 單次更新中位耗時 | 範圍 |
|---|---:|---:|
| 啟用，輸出快取命中 | 268.34 ms | 242.83–316.40 ms |
| 雙側停用，輸出快取命中 | 236.40 ms | 210.51–297.60 ms |

每組 7 次更新仍發生 35 次全網格拓撲 hash、7 次鏡像環配對，沒有進行 corrected_vertex 校正計算。成本主要出現在快取之前。這是 handler 執行時間，沒有量測 GUI FPS，也不是大型模型壓力測試。

建議：將 topology/rest/binding/profile 驗證和 migration 改為相關資料變更時才執行；姿勢更新採輕量判斷。不相關依賴圖更新直接返回。停用時仍要完成一次校正輸出的 reset/mute，再進入低成本狀態。

目前保存的 X.blend 沒有前臂校準記錄，其空閒 forearm handler 約 0.02 ms。因此不能把歷史校準場景的結果當成目前 X 的卡頓原因。

證據：[確認腳本](D:/Blender/Projects/Character/X/outputs/review_character_designer/performance_forearm_confirm.py)、[確認結果](D:/Blender/Projects/Character/X/outputs/review_character_designer/performance_forearm_confirm.json)。

**3. [P2] 拓撲鏡像會清除整個物件的銳邊、摺痕及倒角權重**

位置：[topology_symmetry.py:30](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/topology_symmetry.py:30)，屬性移轉在 873 行跳過 `sharp_edge`、`crease_edge`、`bevel_weight_edge` 和 `bevel_weight_vertex`，之後也沒有補回。

重現：操作前有 22 條 sharp edge，操作後變成 0；三種 crease/bevel 權重屬性全部消失。由於整個 Mesh 被替換，影響也包含選中來源和其他未編輯區域，可能改變平滑、細分與倒角結果。

建議：依既有 edge/vertex origin 對照移轉以上屬性，驗證未編輯區域完全保留，並補上法線等其餘資料的保留契約。此項與第 1 項共用同一實測腳本與 JSON。

**4. [P2] Quick Bind 後改名骨骼，恢復綁定會還原到失效的舊群組並刪掉備份**

位置：[quick_bind.py:205](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/quick_bind.py:205)。只按備份中的舊名稱尋找群組；找不到就在 212 行重建。232–234 的預檢沒有確認骨骼／群組對應，246–248 仍清除備份。

重現：原 A/B 權重 0.5/0.5，Quick Bind 後變成 0.8/0.2；正常將骨骼 A 改名為 Renamed_A，Blender 也自動改名群組。Restore Previous Binding 成功返回，但實際留下 Renamed_A=0.8、B=0.5，另外新建無作用的 A=0.5。A 位移 1 時，頂點 X 原應恢復 0.5，實際為 0.6153846；備份已刪除。

建議：保存能跨改名追蹤的對應；無法確認時拒絕恢復並保留備份，避免回報虛假的成功。

證據：[重現腳本](D:/Blender/Projects/Character/X/outputs/review_character_designer/safety_quickbind_rename.py)、[實測結果](D:/Blender/Projects/Character/X/outputs/review_character_designer/safety_quickbind_rename.json)。

**5. [P2] 同時清理相依 Shape Keys，第一次不會真正清掉變形**

位置：[shape_key_tools.py:242](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/shape_key_tools.py:242)。所有目標都取自修改前的 relative-key 座標，沒有計入同批次中也被清除的父 key。

重現：Basis Y=0、父 key Y=0.5、相對父 key 的子 key Y=0.75。同時選兩者並清除後，父 key=0、子 key=0.5；子 key 相對變形仍為 0.5，實際 evaluated mesh 也偏移 0.5。再按一次才歸零。現有測試刻意檢查舊快照值，因此測試通過不代表「清除變形」的結果符合按鈕語意。

建議：按 relative-key 相依關係計算本批次完成後的最終基準，或拒絕同批選到相依鏈並提供清楚說明；加入評估後的變形與重複操作不再改變結果的驗證。

證據：[重現腳本](D:/Blender/Projects/Character/X/outputs/review_character_designer/shape_key_review_probe.py)、[實測結果](D:/Blender/Projects/Character/X/outputs/review_character_designer/shape_key_review_probe.json)。另測試的「Edit Mode 尚未同步座標」情境沒有重現失敗，不列為問題。

**6. [P2] 完全未使用的失效貼圖，也會阻止 Unity 匯出**

位置：[unity_export_worker.py:332](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_export_worker.py:332)，缺檔錯誤在 540 行。

材質影像搜尋收集節點樹中所有 image，包含未接到材質輸出的舊節點。完整 export_job 實測：有效 Principled 材質中僅多放一個完全未接線、檔案已遺失的 Image Texture，整次匯出就失敗；刪除該節點後，相同骨架／網格成功輸出 FBX。

建議：只處理有效 Material Output 實際依賴的貼圖；未使用的缺檔可略過並提示，也避免複製無關的大貼圖。

證據：[完整匯出重現腳本](D:/Blender/Projects/Character/X/outputs/review_character_designer/export_unused_texture_probe.py)。

**流程與架構建議（與上述已重現問題區分）**

- 統一角色目標來源。[animation.py:26](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation.py:26) 使用動畫獨立設定、當前骨架、硬編碼 `CoshaRig`，沒有沿用 Character Setup Main Rig；多角色時容易困惑。建議 Main Rig 作預設，保留明確覆寫。
- 提早顯示動畫相容性。[unity_animation.py:131](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation.py:131) 拒絕有骨骼 constraints 的目標，因此完整 Body Setup 不能直接銜接此預覽流程。這是已知能力限制；可在操作前說明條件，避免最後一步才失敗。
- 把「資料保留」定義成共用契約。現有多個模組已有備份與回滾，但 topology mirror、Shape Key cleanup、Quick Bind 的保留／恢復語意各自實作。應共用驗證規格，尤其覆蓋動畫、改名、未編輯區域和操作後實際變形。
- 將高成本計算與即時更新分離。前臂問題顯示目前的快取主要避免輸出計算，仍需對快取前的驗證成本設性能預算。
- 本次統計為 83 個 Python 模組、63,250 行；`__init__.py` 8,750 行，`limb_ik.py` 9,146 行。可逐步分離註冊、服務、狀態和 UI，便於驗證；行數本身不是性能問題，也不建議只為拆檔做全面重寫。

**已做驗證與範圍**

- `deploy_local.py --module character_designer --project-addons D:\Blender\Projects\Character\X\addons --check`：Blender 安裝版、X 驗證副本與 canonical 原始碼，各 103 個檔案，差異 0。
- 既有測試通過：Character Designer 48 項、UI Pages 4 項、Shape Key Tools 6 項、Topology Mirror 7 項、Quick Bind 8 項；另通過與 RR Helper 的兩種載入／卸載順序。
- 以上額外重現情境均在獨立背景 Blender 執行。前臂性能以現有真實歷史場景唯讀載入後量測；停用測試只改該背景程序中的記憶體狀態。
- 本次是定向程式審查與重現，未跑完所有回歸測試、未量測 GUI FPS、未實際在 Unity Player 驗證，也未檢視目前操作中的 UI 畫面。

建議修正順序：先完成拓撲鏡像的動畫與屬性保留，再改善前臂更新；之後處理改名後恢復、相依 Shape Key 清除和無關貼圖阻擋匯出，最後統一角色選擇流程。
