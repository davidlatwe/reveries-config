
# Publishing Render

Maya Lighting 與 Nuke compositing 工作銜接的必要流程。

---

## 注意事項

Maya renderLayer 可以有多個 renderable cameras，而每個 camera 都會產出一段序列圖，所以在 publish render 的時候會確保每個 layer-camera 的組合都有獨立的路徑 (file name prefix)。

例如 `<scene>/<camera>/<scene>_<renderLayer>`，(Arnold 的話可能會多一個 `<RenderPass>` 的標籤以區隔 AOV)，見下圖

![image](https://user-images.githubusercontent.com/3357009/72252789-fb47a100-363a-11ea-9bb5-10c946c462ad.png)


Deadline Job 也會以一層 RenderLayer 配一顆 Camera 為一組，然後會有另一個 Job 是 Publish Job，名稱會以 "|| Publish: " 為開頭，如下圖

![deadlinejobs](https://user-images.githubusercontent.com/3357009/72244912-3f7e7580-362a-11ea-872b-f425a086a6b4.png)

!!! Danger
    Publish Job 會在與它相對應的 renderLayer Job 完成之後自動開始，**Publish Job 必須要完成才會在 Loader 上看到算完的圖檔**。

    **請勿刪除 Publish Job 或對它進行任何更動。**


## 發佈步驟

!!! warning
    由於**新版 (2020.01.13 開始) 的 Render publish 流程與舊版並不相容**，所以若要繼續從舊場景 publish render 的話會有問題，請先將舊的 publish 節點 (`imgseqRender`) 刪除，然後再開始進行下面的新流程步驟。

1. 請先確認場景裡面有 `renderglobalsDefault` 這個 `objectSet` 節點，如下圖

    ![renderglobalsDefault](https://user-images.githubusercontent.com/3357009/72150219-fc30c680-33df-11ea-85f5-28e77b1cd826.png)

2. 如果沒有，請打開 [Creator](avalon_tool_creator.md) 並選取 `Render`，只要確認 Asset 名稱沒問題後，直接按下 `Create`。

    ![CreateRender](https://user-images.githubusercontent.com/3357009/72150076-a5c38800-33df-11ea-99a2-5009cf6796aa.png)

    !!! note
        舊流程會需要在先選取算圖攝影機，但新版本已經不需要了，所以只需要確認 `renderglobalsDefault` 這個紅色三角形節點有存在就好囉。

3. 至 Avalon 選單打開 Deadline Publish，開始進行驗證與發佈。

    ![publishDeadline](https://user-images.githubusercontent.com/3357009/72244587-920b6200-3629-11ea-85e8-41a04c38ec3d.png)


## 檢查項目

(待續..)
