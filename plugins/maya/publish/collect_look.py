
import pyblish.api
from maya import cmds
from reveries import plugins
from reveries.maya import pipeline, utils


def create_texture_subset_from_look(instance, textures, use_txmaps):
    """
    """
    family = "reveries.texture"
    subset = instance.data["subset"]
    subset = "texture" + subset[0].upper() + subset[1:]
    data = {
        "useTxMaps": use_txmaps,
    }

    plugins.create_dependency_instance(instance,
                                       subset,
                                       family,
                                       textures,
                                       data=data)


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

        # Require Avalon UUID
        instance.data["requireAvalonUUID"] = cmds.listRelatives(surfaces,
                                                                parent=True,
                                                                fullPath=True)

        instance.data["dagMembers"] = instance[:]
        instance[:] = instance.data.pop("shadingNetwork", [])

        stray = pipeline.find_stray_textures(instance)
        if stray:
            is_arnold = utils.get_renderer_by_layer() == "arnold"
            create_texture_subset_from_look(instance, stray, is_arnold)
