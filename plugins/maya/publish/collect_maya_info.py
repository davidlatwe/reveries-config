import os

import pyblish.api

from maya import cmds


class CollectMayaInfo(pyblish.api.ContextPlugin):
    """Inject the current workspace and maya version into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Maya Info"
    hosts = ["maya"]

    def process(self, context):
        workspace = cmds.workspace(rootDirectory=True, query=True)
        if not workspace:
            # Project has not been set. Files will
            # instead end up next to the working file.
            workspace = cmds.workspace(dir=True, query=True)

        # Maya returns forward-slashes by default
        normalised = os.path.normpath(workspace)

        context.data["workspaceDir"] = normalised

        context.data["mayaVersion"] = cmds.about(version=True)
        context.data["mayaVersionAPI"] = cmds.about(apiVersion=True)
