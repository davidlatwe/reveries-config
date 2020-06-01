
import pyblish.api


class CollectAllDescendents(pyblish.api.InstancePlugin):
    """Collect instance's allDescendents
    """

    order = pyblish.api.CollectorOrder + 0.11
    hosts = ["maya"]
    label = "Collect All Descendents"

    def process(self, instance):
        from maya import cmds

        # Collect all descendents
        members = instance[:]

        for node in instance:
            if not cmds.objExists(node):
                self.log.warning("No object matches name: %s" % node)
                continue
            members += cmds.listRelatives(node,
                                          allDescendents=True,
                                          fullPath=True) or []

        instance[:] = sorted(set(members))
