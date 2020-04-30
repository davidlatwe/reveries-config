
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

        stereo_cameras = cmds.ls(instance, type="stereoRigCamera")
        cameras = cmds.ls(instance, exactType="camera")

        if len(cameras) == 0 and len(stereo_cameras) == 0:
            raise Exception("No camera collected.")

        if (len(stereo_cameras) > 1
                or (len(stereo_cameras) == 1 and len(cameras) > 2)
                or (len(stereo_cameras) == 0 and len(cameras) > 1)):
            raise Exception("Multiple cameras found: %s "
                            % (stereo_cameras + cameras))
