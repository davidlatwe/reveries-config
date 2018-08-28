
import pyblish.api
from maya import cmds
from avalon import maya


class AvalonLockScene(pyblish.api.ContextPlugin):
    """Prevent accidental overwrite of original scene once published

    A node is placed within the scene called "lock" where the name of
    the file as it exists currently is imprinted. If an attempt is made
    to publish this file where the name of the file and that in the lock
    is a match, publishing fails.

    """

    label = "Lock Scene"
    order = pyblish.api.IntegratorOrder + 0.5

    def process(self, context):

        assert all(result["success"] for result in context.data["results"]), (
            "Integration failed, aborting.")

        maya.lock()

        with maya.lock_ignored():
            cmds.file(save=True, force=True)
