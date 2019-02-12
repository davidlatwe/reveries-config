import pyblish.api
from maya import cmds


class CollectAllDescendents(pyblish.api.InstancePlugin):
    """Collect instance's allDescendents
    """

    order = pyblish.api.CollectorOrder
    hosts = ["maya"]
    label = "Collect All Descendents"

    def process(self, instance):
        # Collect all descendents
        instance += cmds.listRelatives(instance,
                                       allDescendents=True,
                                       fullPath=True) or []

        instance[:] = sorted(list(set(instance)))

        self.log.debug("Descendents collected for instance {!r}."
                       "".format(str(instance.name)))
