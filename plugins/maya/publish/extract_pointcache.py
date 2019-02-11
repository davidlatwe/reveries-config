
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
        "reveries.pointcache",
    ]

    representations = [
        "Alembic",
        "FBXCache",
        "GPUCache",
    ]

    def extract(self):

        if self.data.get("staticCache"):
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
            for namespace, out_geo in self.data["outCache"].items():
                self.out_name = namespace
                cmds.select(out_geo, replace=True)
                super(ExtractPointCache, self).extract()

    def add_cache_data(self, namespace, cache_file):
        relative = os.path.join(namespace, cache_file).replace("\\", "/")
        self.add_data({
            "cacheFiles": {
                namespace: relative,
            }
        })
        return relative, namespace

    def extract_Alembic(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package()

        cache_files = list()

        for namespace, out_geo in self.data["outCache"].items():
            cmds.select(out_geo, replace=True)

            cache_path = os.path.join(package_path, namespace, cache_file)

            root = cmds.ls(sl=True, long=True)

            io.export_alembic(cache_path,
                              self.start_frame,
                              self.end_frame,
                              selection=False,
                              renderableOnly=True,
                              writeCreases=True,
                              worldSpace=True,
                              root=root,
                              attr=[lib.AVALON_ID_ATTR_LONG])

            cache_data = self.add_cache_data(namespace, cache_file)
            cache_files.append(cache_data)

        entry_path = os.path.join(package_path, entry_file)
        io.wrap_abc(entry_path, cache_files)

        self.add_data({"entryFileName": entry_file})

    def extract_FBXCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("fbx")
        package_path = self.create_package()

        cache_files = list()

        for namespace, out_geo in self.data["outCache"].items():
            cmds.select(out_geo, replace=True)

            cache_path = os.path.join(package_path, namespace, cache_file)

            # bake visible key
            with capsule.maintained_selection():
                lib.bake_hierarchy_visibility(
                    cmds.ls(sl=True), self.start_frame, self.end_frame)
            with io.export_fbx_set_pointcache("FBXCacheSET"):
                io.export_fbx(cache_path)

            cache_data = self.add_cache_data(namespace, cache_file)
            cache_files.append(cache_data)

        entry_path = os.path.join(package_path, entry_file)
        io.wrap_fbx(entry_path, cache_files)

        self.add_data({"entryFileName": entry_file})

    def extract_GPUCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package()

        cache_files = list()

        for namespace, out_geo in self.data["outCache"].items():
            cmds.select(out_geo, replace=True)

            cache_path = os.path.join(package_path, namespace, cache_file)

            io.export_gpu(cache_path, self.start_frame, self.end_frame)

            cache_data = self.add_cache_data(namespace, cache_file)
            cache_files.append(cache_data)

        entry_path = os.path.join(package_path, entry_file)
        io.wrap_gpu(entry_path, cache_files)

        self.add_data({"entryFileName": entry_file})
