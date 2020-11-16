
import contextlib
import pyblish.api


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
        from reveries import utils

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
            start = context_data["startFrame"]
            end = context_data["endFrame"]

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
            # (monument): We once needed to cleanup leaf name duplicated
            #   nodes with `lib.ls_duplicated_name`, and somehow now we
            #   don't. Just putting notes here in case we bump into
            #   alembic export runtime error again.

            for node in set(root):
                # (NOTE) If a descendent is instanced, it will appear only
                #        once on the list returned.
                root += cmds.listRelatives(node,
                                           allDescendents=True,
                                           fullPath=True,
                                           noIntermediate=True) or []
            root = list(set(root))
            cmds.select(root, replace=True, noExpand=True)

            def _export_alembic():
                io.export_alembic(
                    outpath,
                    start,
                    end,
                    selection=True,
                    renderableOnly=True,
                    writeVisibility=True,
                    writeCreases=True,
                    worldSpace=True,
                    uvWrite=True,
                    writeUVSets=True,
                    eulerFilter=euler_filter,
                    attr=[
                        lib.AVALON_ID_ATTR_LONG,
                    ],
                    attrPrefix=[
                        "ai",  # Write out Arnold attributes
                        "avnlook_",  # Write out lookDev controls
                    ],
                )

            auto_retry = 1
            while auto_retry:
                try:
                    _export_alembic()
                except RuntimeError as err:
                    if auto_retry:
                        # (NOTE) Auto re-try export
                        # For unknown reason, some artist may encounter
                        # runtime error when exporting but re-run the
                        # publish without any change will resolve.
                        auto_retry -= 1
                        self.log.warning(err)
                        self.log.warning("Retrying...")
                    else:
                        raise err
                else:
                    break
