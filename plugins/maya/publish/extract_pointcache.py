
import os
import contextlib

import pyblish.api
import avalon.maya

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
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            avalon.maya.maintained_selection(),
        ):
            out_geo = self.data.get("out_animation", self.member)
            cmds.select(out_geo, replace=True)

            super(ExtractPointCache, self).extract()

    def extract_Alembic(self):
        entry_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        root = cmds.ls(sl=True, long=True)

        io.export_alembic(entry_path,
                          self.start_frame,
                          self.end_frame,
                          selection=False,
                          renderableOnly=True,
                          writeCreases=True,
                          worldSpace=True,
                          root=root,
                          attr=[lib.AVALON_ID_ATTR_LONG])

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
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        io.export_gpu(cache_path, self.start_frame, self.end_frame)
        io.wrap_gpu(entry_path, cache_file, self.data["subset"])
