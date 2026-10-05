# Dress exact-index delta overlay：只讀可行性與隔離邊界

日期：2026-10-05。狀態：**只讀研究；未實作、未跑 native、未改 canonical 或 Unity。**

目前任務仍是 all32 bone transfer diagnostic。本文僅保存一個備用方向，供下一步重新使用；不能作為完整目標、Shape Keys 效果、導出或 production 相容的驗收。

## 已有證據與待解問題

Actual800 Cloth 的 Body crossing 診斷遠少於 final32 bone skin；少量 Cloth crossing 集中在腰沿 ring0→1。單段 roll native 已證明參考方向可穩定傳出，四個取樣幀 actual800 與 old416 tracker 座標完全一致，但 final skin 的效果有改善也有惡化。

例如 frame25 raw395/399 的誤差分別由 18.092/22.651 mm 降至 7.162/11.517 mm；frame30 的全800點最大誤差卻由 21.566 mm 增至 25.540 mm。因此「physical Cloth 已有较好的碰撞結果」不能自動證明其32骨蒙皮近似也足夠。

本機證據：[單段比較 JSON](D:/Blender/Projects/Character/X/Validation/dress_automatic_20261005/one_segment_roll_51_20261005_071301_194/result/comparison_to_frozen_stretch.json)。Baseline 在部分幀只保存 worst16 的 raw skin 座標，不能補猜缺失頂點。四幀相等也不是全部中間幀逐值相等的證明。

## 候選公式與語義

所有位置先轉為最終輸出 object 的 local space，並使用完全相同的 raw vertex index `i`：

```text
S[i] = 現有 source 在 Armature 後、Subsurf 前的位置
C[i] = 獨立 actual800 Cloth 的 evaluated 位置；其輸入為固定 Basis
H[i] = 獨立 pure-physics skin helper 的 evaluated 位置；其輸入為固定 Basis

Automatic + 保留作者變形： O[i] = S[i] + (C[i] - H[i])
Manual：                  O[i] = S_manual[i]   （overlay 關閉，physics influence = 0）
```

第一式可寫為 `C + (S - H)`：把目前 Armature 結果相對 pure physics 的 manual、Original correction 與 Shape Key 差值加回 Cloth。

這不是既有第三個 runtime mode。現有 `skirt_motion_profiles.py` 的 `PHYSICS/MANUAL/BOTH` 是生成能力；runtime mode 只有 `AUTOMATIC/MANUAL`。目前 automatic 仍疊加 manual shaping，`physics_influence` 是 physics rotation driver 的來源。

若將 Physics 定義為**絕對等於 C**，就會抹去顯示中的 manual 和 Shape Key 差值。保留 Key 資料不等於保留 Key 效果；若要保留 Key，應明確使用上述差值語義，而不能同時聲稱所有頂點絕對等於固定 Basis Cloth。

第一個隔離試驗只允許 fully automatic 的 influence=1 與 manual 的 influence=0。`0<f<1` 的骨旋轉混合與座標差值插值不是同一種混合；未證明前不新增 Physics Blend 語義。

## Pure-physics helper 是必要的獨立輸入

現有 final DEF 包含 manual Spline IK、physics rotation 和已保存的 Original corrections，不能直接把同一份 final DEF skin 當作 H；這樣 `S-H` 會把需要保留的變形減掉。

H 必須有獨立、明確的 pure-physics 評估途徑，固定 Basis，並使用相同 Rest、raw topology、index、native weights、物件座標與 physics/Body/waist 時間輸入。不能每幀暫時 mute 原 Rig 的 manual/corrections 或修改原 Shape Key 值來取得 H。原 PHYS bones 本身 `use_deform=False`，也不能為了 helper 改原骨架的 deform flags。

如需 helper Rig，僅在 disposable QA 副本建立獨立資料與精確映射；其結果必須先驗證，不能以骨名相似或 nearest 推導對應。它不代表 production 應新增或替換原32個 final DEF。

在 neutral manual、Key=0 的測試中，S 與 H 應符合定義中的純物理一致性，才可宣稱 `O=C`。已有非零 Original correction 時應保留並明示為作者差值，不能把它偷偷歸零來做這個等式。

## 依賴回饋與座標空間

允許的單向關係是：上游 Body/waist/作者輸入 → actual Cloth → physics/helpers → final source overlay。以下情況必須拒絕：

- Cloth、Body collider、waist 或 H 讀取添加 overlay 後的 source geometry。
- 用 source 自己的 Object Info 取得「Armature 前一層」幾何；Object Info 讀取的是 object 的 evaluated geometry，不能作為 modifier stack 的上游抽頭。
- H 已含相同 overlay，或其 constraint/driver/control 經其他物件回到 source 輸出。
- 為了取得 baseline，暫時改作者 Rig、Key、Action、NLA、constraints、Rest 或 cache。

Blender 5.1 的 Object Info 原生實作拒絕讀取自身幾何，並對未完成求值的依賴循環回報錯誤。其 `RELATIVE` geometry 使用完整矩陣 `source.world_inverse × helper.world`，可把 C、H 直接帶到輸出 local space；不可再加一次 Root/parent transform。[官方 5.1 Object Info 原始碼](https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_object_info.cc)

如果先在 world space 相減，差值是 vector，只能用輸出 inverse 的線性3×3部分轉回；不能把差值當 point 再乘含 translation 的4×4矩陣。量測時的 metres-per-unit 也不能再混入 native position 計算。

## Keys、manual correction 與碰撞的實際限制

原 Shape Key datablock、相對關係、mask、value/mute、drivers、Actions 都應完全不寫。H 不可共享「活動 Key 的求值」；否則它會將 Key delta 一併減掉。獨立固定 Basis 資料需要從原 Basis 只讀複製，不能 clear 原 source 的 Keys。

當 C/H 不受 Key 或 manual 影響時，候選有可量測的關係：`O(Key)-O(Basis) = S(Key)-S(Basis)`，manual 的前後差值也同理。這仍需 native 測試至少一個局部、非對稱 Key，以及曲線 shaping 和 Original DEF correction；不能只凭資料 hash 推斷可見效果保留。

`skirt_original_mode.py` 將作者 DEF basis 保存為 native local correction，manual Copy Transforms 使用 `BEFORE_FULL`，physics Copy Rotation 使用 local `BEFORE`。骨旋轉、父 FULL scale/shear 的非交換關係仍在 S 中；vertex delta overlay 不是把控制骨搬到 Cloth 位置，也不修改這套 capture/leave 記錄。

此外，Cloth 的碰撞約束只作用於 C。加回 manual/Key 差值可能再次產生穿插、拉伸或摺疊；不能保證高級手動調整後仍保有 Cloth 的碰撞結果。原 Original/Controls 切換也只驗證 native bone matrices，不能代替最終 overlay mesh 的連續性與效果驗證。

## 最小 Geometry Nodes 邊界

只考慮 `ARMATURE → NODES(position-only) → 原 SUBSURF`。輸出 geometry 始終來自 Group Input；helper geometry 僅用於取位置，禁止 Join、重新建 mesh、刪點、nearest、重排或重建 UV/weights。

Sample Index 使用 Mesh Point domain、向量 Position 和原 Index；C/H/source 都必須證明相同800個頂點、原 index 與 connectivity。關閉 Clamp 並不自動拒絕錯配：原生節點對越界會返回預設值，因此 count/domain/映射證明不可省略。[官方 5.1 Sample Index 原始碼](https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_sample_index.cc)

Set Position 原生實作在 Point domain 寫 position 並傳遞輸入 geometry。這支持只做座標疊加的候選，但 UV、groups、weights、material/其他 attributes 和 loop/edge/face/index 的保持仍需 raw 與 evaluated 比較，不能只檢查頂點數。[官方 5.1 Set Position 原始碼](https://raw.githubusercontent.com/blender/blender/blender-v5.1-release/source/blender/nodes/geometry/nodes/node_geo_set_position.cc)

## 現有導出明確不支持

`unity_export_worker.py:175–185` 會比較開關每個 NODES modifier 的 geometry/weights；座標不同即拒絕，僅允許已驗證的 normal/attribute-only nodes。這個 overlay 正常工作時恰好會改座標，**不能放寬這個 guard 來宣稱問題已解決**。

Model exporter 還會先移除 temporary Armature 再逐 Key 求值；此時 overlay 的 S/H 語義也不能直接沿用。即便某個 Rest frame 的 offset 碰巧為0而通過，也不能證明之後動畫可導出。

`animation_export_worker.py` 只烘焙 skeleton motion，不導出 mesh、Shape Key animation 或 Cloth。骨動畫 FBX 無法表達每頂點、每幀的 overlay。Unity Magica 也沒有目前 Blender GN graph 的既有對應實作；本方向不能作為 Blender/Unity效果相等或現有export兼容的證明。

只讀程式入口：

- [Original correction/capture/leave](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt_original_mode.py)
- [Dress capability/runtime mode](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt_motion_profiles.py)
- [Native influence/mode交易](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt_motion_tuning.py)
- [Model export baker](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_export_worker.py:117)
- [Bones-only animation export](D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_export_worker.py:300)

## 允許下一次隔離效果驗證的最小條件

1. 仍用 factory/background 的 disposable artist 副本和既有原資產/file/code protection；不部署、不刷新 artist、不寫 Unity。
2. 固定 actual800 Basis、精確 raw index/weights/Rest 和同一份 QA Action；證明 C/H 不讀最終 overlay，Object Info 全部求值成功，沒有循環或預設值假成功。
3. 只在 QA source clone 新增一個 position-only GN 與獨立 H；原資料、manual controls、saved correction/ownership、Keys、UV、weights、final DEF 與 Action/NLA 不寫。
4. Native 核對 neutral 無跳；Manual pass-through；無 manual/Key 時的 C 關係；非對稱 Key 與兩種 manual shaping 的 delta 關係；以及最終 mesh 在同一組動態幀的有限值、碰撞/triangle crossing/摺疊與 render。
5. 每個結果明示「QA-only overlay、native compatibility pending、current export unsupported」。失敗清理/回滾檢查原資產，成功也只另存獨立候選。RAM Cloth cache 重開需逐幀 replay，不能當持久 bake。

結論：**可限定為一次 isolated position-only 效果研究；尚不是 production 方案。** 優先等待目前 all32 bone diagnostic 的結果，不以本文擴大現有任務或鬆動 export/ownership guard。
