
import pyblish.api
from avalon import maya


class UnlockSceneOnFailed(pyblish.api.ContextPlugin):
    """Unlock Maya scene if error raised during extraction or integration
    """

    label = "Unlock On Failed"
    order = pyblish.api.IntegratorOrder + 0.499

    def process(self, context):

        if not all(result["success"] for result in context.data["results"]):
            self.log.info("Publish failed, scene unlocked.")
            maya.unlock()
