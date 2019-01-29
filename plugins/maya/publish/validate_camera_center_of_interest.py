
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
        "reveries.imgseq",
        "reveries.camera",
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        cameras = cmds.ls(instance[:], type="camera", long=True)
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
