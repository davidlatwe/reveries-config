
![avalon-logo](https://raw.githubusercontent.com/getavalon/core/master/res/icons/png/avalon-logo-48.png)

## 起手式

首先請先在桌面上找到如上圖的捷徑，那是 Avalon Launcher，請用滑鼠雙擊以啟動並進入系統。
若一切正常，就會出現一個視窗列出當前所有的專案。

!!! note
    視當下的公司內部網路流量狀況，啟動所需的時間大約從 1 秒到 10 秒不等，超過 30 秒是不能被接受的，務必舉手。

!!! help
    如果不確定自己的機器是否已安裝或者啟動有問題，請舉手。


## 系統概念

既然已經確認了系統是否能夠正常啟動，現在就先來抽象的看一下整個系統的脈動及其中的概念。

![avalon-dataflow](https://user-images.githubusercontent.com/3357009/66933688-04d96100-f06c-11e9-8b94-374b0256b503.png)

每一個 Asset 都在這樣的循環中，`創作/加工 > 發布 > 保存 > 載入 > 創作/加工` ..
每一次的循環都在生成新的內容，在過程中堆疊了許多版本，各種不同類型的資料。

!!! example
    `Modeler 建模 > 模型發布 > 模型檔保存於網路硬碟 > Rigger 將模型載入場景 > 綁骨架 > 發布` ..

(待續)
