
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
        from reveries.maya import pipeline

        upstream_nodes = instance.data.get("shadingNetwork", [])
        instance.data["fileNodes"] = cmds.ls(upstream_nodes, type="file")

        # Frame range
        if instance.data["staticCache"]:
            instance.data["startFrame"] = cmds.currentTime(query=True)
            instance.data["endFrame"] = cmds.currentTime(query=True)
        else:
            get = (lambda f: cmds.playbackOptions(query=True, **f))
            instance.data["startFrame"] = get({"minTime": True})
            instance.data["endFrame"] = get({"maxTime": True})

        instance.data["byFrameStep"] = 1
