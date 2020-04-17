
import pyblish.api
from reveries import plugins


class SelectInvalid(plugins.MayaSelectInvalidInstanceAction):

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
        from maya import cmds

        if instance.data["family"] == "reveries.renderlayer":
            cameras = [instance.data["camera"], ]

        elif instance.data["family"] == "reveries.camera":
            cameras = cmds.ls(instance, type="camera", long=True)

        else:
            raise Exception("The family of '%s' was not handled, "
                            "this is a bug.")

        defaults = [cam for cam in cameras if
                    cmds.camera(cam, query=True, startupCamera=True)]

        invalid = defaults
        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Default cameras "
                               "found: {0}".format(invalid))
