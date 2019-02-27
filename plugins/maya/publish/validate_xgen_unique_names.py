
import pyblish.api


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

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        for palette in instance.data["xgenPalettes"]:
            for node in cmds.ls(palette, long=True):
                if not cmds.nodeType(node) == "xgmPalette":
                    invalid.append(node)

        for desc in instance.data["xgenDescriptions"]:
            for node in cmds.ls(desc, long=True):
                shapes = cmds.listRelatives(node,
                                            shapes=True,
                                            fullPath=True) or []
                if not shapes:
                    invalid.append(node)

                for shape in shapes:
                    if not cmds.nodeType(shape) == "xgmDescription":
                        invalid.append(node)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("These nodes has named after one of XGen nodes, "
                            "please rename or delete them.")
