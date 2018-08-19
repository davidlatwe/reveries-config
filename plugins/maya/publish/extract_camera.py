
import os
import pyblish.api
import avalon
import reveries.utils

from reveries.maya import io, lib, capsule
from reveries.plugins import repr_obj, DelegatableExtractor

from maya import cmds


class ExtractCamera(DelegatableExtractor):
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
        repr_obj("mayaAscii", "ma"),
        repr_obj("Alembic", "abc"),
        repr_obj("FBX", "fbx"),
        repr_obj("PNGSequence", "png"),
    ]

    def dispatch(self):
        context_data = self.context.data
        self.start = context_data.get("startFrame")
        self.end = context_data.get("endFrame")
        camera = cmds.ls(self.member, type="camera")[0]

        with capsule.no_refresh(with_undo=True):
            with capsule.evaluation("off"):
                # bake to worldspace
                lib.bake_camera(camera, self.start, self.end)
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
            io.export_alembic(out_path, self.start, self.end)

        self.stage_files(representation)

    def extract_FBX(self, representation):

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        with avalon.maya.maintained_selection():
            io.export_fbx_set_camera()
            io.export_fbx(out_path)

        self.stage_files(representation)

    def extract_PNGSequence(self, representation):

        if not self.data.get("capture_png"):
            return

        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        width, height = reveries.utils.get_resolution_data()
        camera = cmds.ls(self.member, type="camera")[0]
        io.capture_seq(camera,
                       out_path,
                       self.start,
                       self.end,
                       width,
                       height)

        self.stage_files(representation)
