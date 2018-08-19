import pyblish.api
from maya import cmds


class CollectLook(pyblish.api.InstancePlugin):
    """Collect mesh's shading network and objectSets
    """

    order = pyblish.api.CollectorOrder + 0.35
    hosts = ["maya"]
    label = "Collect Look"
    families = ["reveries.look"]

    def process(self, instance):
        meshes = cmds.ls(instance,
                         visible=True,
                         noIntermediate=True,
                         type="mesh")

        # Collect shading networks
        shaders = cmds.listConnections(meshes, type="shadingEngine")
        upstream_nodes = cmds.listHistory(shaders, pruneDagObjects=True)

        instance.data["look_members"] = upstream_nodes
        instance[:] += upstream_nodes
