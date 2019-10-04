
import os
import contextlib

import pyblish.api
import avalon

from reveries.maya import io, lib, capsule, utils
from reveries.plugins import PackageExtractor

from maya import cmds


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

        DO_BAKE_THESE = [
            "focalLength",
        ]
        DO_BAKE_THESE += lib.TRANSFORM_ATTRS

        context_data = self.context.data
        self.start = context_data.get("startFrame")
        self.end = context_data.get("endFrame")
        self.step = self.data.get("bakeStep", 1.0)
        camera = cmds.ls(self.member, type="camera", long=True)[0]

        self.camera_uuid = utils.get_id(camera)

        cam_transform = cmds.listRelatives(camera,
                                           parent=True,
                                           fullPath=True)[0]

        donot_bake = [cam_transform + "." + attr for attr in DO_NOT_BAKE_THESE]
        do_bake = [cam_transform + "." + attr for attr in DO_BAKE_THESE]

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.attribute_states(donot_bake, lock=False, keyable=False),
            capsule.attribute_states(do_bake, lock=False, keyable=True),
            capsule.evaluation("off"),
        ):
            with capsule.delete_after() as delete_bin:

                # bake to worldspace
                frame_range = (self.start, self.end)
                baked_camera = lib.bake_to_world_space(cam_transform,
                                                       frame_range,
                                                       self.step)[0]
                delete_bin.append(baked_camera)

                cmds.select(baked_camera,
                            hierarchy=True,  # With shape
                            replace=True,
                            noExpand=True)

                super(ExtractCamera, self).extract()

    def extract_mayaAscii(self, packager):

        entry_file = packager.file_name("ma")
        package_path = packager.create_package()
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

        packager.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })

    def extract_Alembic(self, packager):

        entry_file = packager.file_name("abc")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)

        euler_filter = self.data.get("eulerFilter", False)

        with avalon.maya.maintained_selection():
            io.export_alembic(entry_path,
                              self.start,
                              self.end,
                              eulerFilter=euler_filter)

        packager.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })

    def extract_FBX(self, packager):

        entry_file = packager.file_name("fbx")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)

        with avalon.maya.maintained_selection():
            io.export_fbx_set_camera()
            io.export_fbx(entry_path)

        packager.add_data({
            "entryFileName": entry_file,
            "cameraUUID": self.camera_uuid,
            "startFrame": self.start,
            "endFrame": self.end,
            "byFrameStep": self.step,
        })
