
import pyblish.api
from reveries import plugins


class SelectInvalid(plugins.MayaSelectInvalidInstanceAction):

    label = "Invalid Description"


class ValidateXGenNoFrozenSpline(pyblish.api.InstancePlugin):
    """No frozen spline in XGen Interactive Groom

    XGen Interactive Groom should not publish with frozen spline,
    please defreeze them.

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "XGen No Frozen Spline"
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
            if cmds.xgmSplineQuery(description, frozenSplineCount=True) > 0:
                invalid.append(description)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Description has frozen spline.")
