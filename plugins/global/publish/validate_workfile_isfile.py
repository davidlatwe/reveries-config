
import os
import pyblish.api


class ValidateWorkfileInWorkspace(pyblish.api.ContextPlugin):
    """Validate the workfile is a real existed file"""

    order = pyblish.api.ValidatorOrder - 0.49995
    label = "Workfile Exists"

    def process(self, context):
        current_making = context.data.get("currentMaking")
        if not os.path.isfile(current_making):
            raise RuntimeError("Workfile not exists: %s" % current_making)
