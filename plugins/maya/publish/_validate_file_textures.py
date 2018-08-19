import pyblish.api

from maya import cmds


class ValidateFileTextures(pyblish.api.InstancePlugin):
    """Ensure file exists
    """

    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    label = "Validate Camera"
    families = [
        "reveries.camera",
        "reveries.playblast",
    ]

    def process(self, instance):

        members = cmds.ls(instance[:], type="camera")

        if len(members) > 1:
            msg = "Each instance can only have one camera."
            self.log.error(msg)
            raise Exception(msg)

        if not members:
            msg = "No camera to publish."
            self.log.error(msg)
            raise TypeError(msg)
