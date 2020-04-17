
import pyblish.api


class CollectAllInstanced(pyblish.api.InstancePlugin):
    """Collect instanced objects from Maya instancers
    """

    order = pyblish.api.CollectorOrder + 0.115
    hosts = ["maya"]
    label = "Collect All Instanced"

    def process(self, instance):
        from maya import cmds

        instanced_hierarchies = dict()
        instanced_roots = set()

        for instancer in cmds.ls(instance, type="instancer"):
            inputs = cmds.listConnections(instancer + ".inputHierarchy",
                                          source=True,
                                          destination=False)
            instanced_roots.update(cmds.ls(inputs, long=True))

        for root in instanced_roots:
            hierarchy = [root]
            hierarchy += cmds.listRelatives(hierarchy,
                                            allDescendents=True,
                                            fullPath=True) or []

            instanced_hierarchies[root] = sorted(set(hierarchy))

        instance.data["instancedHierarchies"] = instanced_hierarchies
