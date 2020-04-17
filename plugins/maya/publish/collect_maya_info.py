
import os
import pyblish.api


class CollectMayaInfo(pyblish.api.ContextPlugin):
    """紀錄 Maya 版本以及目前工作空間 (workspace) 路徑"""

    """Inject the current workspace and maya version into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "關於 Maya .."
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds

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
