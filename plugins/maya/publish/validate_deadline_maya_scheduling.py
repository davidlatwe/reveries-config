
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Invalid Instance"


class ValidateDeadlineMayaScheduling(pyblish.api.InstancePlugin):

    label = "Deadline Scheduling"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]

    targets = ["deadline"]

    families = [
        "reveries.pointcache",
        "reveries.standin",
        "reveries.renderlayer",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        cls.log.debug("Selecting %s" % instance.data["objectName"])
        return [instance.data["objectName"]]

    def process(self, instance):

        priority_limit = 80
        priority = instance.data["deadlinePriority"]
        assert priority <= priority_limit, ("Deadline priority should not be "
                                            "greater than %d."
                                            "" % priority_limit)

        pool = instance.data["deadlinePool"]
        assert not pool == "none", ("Deadline pool did not set.")
