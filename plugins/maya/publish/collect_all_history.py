import pyblish.api
from maya import cmds


class CollectAllHistory(pyblish.api.InstancePlugin):
    """Collect instance shape members' history connections
    """

    order = pyblish.api.CollectorOrder + 0.12
    hosts = ["maya"]
    label = "Collect All History"

    def process(self, instance):
        shapes = cmds.ls(instance, type="shape", noIntermediate=True)

        try:
            history = cmds.listHistory(shapes,
                                       future=True,
                                       pruneDagObjects=True) or []
        except RuntimeError:
            # Found no items to list the history for.
            history = []

        instance.data["allHistory"] = set(history)

        self.log.debug("History collected for instance {!r}."
                       "".format(str(instance.name)))
