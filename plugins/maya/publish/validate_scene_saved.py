
import pyblish.api

from maya import cmds


class ValidateSceneSaved(pyblish.api.InstancePlugin):
    """Valides the frame ranges and fps.
    """

    label = "Validate Scene Saved"
    hosts = ["maya"]
    order = pyblish.api.ValidatorOrder - 0.49

    def process(self, instance):
        if cmds.file(q=True, modified=True):
            raise RuntimeError("Save scene before publish.")
