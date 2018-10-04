
import math
import pyblish.api
from maya import cmds


class ValidateCameraCenterOfInterest(pyblish.api.InstancePlugin):
    """Ensure camera's `centerOfInterest` is not NaN
    """

    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    label = "Center Of Interest"
    families = [
        "reveries.camera",
        "reveries.playblast",
    ]

    def process(self, instance):
        try:
            camera = cmds.ls(instance[:], type="camera")[0]
        except IndexError:
            raise Exception("No camera.")

        coi_value = cmds.getAttr(camera + ".centerOfInterest")

        assert not math.isnan(coi_value), ("Camera `centerOfInterest` is NaN.")
