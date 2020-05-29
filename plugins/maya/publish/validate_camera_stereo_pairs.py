
import pyblish.api


class ValidateCameraStereoPairs(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Camera Stereo Pairs"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):
        from maya import cmds

        stereo_rig = cmds.ls(instance, type="stereoRigTransform")
        if not stereo_rig:
            return

        stereo_rig = stereo_rig[0]

        if (not self.validate_side(stereo_rig, "left")
                or not self.validate_side(stereo_rig, "right")):
            raise Exception("Not a valid stereo camera.")

    def validate_side(self, rig, side):
        from maya import cmds

        camera = cmds.listConnections(rig + ".%sCamera" % side)
        if not camera:
            self.log.error("Nothing connected to %s side of stereo camera."
                           % side)
            return False

        camera = camera[0]

        camera_shp = cmds.listRelatives(camera, shapes=True, path=True)
        if not camera_shp:
            self.log.error("No camera connected to %s side of stereo camera."
                           % side)
            return False

        camera_shp = camera_shp[0]

        if side not in camera.lower() or side not in camera_shp.lower():
            self.log.error("Stereo side '%s' did not tag in camera name."
                           % side)
            return False

        return True
