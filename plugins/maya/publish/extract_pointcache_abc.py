
import contextlib
import pyblish.api
from reveries import utils


class ExtractPointCacheABC(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache (abc)"
    families = [
        "reveries.pointcache.abc",
    ]

    def process(self, instance):
        from maya import cmds

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        filename = "%s.abc" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.Alembic._stage"] = staging_dir
        instance.data["repr.Alembic._hardlinks"] = [filename]
        instance.data["repr.Alembic.entryFileName"] = filename

        if instance.data.get("staticCache"):
            start = cmds.currentTime(query=True)
            end = cmds.currentTime(query=True)
        else:
            context_data = instance.context.data
            start = context_data.get("startFrame")
            end = context_data.get("endFrame")

            instance.data["startFrame"] = start
            instance.data["endFrame"] = end

        euler_filter = instance.data.get("eulerFilter", False)
        root = instance.data["outCache"]

        instance.data["repr.Alembic._delayRun"] = {
            "func": self.export_alembic,
            "args": [
                root, outpath, start, end, euler_filter
            ],
        }

    def export_alembic(self, root, outpath, start, end, euler_filter):
        from reveries.maya import io, lib, capsule
        from maya import cmds

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
        ):
            # Selection may change if there are duplicate named nodes and
            # require instancing them to resolve

            with capsule.delete_after() as delete_bin:

                # (NOTE) We need to check any duplicate named nodes, or
                #        error will raised during Alembic export.
                result = lib.ls_duplicated_name(root)
                duplicated = [n for m in result.values() for n in m]
                if duplicated:
                    # Duplicate it so we could have a unique named new node
                    unique_named = list()
                    for node in duplicated:
                        new_nodes = cmds.duplicate(node,
                                                   inputConnections=True,
                                                   renameChildren=True)
                        new_nodes = cmds.ls(new_nodes, long=True)
                        unique_named.append(new_nodes[0])
                        # New nodes will be deleted after the export
                        delete_bin.extend(new_nodes)

                    # Replace duplicat named nodes with unique named
                    root = list(set(root) - set(duplicated)) + unique_named

                for node in set(root):
                    # (NOTE) If a descendent is instanced, it will appear only
                    #        once on the list returned.
                    root += cmds.listRelatives(node,
                                               allDescendents=True,
                                               fullPath=True,
                                               noIntermediate=True) or []
                root = list(set(root))
                cmds.select(root, replace=True, noExpand=True)

                io.export_alembic(
                    outpath,
                    start,
                    end,
                    selection=True,
                    renderableOnly=True,
                    writeVisibility=True,
                    writeCreases=True,
                    worldSpace=True,
                    eulerFilter=euler_filter,
                    attr=[
                        lib.AVALON_ID_ATTR_LONG,
                    ],
                    attrPrefix=[
                        "ai",  # Write out Arnold attributes
                    ],
                )
