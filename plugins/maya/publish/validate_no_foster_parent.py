
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectFosterParent(MayaSelectInvalidInstanceAction):

    label = "選取 fosterParent"


class ValidateNoFosterParent(pyblish.api.ContextPlugin):
    """不可以有 fosterParent 存在

    Publish model，rig 的時候，場景不可以有任何 fosterParent 的殘留，如果有的話，
    請修正或直接刪除它。

    通常會出現 fosterParent 是因為 reference 遺失，如果確定是不會再使用的資源，可
    以安心的直接刪除。

    """
    """No fosterParent node in scene

    Should not contain any fosterParent node in scene. If so, please reslove
    the referencing issue or just delete it if not used.

    """

    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya"]
    label = "No Foster Parent"
    families = [
        "reveries.model",
        "reveries.rig",
    ]
    actions = [
        pyblish.api.Category("選取"),
        SelectFosterParent,
    ]

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds
        return cmds.ls(type="fosterParent")

    def process(self, context):
        if self.get_invalid(context):
            raise Exception("Found 'fosterParent' nodes.")
