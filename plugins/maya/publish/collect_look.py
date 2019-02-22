
import pyblish.api
from maya import cmds
from reveries import plugins
from reveries.maya import pipeline


def create_texture_subset_from_look(look_instance, textures):
    """
    """
    look_name = "look"
    texture_name = "texture"
    family = "reveries.texture"
    subset = texture_name + look_instance.data["subset"][len(look_name):]

    plugins.create_dependency_instance(look_instance,
                                       subset,
                                       family,
                                       textures)


class CollectLook(pyblish.api.InstancePlugin):
    """Collect mesh's shading network and objectSets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Look"
    families = ["reveries.look"]

    def process(self, instance):
        surfaces = cmds.ls(instance,
                           noIntermediate=True,
                           type="surfaceShape")

        # Collect shading networks
        shaders = cmds.listConnections(surfaces, type="shadingEngine")
        upstream_nodes = cmds.ls(cmds.listHistory(shaders), long=True)
        # (NOTE): The flag `pruneDagObjects` will also filter out
        # `place3dTexture` type node.

        # Remove unwanted types
        unwanted_types = ("groupId", "groupParts", "surfaceShape")
        unwanted = set(cmds.ls(upstream_nodes, type=unwanted_types, long=True))
        upstream_nodes = list(set(upstream_nodes) - unwanted)

        instance.data["dagMembers"] = instance[:]
        instance[:] = upstream_nodes

        stray = pipeline.find_stray_textures(instance)
        if stray:
            create_texture_subset_from_look(instance, stray)
