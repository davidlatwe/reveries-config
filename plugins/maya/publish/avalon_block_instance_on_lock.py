
import pyblish.api


class BlockInstancesOnLock(pyblish.api.ContextPlugin):
    """Nothing can be published if scene is locked

    Unless you got privilege.

    """

    label = "Block Instances On Lock"
    order = pyblish.api.CollectorOrder + 0.4999
    hosts = ["maya"]

    def process(self, context):
        from avalon import maya

        if not maya.is_locked():
            return

        if context.data.get("_has_privileged_instance"):
            context.data["_ignore_modifications"] = True
        else:
            return

        self.log.info("Blocking instances..")

        for instance in context:
            if instance.data.get("_privilege_on_lock"):
                self.log.info("Instance {!r} has privilege, skipping.."
                              "".format(instance.name))
                continue

            instance.data["optional"] = False
            instance.data["publish"] = False
