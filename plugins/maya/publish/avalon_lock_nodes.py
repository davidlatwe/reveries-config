
import pyblish.api
from avalon import maya


class AvalonLockNodes(pyblish.api.ContextPlugin):
    """Lock all nodes if instances required to publish on lock
    """

    label = "Lock Nodes"
    order = pyblish.api.IntegratorOrder + 0.499999
    hosts = ["maya"]

    def process(self, context):
        from reveries.maya.pipeline import lock_edit, is_editable

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        publish_on_lock = any(i.data.get("publishOnLock") for i in context)

        if maya.is_locked() and publish_on_lock:
            if not is_editable():
                self.log.info("All nodes already locked.")
                return

            self.log.info("Locking all nodes.")
            lock_edit()

        else:
            self.log.info("No need to be locked.")
