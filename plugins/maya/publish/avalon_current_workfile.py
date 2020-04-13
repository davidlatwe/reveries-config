import os
import pyblish.api


class CurrentWorkfile(pyblish.api.ContextPlugin):
    """紀錄當前工作檔的檔案路徑"""

    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "當前工作檔"
    hosts = ["maya"]

    def process(self, context):
        """Inject the current working file"""
        from maya import cmds

        current_file = cmds.file(query=True, sceneName=True)
        context.data["currentMaking"] = os.path.normpath(current_file)
