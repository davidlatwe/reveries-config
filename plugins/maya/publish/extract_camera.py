
import os
import contextlib

import pyblish.api
import avalon

from reveries.maya import io, lib, capsule, utils
from reveries.plugins import PackageExtractor

from maya import cmds


DO_NOT_BAKE_THESE = [
    "motionBlurOverride",
    "aiUseGlobalShutter",
    "aiShutterStart",
    "aiShutterEnd",
    "aiShutterType",
    "aiEnableDOF",
    "aiFov",
    "aiHorizontalFov",
    "aiVerticalFov",
]


class ExtractCamera(PackageExtractor):
    """
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
    ]

    def extract(self):
        context_data = self.context.data
        self.start = context_data.get("startFrame")
        self.end = context_data.get("endFrame")
        self.step = self.data.get("bakeStep", 1.0)
        camera = cmds.ls(self.member, type="camera", long=True)[0]

        self.camera_uuid = utils.get_id(camera)

        donot_bake = [camera + "." + attr for attr in DO_NOT_BAKE_THESE]

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.attr_unkeyable(donot_bake),
            capsule.evaluation("off"),
            capsule.undo_chunk(),
        ):
            # bake to worldspace
            baked_camera = lib.bake_camera(camera,
                                           self.start,
                                           self.end,
                                           self.step)

            cmds.select(baked_camera,
                        hierarchy=True,  # With shape
                        replace=True,
                        noExpand=True)

            super(ExtractCamera, self).extract()

    def extract_mayaAscii(self):

        entry_file = self.file_name("ma")
        package_path = self.create_package()
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

        self.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })

    def extract_Alembic(self):

        entry_file = self.file_name("abc")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)

        euler_filter = self.data.get("eulerFilter", False)

        with avalon.maya.maintained_selection():
            io.export_alembic(entry_path,
                              self.start,
                              self.end,
                              eulerFilter=euler_filter)

        self.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })

    def extract_FBX(self):

        entry_file = self.file_name("fbx")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)

        with avalon.maya.maintained_selection():
            io.export_fbx_set_camera()
            io.export_fbx(entry_path)

        self.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })
