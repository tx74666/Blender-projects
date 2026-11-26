# 目前 Blender 網格：新修復與驗收方案

2026-11-11。狀態：**方案已準備，尚未實作新拓撲接收或替換正式 Unity 資產。**

本輪依使用者選擇，以目前 Blender 的網格與權重為新基準。Blender 0.77.191 的骨骼顯示修復已正式安裝：174 根頭髮骨骼與左右腿腳控制器已恢復顯示、可選，作者資料與目前姿勢保留。

## 資料範圍

下表是 FBX 控制點數，不是 Unity 拆分 UV／法線後的頂點數；索引不同不代表已證明同一個實體頂點的權重改變。

| 部件 | Unity 舊來源 → 目前來源 | 本方案的處理 |
| --- | ---: | --- |
| Body／Cosha | 14374 → 13134 | 以目前 Blender 幾何、權重準備新修復，配套重建當前校準的 Unity Forearm 資料。 |
| Shoes | 38316 → 25362 | 以目前幾何、權重準備新修復，驗證雙側腳跟、腳尖及鞋底。 |
| Stocking | 1967 → 1603 | 以目前幾何、權重準備新修復，驗證膝踝變形與鞋襪交界。 |
| Clothes | 2525 → 2457 | 額外發現真實拓撲與權重陣列差異；列入實作前的明確審閱項目。 |
| Hair | 5463 → 5463 | Polygon 索引、UV 相同；另有 10 個面的材質索引改變，與骨骼分段更新分開審閱。 |
| Dress | 3040 → 3040 | 已核對拓撲、UV、材質、共同非空權重相同；仍需原生綁定與物理驗收。 |

完整骨架仍採目前 Rig：263 根匯出骨骼、32 條頭髮鏈共 174 根骨骼；保留已審閱的左右 thigh／shin Rest 四項變動，前臂左右修正最終均為關閉。

## 執行順序與通過條件

1. **鎖定目前來源。** 正常 Finish 後確認真實繪製狀態為 None，重新核對目前網格、權重、形態鍵與既有校準；另做尚未執行的唯讀 current ARM graph 驗證。來源若改變，產生新封存匯出與新證據，不改寫舊檔雜湊。
2. **建立全新私有驗收版。** 舊 Unity 三個已驗收網格、匹配的 Forearm、原始資料與整套可回退版本完整保留。新輸出採新 UUID／修訂，不以舊頂點索引搬運權重、stencil 或校準；不自動重塗、正規化或重採集校準。
3. **按目前 Blender 逐項驗收。** 比對新原生網格的拓撲、UV、材質、形態鍵、骨骼路徑與具名權重。檢查身體接縫、肩肘腕、膝踝、雙側 IK／FK、腳跟腳尖、鞋襪交界及衣物貼合。發現缺陷先列出具體差異與修復項，不套用舊網格資料掩蓋問題。
4. **驗收物理與交易。** 重建所有受新網格影響的初始化資料與快取，保留已儲存的參數、碰撞器與引用意圖。實際驗證 Hair 174／32 及其他受影響的 solver；做真實 Play、分階段故障回退、檔案與載入狀態復原、原有缺失 Dress 引用保護及本任務快取清理。
5. **審閱實際新輸出後才正式同步。** 新的「已審閱拓撲替換」契約須逐項綁定全部改動、來源／舊版／新輸出雜湊及原生證據。舊 generic／Hair-only 保護保持嚴格。正式提交需一次續接新骨架、網格、Forearm、Avatar、物理與 ledger，避免新舊資料混用；完整舊版本保留回退。

## 前臂的具體邊界

目前已儲存的 Blender 校準屬於 **3324 原始頂點 → 13134 匯出控制點**，不能因舊 Unity 網格較大就判定需要重採集。已有來源證據包含每側 135 個支援頂點、匯出每側 16 個有界樣本、合計 32 個樣本與 296 個 stencil；既有 bake 誤差為 9.49e-8 m，低於原先 3e-6 m 門檻。

新 Unity 資料必須來自目前 authored companion，且證明新網格的 ID／UV seam、骨骼、權重與配對 fingerprint 正確。本輪驗收左右關閉、校準可回讀及沒有額外修正輸出。Blender 連續 sampler 與匯出有界 sampler 的開啟效果一致性尚未證明；不在本輪靜默改演算法或宣稱 On 模式已驗收。

## 目前成果與未完成工作

- 已完成：0.77.191 顯示修復、差異診斷與此方案。正式 Unity 舊資產與 ledger 保持原樣。
- 待執行：新拓撲接收契約、私有新修復、原生姿勢／物理／Play／回退驗收與最後正式替換。
- Exporter 0.77.192 仍為私有候選；Finish／保留狀態保護已通過 13 類原生測試，尚未正式發布、安裝或啟用 Unity 能力。
- Unity 的 Adventure 仍有未保存內容。正式替換前須另安排獲准的安全場景窗口；此方案階段不儲存、關閉或切換它。

## 證據與交接

- [使用者資料權威選擇](</D:/Blender/Projects/Character/X/validation/rig_export_diagnosis_20261111/current_blender_mesh_plan_decision01.json>)：目前 Blender、先準備方案。
- [五階段技術概覽與 Forearm 補充](</D:/Unity Projects/RandomRealm2/.codex/task-staging/character-hair-structure-20261111/reviewed-topology-replacement01/REVIEW_BRIEF.md>)，SHA `dca678b95b5068894ed6b06181334afe9d92d2ea1ef861c0b60e3f5ecaddb8b9`。
- [完整資產／來源權威表、步驟與停止條件](</D:/Unity Projects/RandomRealm2/.codex/task-staging/character-hair-structure-20261111/reviewed-topology-replacement01/PLAN.md>)，SHA `b98b9bc4b36b227a6a77263c3ba4e865851b51a9dc7431092368593fb6f2ca38`。
- [目前校準資料閉合證據](</D:/Blender/Projects/Character/X/validation/rig_export_diagnosis_20261111/production_provider01/current_mesh_forearm_closure01.json>)，SHA `034b6ebc24b4df2418c53108772adca96d1c1971cf220419ed8ecaec139d9a6b`。完整 current ARM graph 仍是後續前置驗證。

目前 sealed source definition 為 `04fa5751628ef558db82b5f1c1638cd1b8c79734c7ed1949291f76ef4a7cf331`；實際完整 FBX 為 `46931750a3e8b9dfc60e982dc4b171cad8960233e4148743b80e61ff4572a18b`。它們是準備來源，不是正式替換的驗收通行證。
