
import os
import pyblish.api


class ValidateWorkfileInWorkspace(pyblish.api.ContextPlugin):
    """確認工作檔真的是一個存在於硬碟上的檔案"""

    """Validate the workfile is a real existed file"""

    order = pyblish.api.ValidatorOrder - 0.49995
    label = "確認工作檔路徑"

    def process(self, context):
        current_making = context.data.get("currentMaking", "")
        if not os.path.isfile(current_making):
            raise RuntimeError("Workfile not exists: %s" % current_making)
