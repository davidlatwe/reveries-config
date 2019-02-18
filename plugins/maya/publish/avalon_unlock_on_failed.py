
import pyblish.api
from avalon import maya


class UnlockSceneOnFailed(pyblish.api.ContextPlugin):
    """Unlock Maya scene if error raised during extraction or integration
    """

    label = "Unlock On Failed"
    order = pyblish.api.IntegratorOrder + 0.499
    hosts = ["maya"]

    def process(self, context):

        if not all(result["success"] for result in context.data["results"]):
            publish_on_lock = any(i.data.get("publishOnLock") for i in context)

            if publish_on_lock:
                self.log.info("Publish on lock failed, remain locked.")
                return

            self.log.info("Publish failed, scene unlocked.")
            maya.unlock()
