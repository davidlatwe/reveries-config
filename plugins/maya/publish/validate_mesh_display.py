import pyblish.api
from maya import cmds


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "failed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        cmds.select(plugin.invalid)


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
        SelectInvalid,
    ]

    invalid = []

    def process(self, instance):

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
                self.invalid.append(node)

        if self.invalid:
            self.log.error(
                "'%s' has hidden shapes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in self.invalid))
            )
            raise Exception("%s <Hidden Shape> Failed." % instance)

        self.log.info("%s <Hidden Shape> Passed." % instance)
