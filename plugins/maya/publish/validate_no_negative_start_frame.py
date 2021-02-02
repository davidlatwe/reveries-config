
import pyblish.api


class ValidateNoNegativeStartFrame(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "No Negative Start Frame"
    families = [
        "reveries.standin",
        "reveries.rsproxy",
        "reveries.atomscrowd",
        "reveries.renderlayer",
    ]

    def process(self, instance):
        err_msg = ("Negative start frame not supported. "
                   "Start frame should be greater than or equal to 0.")
        assert instance.data["startFrame"] >= 0, err_msg
