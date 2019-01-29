
import pyblish.api

from avalon.pipeline import AVALON_CONTAINER_ID
from reveries import plugins
from reveries.maya import lib, pipeline


def create_texture_subset_from_lightSet(instance, textures):
    """
    """
    look_name = "lightSet"
    texture_name = "texture"
    family = "reveries.texture"
    subset = texture_name + instance.data["subset"][len(look_name):]

    plugins.create_dependency_instance(instance,
                                       subset,
                                       family,
                                       textures)


class CollectLightSet(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect LightSet"
    families = ["reveries.lightset"]

    def process(self, instance):
        from maya import cmds

        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

        lights = list()
        # Find all light node from shapes
        for node in cmds.ls(instance, type="shape", long=True):
            if "Light" in cmds.nodeType(node):
                # (NOTE) The light node from third party render engine might
                # not inherited from Maya `renderLight` type node, hence you
                # cannot use `cmds.ls(type="light")` nor `cmds.ls(lights=True)`
                # to find them.
                # Since I found there always have "Light" in thier type name,
                # so I use this as a workaround to filter out all the light
                # nodes.
                lights.append(node)

        instance.data["lights"] = lights
        instance.data["dagMembers"] = instance[:]

        upstream_nodes = cmds.ls(cmds.listHistory(lights), long=True)

        # Remove nodes that are not belong to current DAG hierarchy
        for node in cmds.ls(upstream_nodes, type="transform", long=True):
            if node not in instance.data["dagMembers"]:
                upstream_nodes.remove(node)

        instance[:] = list(set(upstream_nodes + instance.data["dagMembers"]))

        stray = pipeline.find_stray_textures(instance, containers)
        if stray:
            create_texture_subset_from_lightSet(instance, stray)
