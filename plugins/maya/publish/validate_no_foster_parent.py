
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction
from reveries.plugins import context_process


class SelectFosterParent(MayaSelectInvalidInstanceAction):

    label = "選取 fosterParent"


class ValidateNoFosterParent(pyblish.api.InstancePlugin):
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
        "reveries.look",
        "reveries.xgen",
        "reveries.mayashare",
    ]
    actions = [
        pyblish.api.Category("選取"),
        SelectFosterParent,
    ]

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds
        return cmds.ls(type="fosterParent")

    @context_process
    def process(self, context):
        from maya import cmds
        invalid = self.get_invalid(context)
        if invalid:
            for node in invalid:
                if not cmds.referenceQuery(node, isNodeReferenced=True):
                    raise Exception("Found 'fosterParent' nodes.")
            else:
                self.log.warning("Found 'fosterParent' nodes in reference.")
