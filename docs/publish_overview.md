
![pyblish-logo](https://pyblish.com/images/logo_macaw_extrasmall.png)

## Pyblish

![image](https://user-images.githubusercontent.com/3357009/67102701-80671980-f1f6-11e9-8989-9329cce6fee6.png)

我們搭配的發佈工具視窗介面是一個叫做 [pyblish-qml](https://github.com/pyblish/pyblish-qml) 的開源工具，以下介紹使用方式。

## 介面說明

### 主介面
![image](https://user-images.githubusercontent.com/3357009/67102653-688f9580-f1f6-11e9-9588-9129654639b6.png)

#### Family, Subset

左側 <font color="green">(綠色區塊)</font> 列出的物件是從場景收集到要 publish 的 Subset，並且依照所屬的 Family 做分類。
物件左邊的方塊是可以開關的。

#### Plugin

右側 <font color=#EDCD1C>(黃色區塊)</font> 列出的是 Publish 過程中需要執行的項目 (Plugin)，而 publish 的過程總共有四個階段

|階段|目的|
|--:|--|
|Collect (收集)| 收集場景資料，啟動時自動執行|
|Validate (驗證)| 執行各項資料檢查，按下發佈或驗證按鈕時執行|
|Extract (輸出)| 開始執行檔案輸出，驗證通過之後才會執行|
|Integrate (上傳)| 上傳到資料庫，驗證通過才會執行|

!!! bug
    除了驗證，其他階段不該見紅，如果有的話很有可能是 Bug，務必舉手。

#### Action

有些項目會有上圖<font color="#368CDE">被藍色圓點標記</font>的小按鈕 (Action)，大部分是出現錯誤時才會出現。對著按鈕右鍵點擊會出現浮動選單，可從上面提供的選項來輔助驗證除錯。

### 事件紀錄

每個項目 (Plugin) 右邊都有一個 `>` 的按鈕 <font color="#DD3355">(上面主視窗紅色圓形區)</font>，點按會切換到事件紀錄頁面，如下圖。

![image](https://user-images.githubusercontent.com/3357009/67090748-81d81800-f1dd-11e9-8bec-f33675167069.png)

#### Info, Documentation

頁面最上方顯示的是項目名稱，以及執行時間，上方第二個區塊則是該項目的說明文字。

#### Errors

錯誤列表 <font color="#368CDE">(藍色區塊)</font>，執行時的錯誤會顯示在這邊，被<font color=#EDCD1C>黃色圓點標記</font>的那個小三角形展開可以顯示錯誤資訊的細節。**驗證除錯時，請務必閱讀這邊的訊息。**

!!! tip
    回報錯誤時，請務必一併提供這個區塊的資訊。

#### Records

事件列表 <font color="#3CC683">(綠色區塊)</font>，所有的訊息都會記錄在這邊，有時會拿來檢視執行過程是否正常。但通常不需要特別在意，是除錯時的第二線索。

