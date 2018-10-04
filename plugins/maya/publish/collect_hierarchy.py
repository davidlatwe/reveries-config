import pyblish.api
from maya import cmds


class CollectHierarchy(pyblish.api.InstancePlugin):
    """Collect instance's allDescendents
    """

    order = pyblish.api.CollectorOrder
    hosts = ["maya"]
    label = "Collect Hierarchy"

    def process(self, instance):

        # Collect set members from container interface
        for node in instance:
            try:
                _id = cmds.getAttr(node + ".id")
            except ValueError:
                pass
            else:
                if _id == "pyblish.avalon.interface":
                    instance += cmds.ls(cmds.sets(node, query=True), long=True)

        # Collect all descendents
        instance += cmds.listRelatives(instance,
                                       allDescendents=True,
                                       fullPath=True) or []

        instance[:] = sorted(list(set(instance[:])))
