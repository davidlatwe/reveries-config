
import pyblish.api
from maya import cmds
from reveries import plugins


def create_texture_subset_from_look(instance, textures):
    """
    """
    family = "reveries.texture"
    subset = instance.data["subset"]
    subset = "texture" + subset[0].upper() + subset[1:]

    data = {"useTxMaps": True}

    child = plugins.create_dependency_instance(instance,
                                               subset,
                                               family,
                                               textures,
                                               data=data)
    instance.data["textureInstance"] = child


class CollectLook(pyblish.api.InstancePlugin):
    """Collect mesh's shading network and objectSets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Look"
    families = ["reveries.look"]

    def process(self, instance):
        from reveries.maya import pipeline

        surfaces = cmds.ls(instance,
                           noIntermediate=True,
                           type="surfaceShape")

        # Require Avalon UUID
        instance.data["requireAvalonUUID"] = cmds.listRelatives(surfaces,
                                                                parent=True,
                                                                fullPath=True)

        instance.data["dagMembers"] = instance[:]
        instance[:] = instance.data.pop("shadingNetwork", [])

        stray = pipeline.find_stray_textures(instance)
        if stray:
            create_texture_subset_from_look(instance, stray)
