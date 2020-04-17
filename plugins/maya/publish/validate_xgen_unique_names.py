
import pyblish.api
from reveries import plugins


class SelectDuplicated(plugins.MayaSelectInvalidInstanceAction):

    label = "Select Duplicated"


class ValidateXGenUniqueNames(pyblish.api.InstancePlugin):
    """XGen nodes' short name must be unique name

    No other nodes in scene can have same name as any XGen legacy node.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen Unique Names"
    families = [
        "reveries.xgen.legacy",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectDuplicated,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya.xgen import legacy as xgen

        invalid = list()

        for palette in instance.data["xgenPalettes"]:
            nodes = cmds.ls(palette, long=True)
            nodes.remove(xgen.get_palette_long_name(palette))
            invalid += nodes

        for desc in instance.data["xgenDescriptions"]:
            nodes = cmds.ls(desc, long=True)
            nodes.remove(xgen.get_description_long_name(desc))
            invalid += nodes

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("These nodes has named after one of XGen nodes, "
                            "please rename or delete them.")
