
import os
import pyblish.api

from reveries.maya import io, lib, capsule
from reveries.plugins import repr_obj, DelegatableExtractor

from maya import cmds


class ExtractPointCache(DelegatableExtractor):
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
        repr_obj("Alembic", "abc"),
        repr_obj("FBXCache", "fbx"),
        repr_obj("GPUCache", "abc"),
    ]

    start_frame = 0
    end_frame = 0

    def dispatch(self):

        if self.data.get("static_cache"):
            self.start_frame = cmds.currentTime(query=True)
            self.end_frame = cmds.currentTime(query=True)
        else:
            context_data = self.context.data
            self.start_frame = context_data.get("startFrame")
            self.end_frame = context_data.get("endFrame")

        with capsule.no_refresh(with_undo=True):
            with capsule.evaluation("off"):
                out_geo = self.data.get("out_animation", self.member)
                cmds.select(out_geo, replace=True, noExpand=True)
                self.extract()

    def extract_Alembic(self, representation):
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        io.export_alembic(out_path, self.start_frame, self.end_frame)

        self.stage_files(representation)

    def extract_FBXCache(self, representation):
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        # bake visible key
        with capsule.maintained_selection():
            lib.bake_hierarchy_visibility(
                cmds.ls(sl=True), self.start_frame, self.end_frame)
        io.export_fbx_set_pointcache("ReveriesCache")
        io.export_fbx(out_path)

        self.stage_files(representation)

    def extract_GPUCache(self, representation):
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        io.export_gpu(out_path, self.start_frame, self.end_frame)

        self.stage_files(representation)
