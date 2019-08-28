
import pyblish.api
from maya import cmds
from reveries import plugins
from reveries.maya import pipeline


def create_texture_subset_from_look(instance, textures):
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
        shaders = list(set(shaders))
        try:
            # (NOTE): The flag `pruneDagObjects` will also filter out
            #         `place3dTexture` type node.
            # (NOTE): Without flag `allConnections`, upstream nodes before
            #         `aiColorCorrect` may not be tracked if only `outAlpha`
            #         is connected to downstream node.
            #         This might be a bug of Arnold since other Maya node
            #         does not have this issue, not fully tested so not
            #         sure. MtoA version: 3.1.2.1
            _history = cmds.listHistory(shaders, allConnections=True)
            _history = list(set(_history))
        except RuntimeError:
            _history = []  # Found no items to list the history for.
        upstream_nodes = cmds.ls(_history, long=True)

        # Remove unwanted types
        unwanted_types = ("groupId", "groupParts", "surfaceShape")
        unwanted = set(cmds.ls(upstream_nodes, type=unwanted_types, long=True))
        upstream_nodes = list(set(upstream_nodes) - unwanted)

        # Require Avalon UUID
        instance.data["requireAvalonUUID"] = cmds.listRelatives(surfaces,
                                                                parent=True,
                                                                fullPath=True)

        instance.data["dagMembers"] = instance[:]
        instance[:] = upstream_nodes

        stray = pipeline.find_stray_textures(instance)
        if stray:
            create_texture_subset_from_look(instance, stray)
