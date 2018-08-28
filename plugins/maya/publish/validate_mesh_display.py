
import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidAction


class ValidateShapeDisplay(pyblish.api.InstancePlugin):
    """All geometry must be a visible mesh shape

    This ensures all model shape node is not hidden.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.4
    hosts = ["maya"]
    label = "Hidden Shape"
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
    ]

    @staticmethod
    def get_invalid(instance):

        from maya import cmds

        invalid = list()

        display_attrs = {
            ".visibility": True,
            ".lodVisibility": True,
            ".template": False,
            ".hideOnPlayback": False,
            ".intermediateObject": False,
            ".hiddenInOutliner": False,
            ".ghosting": False
        }

        for node in instance:
            if not cmds.nodeType(node) == "mesh":
                continue
            # Ensure mesh shape is not hidden
            not_hidden = (
                all([cmds.getAttr(node + attr) is display_attrs[attr]
                    for attr in display_attrs.keys()])
            )

            if not not_hidden:
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' has hidden shapes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Hidden Shape> Failed." % instance)

        self.log.info("%s <Hidden Shape> Passed." % instance)
