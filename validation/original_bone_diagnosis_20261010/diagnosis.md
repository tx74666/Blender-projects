# Original bone 回匯差異：只讀診斷

日期：2026-10-10。執行中的 Blender：5.2.0 LTS；檔案：`D:\Blender\Projects\Character\X\X.blend`。

比對對象是 `Scene` 的 `CoshaRig`／`Cosha`，及 `Animation Worklist · Cosha` 的 `CoshaRig.001`／`Cosha.001`。原場景 frame 46、沒有作用中的 Action；回匯場景 frame 1、Action 為 `Cosha · Walk_N · Custom`。兩者沒有在同一姿勢下比較。

回匯 rig 的 animation-link 指向 `D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha\Cosha.fbx`。磁碟檔案 SHA-256 與回匯記錄一致：`2ae2067c9794fc7767f6abb35b6af33df496986a006c870fc9d0dc47eaa55db5`。

## 眼骨：骨尾長度在 FBX 匯入時重建

- 原版左右眼骨長度約 0.055473；回匯版約 0.177794，約為原版 3.205 倍。
- 回匯眼骨長度等於回匯 Head 長度；左側完全相同，右側差約 2.98e-8。
- 眼骨局部起點差異不超過 1.12e-8；Rest matrix 最大元素差異約 1.43e-6，方向也幾乎一致。眼骨局部 pose 接近單位矩陣，scale 接近 1。
- Blender 本機 FBX importer `D:\Blender5.2\5.2\scripts\addons_core\io_scene_fbx\import_fbx.py` 第 2672–2705 行會以子骨起點距離估計骨長，沒有子骨時沿用父骨估計長度，再建立 bone tail。這與本模型的眼骨變化吻合。

因此眼骨變長是末端骨尾重建的結果；不是眼睛關節起點移動或眼骨縮放變大。這解釋了使用者沒有手動修改骨頭，回匯後骨形仍會改變。

## 拇指：末端骨尾縮短，當前指尖網格沒有被拉長

- 左右 thumb.01／02／03 全部存在，父子關係一致，有效變形權重存在。關節起點最大差約 8.4e-7，Rest matrix 最大元素差約 3.85e-6。
- thumb.01／02 骨尾幾乎一致；thumb.03 長度約由 0.0383235 變為 0.0314386，縮短約 18%。這是末端骨尾重建，不是關節位置拉長。
- 回匯網格的指尖原始位置也沒有變長。相對於 thumb.03 Rest frame 的最遠軸向位置，原版約 0.043549，回匯版約 0.042799。
- 當前 frame 1，左右各 63 個 thumb.03 權重為 1 的指尖頂點轉回 posed bone local，軸向最遠位置分別為 0.042798799／0.042798710。相對 raw rest 的比例為 0.99999511／0.99999953；局部位置誤差最高 4.03e-7，符合剛體旋轉與平移。
- 728 個拇指相關頂點沒有缺骨或未綁定頂點；578 個混合權重頂點的 evaluated 結果符合獨立線性蒙皮計算，最大差異 3.80e-7。
- 18 條 location 與 18 條 scale 曲線各有 59 個 keys。已記錄 location 值偏離 0 最多 7.15e-7，scale 值偏離 1 最多 9.54e-7；沒有 NLA tracks。當前作用中的原版 Forearm `.002` shape keys 在拇指區的位移小於 9.44e-8。

確認的原因是末節骨頭顯示較短，且兩個場景使用不同拇指旋轉姿勢。這能解釋網格看起來超出骨頭較多；當前證據不支持缺骨、權重遺失或指尖被縮放拉長。截圖中的整体外觀歸因仍是依這些差異作出的判斷，沒有以相同視角與相同姿勢重拍截圖。

限制：evaluated 網格驗證對應當前 frame 1；沒有逐幀檢查完整動畫或曲線插值過衝。

## 操作與證據

沒有套用 Refine、修改 Rest／Pose、改權重、修改插件程式或保存 artist blend。檔案在開始和結束時均已有未保存變更。Scene、frame、active object、selection 保持相同；Properties 回到原本 DATA context。本次開啟的本機 BlenderMCP 連線已正常停止，9876 沒有監聽程序。

- `live_readonly.json`：兩個 rig、網格原始資料與當前姿勢快照。
- `evaluated_readonly.json`：當前動畫幀的 evaluated rig／mesh、動畫曲線與 shape-key 差異。
- `animation_link_readonly.json`：回匯來源連結。
- `thumb_snapshot_analysis.json`：原始拇指資料離線比對。
- `inspection_end_state.json`：結束時 UI／連線狀態。
