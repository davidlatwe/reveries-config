
import pyblish.api
from reveries.plugins import context_process
from reveries.maya.plugins import MayaSelectInvalidContextAction


class SelectUnknownNodes(MayaSelectInvalidContextAction):

    label = "Select Unknown"


class ValidateNoUnknownNodesReferenced(pyblish.api.InstancePlugin):
    """Can not publish with unknown nodes referenced
    """

    order = pyblish.api.ValidatorOrder - 0.1
    label = "No Unknown Nodes Referenced"
    host = ["maya"]
    families = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
        "reveries.xgen",
        "reveries.camera",
        "reveries.mayashare",
        "reveries.standin",
        "reveries.lightset",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectUnknownNodes,
    ]

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds
        return [node for node in cmds.ls(type="unknown")
                if cmds.referenceQuery(node, isNodeReferenced=True)]

    @context_process
    def process(self, context):
        unknown = self.get_invalid(context)

        for node in unknown:
            self.log.error(node)

        if unknown:
            raise Exception("Scene referenced unknown nodes.")
