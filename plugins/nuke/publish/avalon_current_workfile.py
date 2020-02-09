import os
import pyblish.api


class CurrentWorkfile(pyblish.api.ContextPlugin):
    """紀錄當前工作檔的檔案路徑"""

    """Inject the current working file into context"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "當前工作檔"
    hosts = ["nuke"]

    def process(self, context):
        """Inject the current working file"""
        import nuke

        try:
            current_file = nuke.scriptName()
        except RuntimeError:
            # no filename available, have you saved?
            current_file = "Untitled"

        context.data["currentMaking"] = os.path.normpath(current_file)
        context.data["label"] = os.path.basename(current_file)
