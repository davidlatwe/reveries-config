
import pyblish.api
import avalon.api


class ValidateAssetSession(pyblish.api.InstancePlugin):
    """確認當前正在發佈的物件與當前的工作空間設定是同一個 Asset

    正在被發佈的物件 (Subset Instance) 所標記的 Asset 名稱需要與工作區
    所屬的 Asset 一致。 也就是說，你/妳不可以在 Asset A 的工作區下發佈
    Asset B 的內容。

    這個檢查經常在切換工作區之後發生錯誤，這時候如果工作區確認無誤，那就
    請用　Creator 重新打包需要發佈的物件，或者直接修改標記其中的 Asset
    名稱。

    """

    """Only the asset which assigned to this task can be published

    The asset to be published should be the same as the asset of the
    task (current workspace).
    For example, if you are in the task of the asset *Boy*, you can
    not publish asset *Girl* in current session.

    """

    label = "正確的 Asset"
    order = pyblish.api.ValidatorOrder - 0.45

    def process(self, instance):
        from avalon import io

        asset = instance.data["asset"]
        task_asset = avalon.api.Session["AVALON_ASSET"]

        if not asset == task_asset:

            if instance.data.get("assetConfirmed"):
                self.log.warning("Publishing asset that is not in current "
                                 "session.")

                if not io.find_one({"type": "asset", "name": asset}):
                    msg = "Asset name not exists in database."
                    self.log.error(msg)
                    raise AssertionError(msg)

            else:
                msg = ("Instance {name!r} has been set to be as part of "
                       "Asset: {asset!r}, but the current publish session "
                       "is Asset: {task_asset!r}. "
                       "Please check Context Manager."
                       "".format(name=str(instance.data["name"]),
                                 asset=str(asset),
                                 task_asset=str(task_asset)))
                self.log.error(msg)
                raise AssertionError(msg)
