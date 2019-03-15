
import pyblish.api
from maya import cmds
from avalon import maya


class AvalonLockScene(pyblish.api.ContextPlugin):
    """Forbid saving any work file modification once entering extraction

    A node is placed within the scene called "lock" where the name of
    the file as it exists currently is imprinted. If an attempt is made
    to publish this file where the name of the file and that in the lock
    is a match, publishing fails.

    Scene will be saved.

    """

    label = "Lock and Save Scene"
    order = pyblish.api.ExtractorOrder - 0.499
    hosts = ["maya"]

    def process(self, context):

        assert any(inst.data.get("publish", True) for inst in context), (
            "No instance been published, aborting.")

        if maya.is_locked():
            return

        maya.lock()

        # Switch to masterLayer before save
        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        with maya.lock_ignored():
            cmds.file(save=True, force=True)
