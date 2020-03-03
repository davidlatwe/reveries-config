
import pyblish.api


class CollectShadingNetwork(pyblish.api.InstancePlugin):
    """Gathering shading nodes from shading network which has assigned
    """

    order = pyblish.api.CollectorOrder + 0.18
    hosts = ["maya"]
    label = "Collect Shading Network"
    families = [
        "reveries.look",
        "reveries.standin",
    ]

    def process(self, instance):
        from maya import cmds

        surfaces = cmds.ls(instance,
                           noIntermediate=True,
                           type="surfaceShape")

        # Collect geometry from Maya instancers
        for hierarchy in instance.data["instancedHierarchies"].values():
            surfaces += cmds.ls(hierarchy,
                                noIntermediate=True,
                                type="surfaceShape")

        surfaces = list(set(surfaces))
        if not surfaces:
            raise Exception("No surface collected, this should not happen. "
                            "Possible empty group ?")

        # Collect shading networks
        shaders = cmds.listConnections(surfaces, type="shadingEngine") or []
        shaders = list(set(shaders))

        # Filter out dag set members before collecting history
        _dags = cmds.listConnections([s + ".dagSetMembers" for s in shaders],
                                     destination=False,
                                     source=True) or []
        _srcs = cmds.listConnections(shaders,
                                     destination=False,
                                     source=True) or []

        sources = list(set(_srcs) - set(_dags))

        try:
            # (NOTE): The flag `pruneDagObjects` will also filter out
            #         `place3dTexture` type node.
            # (NOTE): Without flag `allConnections`, upstream nodes before
            #         `aiColorCorrect` may not be tracked if only `outAlpha`
            #         is connected to downstream node.
            #         This might be a bug of Arnold since other Maya node
            #         does not have this issue, not fully tested so not
            #         sure. MtoA version: 3.1.2.1
            _history = cmds.listHistory(sources, allConnections=True)
        except RuntimeError:
            _history = []  # Found no items to list the history for.
        else:
            _history = list(set(_history))

        shading_nodes = cmds.ls(_history, long=True)

        # Remove unwanted types
        unwanted_types = ("groupId", "groupParts", "surfaceShape")
        unwanted = set(cmds.ls(shading_nodes, type=unwanted_types, long=True))
        shading_nodes = shaders + list(set(shading_nodes) - unwanted)

        instance.data["shadingNetwork"] = shading_nodes
