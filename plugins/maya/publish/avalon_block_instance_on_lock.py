
import pyblish.api
from avalon import maya


class BlockInstancesOnLock(pyblish.api.ContextPlugin):
    """Nothing can be published if scene is locked

    Except instances which required to publish on lock.

    """

    label = "Block Instances On Lock"
    order = pyblish.api.CollectorOrder + 0.4999
    hosts = ["maya"]

    def process(self, context):

        locked = maya.is_locked()

        for instance in context:
            publish_on_lock = instance.data.get("publishOnLock", False)

            block = not ((publish_on_lock and locked) or
                         (not publish_on_lock and not locked))

            if block:
                self.log.info("Blocking instances {!r}".format(instance.name))
                instance.data["optional"] = False

                if publish_on_lock:
                    instance.data["publish"] = True
                    instance.data["validationOnly"] = True
                else:
                    instance.data["publish"] = False
