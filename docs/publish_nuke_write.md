
# Publishing Write Node

可以將現有的 Write Node 使用 Pyblish 輸出序列圖，並以 Read Node 或 Precomp 的形式載回來繼續作業。

Write Node 在 Publish 的時候會將其上的節點樹另存一份 Nuke Script 備份，因此在 Publish 完成之後除了可以將輸出的序列以 Read Node 載入，也可以用 Precomp Node 的方式載入。

---

### 發布步驟

1. 使用 [Creator](avalon_tool_creator.md) 並選取 `Write` 以建立新的 Write Node 或使用現有的 Write Node

    * 若選取的節點裡面有先前創建的 Write Node，那會將它變成可被 Publish 的 Write Node
    * 若選取的節點裡面沒有 Write Node，則會創建一個新的可 Publish 的 Write Node

    可 Publish 的 Write Node 會有一個 Avalon 的屬性頁面，如下圖
    ![image](https://user-images.githubusercontent.com/3357009/74134022-b5bfc900-4c24-11ea-8014-c36f834d97ba.png)

2. 至 Avalon 選單打開 Publish 或者 Deadline Publish，開始進行驗證與發佈。

    若選 Publish，則會在本機進行 Render，反之則會送到 Deadline 進行。

