import pyblish.api
from maya import cmds


class CollectAllHistory(pyblish.api.InstancePlugin):
    """Collect instance shape members' history connections
    """

    order = pyblish.api.CollectorOrder + 0.39
    hosts = ["maya"]
    label = "Collect All History"

    def process(self, instance):
        shapes = cmds.ls(instance, type="shape", noIntermediate=True)
        history = cmds.listConnections(shapes, skipConversionNodes=True) or []

        instance.data["allHistory"] = set(history)

        self.log.debug("History collected for instance {!r}."
                       "".format(str(instance.name)))
