
import pyblish.api


class ValidateSingleCamera(pyblish.api.InstancePlugin):
    """Ensure the instance only content one camera
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Export Only One Camera"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):
        from maya import cmds

        cameras = cmds.ls(instance[:], type="camera")

        if len(cameras) == 0:
            raise Exception("No camera collected.")

        if len(cameras) > 1:
            raise Exception("Multiple cameras" "found: %s " % cameras)
