
import pyblish.api
from maya import cmds


class CollectContainerInterface(pyblish.api.InstancePlugin):
    """Collect container interfaces from instance

    Collected data:

        * interfaces

    """

    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["maya"]
    label = "Container Interface"

    CONTAINER_INTERFACE_ID = "pyblish.avalon.interface"

    def process(self, instance):
        instance.data["interfaces"] = list()

        for node in instance:
            try:
                _id = cmds.getAttr(node + ".id")
            except ValueError:
                pass
            else:
                if _id == self.CONTAINER_INTERFACE_ID:
                    instance.data["interfaces"].append(node)
