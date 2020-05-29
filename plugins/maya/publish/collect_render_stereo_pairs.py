
import pyblish.api


class CollectRenderStereoPairs(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["maya"]
    label = "Collect Stereo Pairs"
    families = ["reveries.renderlayer"]

    def process(self, instance):
        camera = instance.data["camera"]
        stereo_rig = self.stereo_rig(camera)
        if not stereo_rig:
            return

        side = self.stereo_side(stereo_rig, camera)
        oppo = self.stereo_oppo(stereo_rig, camera)

        instance.data["isStereo"] = True
        instance.data["stereoSide"] = side
        instance.data["stereoOppo"] = oppo

    def stereo_rig(self, camera):
        """Returns setreo rig camera if this camera is being rigged

        Args:
            camera (str): Camera long name

        Returns:
            (str): Setreo rig camera long name or None if not stereo

        """
        from maya import cmds

        stereo_rig = cmds.listConnections(camera,
                                          destination=False,
                                          source=True,
                                          type="stereoRigCamera")
        if stereo_rig:
            return cmds.ls(stereo_rig, long=True)[0]

    def stereo_oppo(self, stereo_rig, camera):
        """Find opposite side if this camera is part of a setreo rig

        Args:
            stereo_rig (str): Stereo rig camera name
            camera (str): Camera long name

        Returns:
            (str): Opposite camera long name

        """
        from maya import cmds

        cameras = cmds.listConnections(stereo_rig,
                                       destination=True,
                                       source=False,
                                       shapes=True,
                                       type="camera",
                                       exactType=True)

        opposite = next(c for c in cmds.ls(cameras, long=True)
                        if c != camera)

        return opposite

    def stereo_side(self, stereo_rig, camera):
        """Returns which side is this camera in the stereo rig

        Args:
            stereo_rig (str): Stereo rig camera name
            camera (str): Camera name

        Returns:
            (str): Side of camera, "left" or "right" (None if invalid rig)

        """
        from maya import cmds

        camera = cmds.listRelatives(camera, parent=True, path=True)[0]
        cam_msg = camera + ".message"

        if cmds.isConnected(cam_msg, stereo_rig + ".leftCamera"):
            return "left"
        elif cmds.isConnected(cam_msg, stereo_rig + ".rightCamera"):
            return "right"
        else:
            return None
