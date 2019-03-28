
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectFosterParent(MayaSelectInvalidInstanceAction):

    label = "Select Foster Parent"


class ValidateNoFosterParent(pyblish.api.InstancePlugin):
    """No fosterParent node in hierarchy

    Should not contain any fosterParent node in DAG hierarchy. If so,
    please reslove the referencing issue or just delete it if not used.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "No Foster Parent"
    families = [
        "reveries.model",
        "reveries.rig",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectFosterParent,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        return cmds.ls(instance, type="fosterParent")

    def process(self, instance):
        if self.get_invalid(instance):
            raise Exception("Found 'fosterParent' nodes.")
