
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Invalid Instance"


class ValidateDeadlineMayaScheduling(pyblish.api.InstancePlugin):

    label = "Deadline Scheduling"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    families = [
        "reveries.pointcache",
        "reveries.imgseq",
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

        if not instance.data["deadlineEnable"]:
            return

        priority = instance.data["deadlinePriority"]
        pool = instance.data["deadlinePool"]

        project = instance.context.data["projectDoc"]
        deadline = project["data"]["deadline"]["maya"]

        job_type = instance.data.get("renderType", "pointcache")
        priority_limit = deadline["priorities"][job_type]

        self.log.info("Renderlayer: %s" % instance.data["renderlayer"])

        assert priority <= priority_limit, ("Deadline priority should not be "
                                            "greater than %d."
                                            "" % priority_limit)
        assert not pool == "none", ("Deadline pool did not set.")
