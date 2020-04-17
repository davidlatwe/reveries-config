
import os
import re
import shutil
import pyblish.api


class CleanupStage(pyblish.api.ContextPlugin):
    """Unlock version directory after subsets have been integrated
    """

    label = "Cleanup Stage"
    order = pyblish.api.IntegratorOrder + 0.2

    targets = ["localhost"]

    def process(self, context):
        # Skip if any error occurred
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            stage_dirs = [value for key, value in instance.data.items()
                          if re.match(r"repr\.[a-zA-Z_]*\._stage", key)
                          and os.path.isdir(value)]

            stage_dirs = set([os.path.normpath(path) for path in stage_dirs])
            for path in stage_dirs:
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    self.log.warning(e)
