import pyblish.api
from maya import cmds


class CollectAllDescendents(pyblish.api.InstancePlugin):
    """Collect instance's allDescendents
    """

    order = pyblish.api.CollectorOrder + 0.11
    hosts = ["maya"]
    label = "Collect All Descendents"

    def process(self, instance):
        # Keep origin objectSet member, for plugins that requires
        # strict selection.
        instance.data["originMembers"] = instance[:]

        # Collect all descendents
        instance += cmds.listRelatives(instance,
                                       allDescendents=True,
                                       fullPath=True) or []

        instance[:] = sorted(set(instance))

        self.log.debug("Descendents collected for instance {!r}."
                       "".format(str(instance.name)))
