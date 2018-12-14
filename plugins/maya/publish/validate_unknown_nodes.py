
import pyblish.api
from maya import cmds


class SelectUnknownNodes(pyblish.api.Action):

    on = "failed"
    label = "Select Unknown"
    icon = "search"

    def process(self, context, plugin):
        cmds.select(cmds.ls(type="unknown"))


class ValidateUnknownNodes(pyblish.api.ContextPlugin):

    order = pyblish.api.ValidatorOrder - 0.1
    label = "No Unknown Nodes"
    host = ["maya"]
    families = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectUnknownNodes,
    ]

    def process(self, context):
        unknown = cmds.ls(type="unknown")

        for node in unknown:
            self.log.error(node)

        if unknown:
            raise Exception("Scene contain unknown nodes.")
