# 頭髮骨骼 A/B 比較 — Character Designer 0.40.0

這兩份檔案使用同一片 Hair2 的六束頭髮，每條鏈三根髮骨。

- `X-Hair-A-Per-Strand.blend`：逐束模式，六條鏈、18 根髮骨。
- `X-Hair-B-Grouped.blend`：分組模式，每三束共用一條鏈，共兩條鏈、6 根髮骨；檔案也保留隱藏的 A 版本。
- 每個版本另有一根頭部跟隨骨，不計入上述髮骨數。
- `Hair-A-vs-B.png`：同視角、同比例的骨骼配置對比。

開啟檔案後，選取生成的頭髮骨架，在 Pose Mode 旋轉髮骨即可比較；兩版都跟隨原角色的 Head 骨骼。檔案以靜止姿態保存，沒有加入自動頭髮物理。

在 Character Designer → Hair → Hair Bones：先回到原始頭髮的 Edit Mode，選取髮束並使用 Select Hair Strands 保存劃分。Per Strand 每束生成一條鏈；Grouped 可選取多束合組、把選中髮束拆出，並透過 Edit Guide 調整每組的骨鏈路徑。Generate New Version 每次建立獨立的網格與骨架，原模型及舊版手修權重、關鍵幀保留。Show Version / Edit Source 用於切換結果與原始劃分。

已驗證：六束 18 / 6 根配置；Hair1、Hair2、Hair3 的頭部跟隨與彎曲；合組及拆组；修改引導線後立即生成；切換版本；保留既有權重及動畫；保存重開；原始幾何與主骨架保留。最終版本的綁定位置誤差小於 0.000001 公尺。

安裝版 0.40.0 已在目前 X 視窗刷新，新 Blender 進程也從已保存的使用者偏好成功自動載入。這些比較結果保存於獨立檔案，未將測試綁定寫入生產用 X.blend。
