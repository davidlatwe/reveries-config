
import contextlib
import pyblish.api


class ExtractModelAsAlembic(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Model (abc)"
    families = [
        "reveries.model",
    ]

    def process(self, instance):
        from reveries import utils

        staging_dir = utils.stage_dir()
        filename = "%s.abc" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        nodes = instance[:]

        instance.data["repr.Alembic._stage"] = staging_dir
        instance.data["repr.Alembic._files"] = [filename]
        instance.data["repr.Alembic.entryFileName"] = filename

        self.extract_alembic(nodes, outpath)

    def extract_alembic(self, nodes, outpath):
        import maya.cmds as cmds
        from reveries.maya import capsule, io, lib

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(nodes),
            capsule.no_smooth_preview(),
            capsule.maintained_selection(),
            capsule.without_extension(),
        ):

            cmds.select(nodes, noExpand=True)

            frame = cmds.currentTime(query=True)
            io.export_alembic(
                outpath,
                frame,
                frame,
                selection=True,
                renderableOnly=True,
                writeCreases=True,
                worldSpace=True,
                uvWrite=True,
                writeUVSets=True,
                attr=[
                    lib.AVALON_ID_ATTR_LONG,
                ],
                attrPrefix=[
                    "ai",  # Write out Arnold attributes
                ],
            )
