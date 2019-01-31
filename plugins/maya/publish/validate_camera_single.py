import pyblish.api

from maya import cmds


class ValidateSingleCamera(pyblish.api.InstancePlugin):
    """Ensure the instance only content one camera
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Single Camera"
    families = [
        "reveries.imgseq",
        "reveries.camera",
    ]

    def process(self, instance):
        cameras = cmds.ls(instance[:], type="camera")

        if len(cameras) == 0:
            raise Exception("No camera collected.")

        if len(cameras) > 1:
            raise Exception("Multiple cameras" "found: %s " % cameras)
