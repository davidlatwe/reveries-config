
import contextlib
import pyblish.api
from reveries import utils


class ExtractPointCacheFBX(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache (fbx)"
    families = [
        "reveries.pointcache.fbx",
    ]

    def process(self, instance):
        from maya import cmds

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        cachename = "%s.fbx" % instance.data["subset"]
        filename = "%s.ma" % instance.data["subset"]
        cachepath = "%s/%s" % (staging_dir, cachename)
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.FBXCache._stage"] = staging_dir
        instance.data["repr.FBXCache._hardlinks"] = [filename, cachename]
        instance.data["repr.FBXCache.entryFileName"] = filename

        if instance.data.get("staticCache"):
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)
        else:
            context_data = instance.context.data
            start = context_data.get("startFrame")
            end = context_data.get("endFrame")

            instance.data["startFrame"] = start
            instance.data["endFrame"] = end

        # (TODO) Make namespace preserving optional on GUI
        keep_namespace = instance.data.get("keepNamespace", False)
        nodes = instance.data["outCache"]

        instance.data["repr.FBXCache._delayRun"] = {
            "func": self.export_fbx,
            "args": [
                outpath,
                cachepath,
                cachename,
                nodes,
                keep_namespace
            ],
        }

    def export_fbx(self,
                   outpath,
                   cachepath,
                   cachename,
                   nodes,
                   keep_namespace):
        from reveries.maya import io, capsule
        from maya import cmds

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
        ):

            cmds.select(nodes, replace=True)

            with capsule.StripNamespace([] if keep_namespace else nodes):
                with io.export_fbx_set_pointcache("FBXCacheSET"):
                    io.export_fbx(cachepath)

                io.wrap_fbx(outpath, [(cachename, "ROOT")])
