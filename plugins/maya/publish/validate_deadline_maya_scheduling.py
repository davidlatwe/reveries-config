
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidAction


class SelectInvalid(MayaSelectInvalidAction):

    label = "Select Invalid Instance"


class ValidateDeadlineMayaScheduling(pyblish.api.InstancePlugin):

    label = "Deadline Scheduling"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    families = [
        "reveries.imgseq.batchrender",
        "reveries.imgseq.turntable",
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
        priority = instance.data["deadlinePriority"]
        pool = instance.data["deadlinePool"]

        self.log.info("Renderlayer: %s" % instance.data["renderlayer"])

        assert priority <= 80, ("Deadline priority should not greater than "
                                "80.")
        assert not pool == "none", ("Deadline pool did not set.")
