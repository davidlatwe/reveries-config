from maya import cmds

import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Invalid Camera"


class ValidateCameraNotDefault(pyblish.api.InstancePlugin):
    """Ensure no default (startup) camera"""

    order = pyblish.api.ValidatorOrder
    label = "Not Default Camera"
    hosts = ["maya"]
    families = [
        "reveries.camera",
        "reveries.renderlayer",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        cameras = instance.data.get("renderCam")
        if not cameras:
            cameras = cmds.ls(instance, type="camera", long=True)

        defaults = [cam for cam in cameras if
                    cmds.camera(cam, query=True, startupCamera=True)]

        invalid = defaults
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Default cameras "
                               "found: {0}".format(invalid))
