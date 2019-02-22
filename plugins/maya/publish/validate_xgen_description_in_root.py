
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Invalid Description"


class ValidateXGenDescriptionInRoot(pyblish.api.InstancePlugin):
    """XGen description nodes should be in root (parented to world)

    XGen Interactive Groom description node should not be parented to
    any other nodes.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen Description In Root"
    families = [
        "reveries.xgen.interactive",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        for description in instance.data["igsDescriptions"]:
            transform = cmds.listRelatives(description, parent=True)[0]
            # Should not have parent
            if cmds.listRelatives(transform, parent=True):
                invalid.append(description)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Description not parented to world, this is not "
                            "okay.")
