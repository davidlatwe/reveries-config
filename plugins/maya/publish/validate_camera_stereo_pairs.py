
import pyblish.api


class ValidateCameraStereoPairs(pyblish.api.InstancePlugin):
    """Stereo camera must have 'Left' and 'Right' side and properly named

    Side annotation in camera name is case sensitive.
    Must be ['Left', 'Right'], should not be ['left', 'right'].

    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Camera Stereo Pairs"
    families = [
        "reveries.camera",
        "reveries.renderlayer",
    ]

    def process(self, instance):
        from maya import cmds

        if instance.data["family"] == "reveries.camera":
            stereo_rig = cmds.ls(instance, type="stereoRigCamera")
            if not stereo_rig:
                return

            stereo_rig = stereo_rig[0]

        elif instance.data["family"] == "reveries.renderlayer":
            stereo_pairs = instance.data.get("stereo")
            if stereo_pairs is None:
                return

            stereo_rig = instance.data["camera"]

        else:
            # Not likely to happen..
            raise Exception("This is a bug.")

        stereo_rig_trans = cmds.listRelatives(stereo_rig,
                                              parent=True,
                                              path=True)[0]

        left_cam = self.validate_side(stereo_rig_trans, "Left")
        right_cam = self.validate_side(stereo_rig_trans, "Right")

        if not left_cam or not right_cam:
            raise Exception("Not a valid stereo camera.")

        left, left_shp = left_cam
        right, right_shp = right_cam

        match = (lambda L, R: L.replace("Left", "") == R.replace("Right", ""))

        if not match(left, right) or not match(left_shp, right_shp):
            raise Exception("Stereo camera name is not pairable.")

    def validate_side(self, rig, side):
        from maya import cmds

        camera = cmds.listConnections(rig + ".%sCam" % side.lower())
        if not camera:
            self.log.error("Nothing connected to %s side of stereo camera."
                           % side.lower())
            return

        camera = camera[0]

        camera_shp = cmds.listRelatives(camera, shapes=True, path=True)
        if not camera_shp:
            self.log.error("No camera connected to %s side of stereo camera."
                           % side.lower())
            return

        camera_shp = camera_shp[0]

        if side not in camera or side not in camera_shp:
            self.log.error("Stereo side '%s' did not tag in camera name."
                           % side)
            return

        return camera, camera_shp
