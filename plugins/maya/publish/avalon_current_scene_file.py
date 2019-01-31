import os

from maya import cmds

import pyblish.api


class CurrentSceneFile(pyblish.api.ContextPlugin):
    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Current Scene File"
    hosts = ["maya"]

    def process(self, context):
        """Inject the current working file"""
        current_file = cmds.file(query=True, sceneName=True)
        context.data["currentMaking"] = os.path.normpath(current_file)
