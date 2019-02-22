
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Invalid Description"


class ValidateXGenNoLinearWire(pyblish.api.InstancePlugin):
    """No linear wire modifier in XGen Interactive Groom

    XGen Interactive Groom should not publish with linear wire modifier,
    please delete them.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen No Linear Wire Modifier"
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
            if cmds.ls(cmds.listHistory(description),
                       type="xgmModifierLinearWire"):
                invalid.append(description)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Description has linear wire modifier.")
