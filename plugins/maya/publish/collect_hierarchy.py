import pyblish.api
from maya import cmds


class CollectHierarchy(pyblish.api.InstancePlugin):
    """Collect instance's allDescendents
    """

    order = pyblish.api.CollectorOrder
    hosts = ["maya"]
    label = "Collect Hierarchy"

    def process(self, instance):
        # Collect all descendents
        instance += cmds.listRelatives(instance,
                                       allDescendents=True,
                                       fullPath=True) or []

        instance[:] = sorted(list(set(instance[:])))
