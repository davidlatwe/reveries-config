import os
import pyblish.api


class ValidateWorkfileName(pyblish.api.ContextPlugin):
    """Validate the workfile name is the same as collected"""

    order = pyblish.api.ValidatorOrder - 0.49995
    label = "Workfile Name"
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds

        current_file = cmds.file(query=True, sceneName=True)

        if context.data["currentMaking"] != os.path.normpath(current_file):
            raise Exception("Scene name changed, please re-run the publish "
                            "process.")
