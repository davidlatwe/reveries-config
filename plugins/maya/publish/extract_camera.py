
import os
import pyblish.api
import avalon
import reveries.pipeline
import reveries.maya.capsule
import reveries.maya.lib
import reveries.maya.io

from maya import cmds
from reveries.maya.vendor import capture


class ExtractCamera(pyblish.api.InstancePlugin):
    """
    TODO: publish multiple cameras
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Camera"
    families = [
        "reveries.camera",
    ]

    def process(self, instance):
        dirname = reveries.pipeline.temp_dir()
        name = instance.data["name"]

        context_data = instance.context.data
        start = context_data.get("startFrame")
        end = context_data.get("endFrame")
        camera = cmds.ls(instance[:], type="camera")[0]

        instance.data["stagingDir"] = dirname
        if "files" not in instance.data:
            instance.data["files"] = list()

        with reveries.maya.capsule.no_refresh(with_undo=True):
            with reveries.maya.capsule.evaluation("off"):

                # bake to worldspace
                reveries.maya.lib.bake_camera(camera, start, end)

                cmds.select(camera, replace=True, noExpand=True)

                # alembic
                filename = "{}.abc".format(name)
                out_path = os.path.join(dirname, filename)
                with avalon.maya.maintained_selection():
                    reveries.maya.io.export_alembic(out_path, start, end)
                instance.data["files"].append(filename)

                # fbx
                filename = "{}.fbx".format(name)
                out_path = os.path.join(dirname, filename)
                with avalon.maya.maintained_selection():
                    reveries.maya.io.export_fbx_set_camera()
                    reveries.maya.io.export_fbx(out_path)
                instance.data["files"].append(filename)

                # mayaAscii
                filename = "{}.ma".format(name)
                out_path = os.path.join(dirname, filename)
                with avalon.maya.maintained_selection():
                    cmds.file(out_path,
                              force=True,
                              typ="mayaAscii",
                              exportSelected=True,
                              preserveReferences=False,
                              constructionHistory=False,
                              channels=True,  # allow animation
                              constraints=False,
                              shader=False,
                              expressions=False)
                instance.data["files"].append(filename)
