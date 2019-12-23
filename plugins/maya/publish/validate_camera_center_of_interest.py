
import math
import pyblish.api
from maya import cmds


class ValidateCameraCenterOfInterest(pyblish.api.InstancePlugin):
    """Ensure camera's `centerOfInterest` is not NaN
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Center Of Interest"
    families = [
        "reveries.renderlayer",
        "reveries.camera",
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        if instance.data["family"] == "reveries.renderlayer":
            cameras = [instance.data["camera"], ]

        elif instance.data["family"] == "reveries.camera":
            cameras = cmds.ls(instance, type="camera", long=True)

        else:
            raise Exception("The family of '%s' was not handled, "
                            "this is a bug.")

        for cam in cameras:
            coi_value = cmds.getAttr(cam + ".centerOfInterest")
            if math.isnan(coi_value):
                invalid.append(cam)

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error("Camera `centerOfInterest` is NaN.")
            raise RuntimeError("Invalid cameras "
                               "found: {0}".format(invalid))
