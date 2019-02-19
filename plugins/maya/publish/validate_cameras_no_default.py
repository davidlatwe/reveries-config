from maya import cmds

import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Invalid Cameras"


class ValidateCamerasNoDefault(pyblish.api.InstancePlugin):
    """Ensure no default (startup) cameras"""

    order = pyblish.api.ValidatorOrder
    label = "No Default Cameras"
    hosts = ["maya"]
    families = [
        "reveries.camera",
        "reveries.imgseq",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        cameras = cmds.ls(instance[:], type="camera", long=True)
        cameras += instance.data.get("renderCam", [])
        defaults = [cam for cam in cameras if
                    cmds.camera(cam, query=True, startupCamera=True)]

        invalid = defaults
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Default cameras "
                               "found: {0}".format(invalid))
