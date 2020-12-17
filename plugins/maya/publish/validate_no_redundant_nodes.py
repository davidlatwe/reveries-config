
import pyblish.api
from reveries import plugins


class SelectUnknownNodes(plugins.MayaSelectInvalidContextAction):

    label = "Select Unknown"


class DeleteUnknownNodes(plugins.RepairContextAction):

    label = "Delete Unknown"


class ValidateNoRedundantNodes(pyblish.api.ContextPlugin):
    # redshift nodes

    order = pyblish.api.ValidatorOrder - 0.1
    label = "No Redundant Nodes"
    host = ["maya"]

    targets = ["deadline"]

    actions = [
        pyblish.api.Category("Select"),
        SelectUnknownNodes,
        pyblish.api.Category("Fix It"),
        DeleteUnknownNodes,
    ]

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds

        invalid = set()

        renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        if (renderer != "redshift"
                and cmds.pluginInfo("redshift4maya", q=True, loaded=True)):

            types = cmds.pluginInfo("redshift4maya", q=True, dependNode=True)
            redundant = cmds.ls(type=types)

            if redundant:
                invalid.update(redundant)
                cls.log.warning("Renderer is not redshift but scene contains "
                                "redshift nodes.")

        return list(invalid)

    def process(self, context):
        invalid = self.get_invalid(context)
        if invalid:
            raise Exception("Found redundant nodes, remove those nodes or "
                            "modify the scene before submit to Deadline.")

    @classmethod
    def fix_invalid(cls, context):
        """Delete unknown nodes"""
        from maya import cmds

        for node in cls.get_invalid(context):
            cmds.delete(node)
