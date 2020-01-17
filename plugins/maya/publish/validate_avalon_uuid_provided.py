
import pyblish.api
from reveries.maya.utils import Identifier, get_id_status
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectMissing(MayaSelectInvalidInstanceAction):

    label = "選取沒有編號的物件"


class ValidateAvalonUUIDProvided(pyblish.api.InstancePlugin):
    """上游物件要有編號 (AvalonID)

    需要被 cache 或 bake animation 的上游物件 (model 或 rig) 都要有編
    號，這是為了之後套材質 (look) 或者套動態 (animCurve) 時的資料配對。

    通常沒有被編號的物件都是沒有 publish 過的，所以如果這個驗證出現錯誤，
    請嘗試下面兩種方法 :

        1. 如果之後不需要套材質，請將 "isDummy" 選項開啟。
        2. 請先 publish 該上游物件

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "上游物件有編號"
    families = [
        "reveries.look",
        "reveries.animation",
        "reveries.pointcache",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        if instance.data.get("isDummy"):
            return []

        invalid = list()
        nodes = cmds.ls(instance.data["requireAvalonUUID"], long=True)
        for node in nodes:
            if get_id_status(node) == Identifier.Untracked:
                invalid.append(node)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception("發現沒有編號的上游物件。")
