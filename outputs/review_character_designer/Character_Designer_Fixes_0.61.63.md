# Character Designer 0.61.63 修正記錄

2026-09-26：整體健檢發現的六項問題已處理，已建立本機安裝包並部署。角色場景未存回；Git 變更尚未提交或推送。

| 問題 | 現在行為 |
|---|---|
| 拓撲鏡像丟失 Shape Key 動畫／drivers | Mirror 與 Repair 在規劃和套用前檢查；遇到目前不支援的動畫資料會拒絕操作，保留原資料。這次沒有新增帶動畫拓撲重建能力。 |
| 拓撲鏡像丟失表面屬性 | 保留銳邊、seams、crease／bevel 權重及自訂法線；來源、鏡射結果、未編輯區域均有驗證。失敗回滾後清除暫存 Mesh。 |
| 前臂無變動仍重做昂貴驗證 | 以精確 bulk fingerprint 快取拓撲和鏡像對應；同次更新的完整 rig 驗證由四遍減為一遍。保留直接資料修改、Undo、載入、停用的處理。 |
| 骨骼改名後恢復綁定錯誤 | 無法確認原骨骼／群組對應時拒絕恢復，保留當前變形與完整備份；恢復名稱後仍可正常還原。 |
| 同批相依 Shape Keys 清不乾淨 | 使用本批次完成後的最終基準，拒絕循環與過期計畫；首次清除的殘留與 evaluated 位移為 0，第二次不再改動。 |
| 無關缺檔貼圖阻止 Unity 匯出 | 追蹤有效材質輸出的實際依賴，包含巢狀群組；未使用的貼圖不再阻擋，必要貼圖缺檔仍會報錯。 |

**性能驗證**

同一真實歷史角色 `X_forearm_ranges_0555_preview.blend`，Blender 5.2 背景程序；每組 3 次暖機、7 次取樣。

| 狀態 | 修正前中位數 | 修正後中位數 |
|---|---:|---:|
| Enabled，輸入未變 | 268.34 ms | 18.56 ms |
| Disabled，輸入未變 | 236.40 ms | 19.65 ms |

Enabled 約快 14.5 倍。這是 handler 耗時，並非 GUI FPS；每次仍有精確資料讀取及一次完整 rig 驗證。當前 X.blend 沒有該校準記錄，因此這組數據不代表它原本的卡頓程度。

[實測結果](D:/Blender/Projects/Character/X/outputs/review_character_designer/performance_forearm_after.json)

**驗證**

通過：Character Designer 48、UI 4、Topology Mirror 7、新增 topology preservation 3、Mesh Mirror 14、Mirror normals 5、Quick Bind 9、binding removal 8、Shape Key 10、Unity worker 10、materials 4、export 5 項測試；另通過 7 個 forearm 測試腳本（含新增快取測試）、兩種插件載入／卸載順序、打包與部署範圍測試。新增保護測試包含動畫／driver／NLA、plan 後變動、失敗回滾、同數量拓撲變更和實際 evaluated 變形。

測試使用 Blender 5.2；未執行 Unity Player 或實測 GUI 幀率。Blender 4.0 的 ID 相容處理保留，但本次未在 4.0 執行驗證。

**交付**

- [本機安裝包](D:/MyRepository/Blender-addons-by-Randy/dist/character_designer-0.61.63.zip)
- 安裝目錄：`C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer`
- X 副本：`D:\Blender\Projects\Character\X\addons\character_designer`
- 兩處皆 104 個檔案，`deploy_local.py --check` 顯示差異 0。
- 部署備份：`C:\Users\Randy\AppData\Local\CodexBackups\addon-deploy\20260926-165547-29f8de88`
- 已開啟的 Blender 可透過 Character Designer 的 **Refresh Add-on** 載入更新；本次沒有重啟或操作正在使用的場景。

最初健檢的角色目標統一、動畫與 Body Setup 相容性等流程建議未納入這次六項缺陷修正，也未做全面架構重寫。共用程式庫中同時進行的 RR Helper 變更未納入本次打包／部署。
