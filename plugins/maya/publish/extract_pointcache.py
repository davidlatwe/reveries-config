
import os
import contextlib

import pyblish.api

from reveries.maya import io, lib, capsule
from reveries.plugins import DelegatablePackageExtractor

from maya import cmds


class ExtractPointCache(DelegatablePackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract PointCache"
    families = [
        "reveries.animation",
        "reveries.pointcache",
    ]

    representations = [
        "Alembic",
        "FBXCache",
        "GPUCache",
    ]

    start_frame = 0
    end_frame = 0

    def extract(self):

        if self.data.get("static_cache"):
            self.start_frame = cmds.currentTime(query=True)
            self.end_frame = cmds.currentTime(query=True)
        else:
            context_data = self.context.data
            self.start_frame = context_data.get("startFrame")
            self.end_frame = context_data.get("endFrame")

        with contextlib.nested(
            capsule.no_refresh(),
            capsule.evaluation("off"),
        ):
                out_geo = self.data.get("out_animation", self.member)
                cmds.select(out_geo, replace=True, noExpand=True)

                super(ExtractPointCache, self).extract()

    def extract_Alembic(self):
        entry_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        io.export_alembic(entry_path, self.start_frame, self.end_frame)

    def extract_FBXCache(self):
        entry_file = self.file_name("fbx")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        # bake visible key
        with capsule.maintained_selection():
            lib.bake_hierarchy_visibility(
                cmds.ls(sl=True), self.start_frame, self.end_frame)
        io.export_fbx_set_pointcache("FBXCache_SET")
        io.export_fbx(entry_path)

    def extract_GPUCache(self):
        entry_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        io.export_gpu(entry_path, self.start_frame, self.end_frame)
