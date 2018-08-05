
import os
import pyblish.api
import avalon
import reveries.utils
import reveries.base
import reveries.maya.capsule
import reveries.maya.lib
import reveries.maya.io

from maya import cmds


class ExtractCamera(reveries.base.DelegatableExtractor):
    """
    TODO: publish multiple cameras
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Camera"
    families = [
        "reveries.camera",
    ]

    representations = [
        reveries.base.repr_obj("mayaAscii", "ma"),
        reveries.base.repr_obj("Alembic", "abc"),
        reveries.base.repr_obj("FBX", "fbx"),
        reveries.base.repr_obj("PNGSequence", "png"),
    ]

    def dispatch(self):
        context_data = self.context.data
        self.start = context_data.get("startFrame")
        self.end = context_data.get("endFrame")
        camera = cmds.ls(self.member, type="camera")[0]

        with reveries.maya.capsule.no_refresh(with_undo=True):
            with reveries.maya.capsule.evaluation("off"):
                # bake to worldspace
                reveries.maya.lib.bake_camera(camera, self.start, self.end)
                cmds.select(camera, replace=True, noExpand=True)

                self.extract()

    def extract_mayaAscii(self, representation):

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        with avalon.maya.maintained_selection():
            cmds.file(out_path,
                      force=True,
                      typ=representation,
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False,
                      channels=True,  # allow animation
                      constraints=False,
                      shader=False,
                      expressions=False)
        self.stage_files(representation)

    def extract_Alembic(self, representation):

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        with avalon.maya.maintained_selection():
            reveries.maya.io.export_alembic(out_path, self.start, self.end)

        self.stage_files(representation)

    def extract_FBX(self, representation):

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        with avalon.maya.maintained_selection():
            reveries.maya.io.export_fbx_set_camera()
            reveries.maya.io.export_fbx(out_path)

        self.stage_files(representation)

    def extract_PNGSequence(self, representation):

        if not self.data.get("capture_png"):
            return

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        width, height = reveries.utils.get_resolution_data()
        camera = cmds.ls(self.member, type="camera")[0]
        reveries.maya.io.capture_seq(camera,
                                     out_path,
                                     self.start,
                                     self.end,
                                     width,
                                     height)

        self.stage_files(representation)
