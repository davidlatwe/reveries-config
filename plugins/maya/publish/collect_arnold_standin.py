
import pyblish.api
from maya import cmds


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
        surfaces = cmds.ls(instance,
                           noIntermediate=True,
                           type="surfaceShape")

        # Collect shading networks
        shaders = cmds.listConnections(surfaces, type="shadingEngine")
        try:
            _history = cmds.listHistory(shaders)
        except RuntimeError:
            _history = []  # Found no items to list the history for.
        upstream_nodes = cmds.ls(_history, long=True)

        instance.data["fileNodes"] = cmds.ls(upstream_nodes, type="file")
        instance.data["relativeRoot"] = ["$AVALON_PROJECTS",
                                         "$AVALON_PROJECT"]
        instance.data["replaceRoot"] = ["[AVALON_PROJECTS]",
                                        "[AVALON_PROJECT]"]

        # Frame range
        if instance.data["staticCache"]:
            instance.data["startFrame"] = cmds.currentTime(query=True)
            instance.data["endFrame"] = cmds.currentTime(query=True)
        else:
            get = (lambda f: cmds.playbackOptions(query=True, **f))
            instance.data["startFrame"] = get({"minTime": True})
            instance.data["endFrame"] = get({"maxTime": True})

        instance.data["byFrameStep"] = 1
