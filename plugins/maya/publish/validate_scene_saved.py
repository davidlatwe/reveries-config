
import pyblish.api

from maya import cmds


class ValidateSceneSaved(pyblish.api.ContextPlugin):
    """Maya scene should be saved before publish and not locked.

    Save your work, if the scene has been locked, please *saveAs*.

    """

    label = "Scene Saved"
    hosts = ["maya"]
    order = pyblish.api.ValidatorOrder - 0.49

    def process(self, context):
        from avalon import maya

        if context.data.get("_ignore_modifications"):
            return

        if cmds.file(q=True, modified=True):
            raise RuntimeError("Save scene before publish.")

        if not context.data.get("contractorAccepted"):
            assert not maya.is_locked(), (
                "This file is locked, please save scene under a new name."
            )
