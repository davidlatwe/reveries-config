
import os
import contextlib

import pyblish.api
import avalon
import reveries.utils

from reveries.maya import io, lib, capsule
from reveries.plugins import DelegatablePackageExtractor

from maya import cmds


class ExtractCamera(DelegatablePackageExtractor):
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
        "mayaAscii",
        "Alembic",
        "FBX",
        "PNGSequence",
    ]

    def extract(self):
        context_data = self.context.data
        self.start = context_data.get("startFrame")
        self.end = context_data.get("endFrame")
        camera = cmds.ls(self.member, type="camera")[0]

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
        ):
            # bake to worldspace
            lib.bake_camera(camera, self.start, self.end)
            cmds.select(camera, replace=True, noExpand=True)

            super(ExtractCamera, self).extract()

    def extract_mayaAscii(self):

        entry_file = self.file_name("ma")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        with avalon.maya.maintained_selection():
            cmds.file(entry_path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False,
                      channels=True,  # allow animation
                      constraints=False,
                      shader=False,
                      expressions=False)

    def extract_Alembic(self):

        entry_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        with avalon.maya.maintained_selection():
            io.export_alembic(entry_path, self.start, self.end)

    def extract_FBX(self):

        entry_file = self.file_name("fbx")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        with avalon.maya.maintained_selection():
            io.export_fbx_set_camera()
            io.export_fbx(entry_path)

    def extract_PNGSequence(self):

        if not self.data.get("capture_png"):
            return

        entry_file = self.file_name("png")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        width, height = reveries.utils.get_resolution_data()
        camera = cmds.ls(self.member, type="camera")[0]
        io.capture_seq(camera,
                       entry_path,
                       self.start,
                       self.end,
                       width,
                       height)
