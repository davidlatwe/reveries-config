
import pyblish.api
from reveries import plugins


class SelectUnknownNodes(plugins.MayaSelectInvalidContextAction):

    label = "Select Unknown"


class ValidateNoUnknownNodesReferenced(pyblish.api.InstancePlugin):
    """Please not publishing when unknown nodes have been referenced
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
        "reveries.rsproxy",
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

    @plugins.context_process
    def process(self, context):
        unknown = self.get_invalid(context)

        if unknown:
            self.log.warning("Scene referenced unknown nodes.")
