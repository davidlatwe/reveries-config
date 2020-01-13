
![creator](https://user-images.githubusercontent.com/3357009/72150034-862c5f80-33df-11ea-80d2-a75699d90431.png)

## Features

在場景內創建 Subset 實體的工具，是 Publish 之前務必進行的工作。

### Family

Subset 資料屬性列表。要 publish 什麼類型的檔案就選什麼項目。

### Asset

Asset 名稱，這個欄位會自動依照當前工作環境去填寫，通常不需要修改。

### Subset

Subset 名稱，預設是 `Default`，通常保留 `Default` 即可，但如果有特別用途，請依照用途去命名。

!!! example
    * 假設現在是輸出模型，如果有需要區分高低模，那就得依照狀況改取 `HighPoly` 或 `LowPoly`。

!!! hint
    如果目前這個 Asset 在 Loader 上面已經有相同名稱的 Subset ，那麼這次的 publish 就是會在它之上新增版本。如果沒有，則會建立新的 Subset。

### Create

確認名稱沒問題之後，按下 `Create` 按鈕即可。
