
import contextlib
import pyblish.api


class ExtractPointCacheGPU(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache (gpu)"
    families = [
        "reveries.pointcache.gpu",
    ]

    def process(self, instance):
        from maya import cmds
        from reveries import utils, lib

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        cachename = "%s.abc" % instance.data["subset"]
        filename = "%s.ma" % instance.data["subset"]
        cachepath = "%s/%s" % (staging_dir, cachename)
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.GPUCache._stage"] = staging_dir
        instance.data["repr.GPUCache._hardlinks"] = [filename, cachename]
        instance.data["repr.GPUCache.entryFileName"] = filename

        if instance.data.get("staticCache"):
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)
        else:
            context_data = instance.context.data
            start = context_data["startFrame"]
            end = context_data["endFrame"]

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end

        # Collect root nodes
        assemblies = set()
        for node in instance.data["outCache"]:
            assemblies.add("|" + node[1:].split("|", 1)[0])
        assemblies = list(assemblies)

        # Collect all parent nodes
        out_hierarchy = set()
        for node in instance.data["outCache"]:
            out_hierarchy.add(node)
            out_hierarchy.update(lib.iter_uri(node, "|"))

        # Hide unwanted nodes (nodes that were not parents)
        attr_values = dict()
        for node in cmds.listRelatives(assemblies,
                                       allDescendents=True,
                                       type="transform",
                                       fullPath=True) or []:
            if node not in out_hierarchy:
                attr = node + ".visibility"

                locked = cmds.getAttr(attr, lock=True)
                has_connections = cmds.listConnections(attr,
                                                       source=True,
                                                       destination=False)
                if locked or has_connections:
                    continue

                attr_values[attr] = False

        instance.data["repr.GPUCache._delayRun"] = {
            "func": self.export_gpu,
            "args": [
                outpath,
                cachepath,
                cachename,
                start,
                end,
                assemblies,
                attr_values
            ],
        }

    def export_gpu(self,
                   outpath,
                   cachepath,
                   cachename,
                   start,
                   end,
                   assemblies,
                   attr_values):
        from reveries.maya import io, capsule
        from maya import cmds

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
        ):

            cmds.select(assemblies, replace=True, noExpand=True)

            with contextlib.nested(
                capsule.attribute_values(attr_values),
                # Mute animated visibility channels
                capsule.attribute_mute(list(attr_values.keys())),
            ):
                io.export_gpu(cachepath, start, end)
                io.wrap_gpu(outpath, [(cachename, "ROOT")])
