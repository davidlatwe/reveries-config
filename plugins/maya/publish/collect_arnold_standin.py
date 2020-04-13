
import pyblish.api
from maya import cmds
from reveries import plugins


def create_texture_subset_from_standin(instance, textures):
    """
    """
    family = "reveries.texture"
    subset = instance.data["subset"]
    subset = "texture" + subset[0].upper() + subset[1:]

    data = {"useTxMaps": True}

    plugins.create_dependency_instance(instance,
                                       subset,
                                       family,
                                       textures,
                                       data=data)


class CollectArnoldStandIn(pyblish.api.InstancePlugin):
    """Collect mesh's shading network and objectSets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Arnold Stand-In"
    families = [
        "reveries.standin"
    ]

    def process(self, instance):
        from reveries.maya import pipeline

        upstream_nodes = instance.data.get("shadingNetwork", [])
        file_nodes = cmds.ls(upstream_nodes, type="file")
        instance.data["fileNodes"] = file_nodes

        # Frame range
        if instance.data["staticCache"]:
            instance.data["startFrame"] = cmds.currentTime(query=True)
            instance.data["endFrame"] = cmds.currentTime(query=True)
        else:
            get = (lambda f: cmds.playbackOptions(query=True, **f))
            instance.data["startFrame"] = get({"minTime": True})
            instance.data["endFrame"] = get({"maxTime": True})

        instance.data["step"] = 1

        stray = pipeline.find_stray_textures(file_nodes)
        if stray:
            self.log.info("Found not versioned textures, creating "
                          "instance for publish.")
            create_texture_subset_from_standin(instance, stray)

        # Yeti
        if cmds.ls(instance, type="pgYetiMaya"):
            instance.data["hasYeti"] = True
