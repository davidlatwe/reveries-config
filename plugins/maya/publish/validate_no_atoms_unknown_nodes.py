
import pyblish.api

from reveries.plugins import RepairContextAction, context_process
from reveries.maya.plugins import MayaSelectInvalidContextAction


class SelectUnknownNodes(MayaSelectInvalidContextAction):

    label = "Select Unknown"


class DeleteUnknownNodes(RepairContextAction):

    label = "Clean Up"


class ValidateNoAtomsUnknownNodes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "No Atoms Unknown Nodes"
    hosts = ["maya"]
    families = [
        "reveries.renderlayer",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectUnknownNodes,
        pyblish.api.Category("Fix It"),
        DeleteUnknownNodes,
    ]

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds

        invalid = list()

        for node in cmds.ls(type="unknown"):
            plugin = cmds.unknownNode(node, query=True, plugin=True)
            if plugin == "AtomsMaya":
                invalid.append(node)

        return invalid

    @context_process
    def process(self, context):
        unknown = self.get_invalid(context)

        for node in unknown:
            self.log.error(node)

        if unknown:
            raise Exception("Scene contain Atoms unknown nodes.")

    @classmethod
    def fix_invalid(cls, context):
        """Delete unknown nodes"""
        from maya import cmds
        cmds.delete(cls.get_invalid(context))
