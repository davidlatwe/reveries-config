
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
            cmds.select(self.data["outCache"], replace=True)
            super(ExtractPointCache, self).extract()

    def extract_Alembic(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        root = cmds.ls(sl=True, long=True)

        with capsule.maintained_selection():
            # Selection may change if there are duplicate named nodes and
            # require instancing them to resolve

            with capsule.delete_after() as delete_bin:

                # (NOTE) We need to check any duplicate named nodes, or
                #        error will raised during Alembic export.
                result = lib.ls_duplicated_name(root)
                duplicated = [n for m in result.values() for n in m]
                if duplicated:
                    # Create instance to avoid duplicated names
                    instanced = cmds.instance(duplicated)
                    # Instance nodes will be deleted after the export
                    delete_bin.extend(instanced)
                    # Update root nodes
                    root = list(set(root) - set(duplicated)) + instanced

                io.export_alembic(
                    cache_path,
                    self.start_frame,
                    self.end_frame,
                    selection=False,
                    renderableOnly=True,
                    writeCreases=True,
                    worldSpace=True,
                    root=root,
                    attr=[
                        lib.AVALON_ID_ATTR_LONG,
                    ],
                    attrPrefix=[
                        "ai",  # Write out Arnold attributes
                    ],
                )

        io.wrap_abc(entry_path, [(cache_file, "ROOT")])

        self.add_data({"entryFileName": entry_file})

    def extract_FBXCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("fbx")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        # bake visible key
        with capsule.maintained_selection():
            lib.bake_hierarchy_visibility(
                cmds.ls(sl=True), self.start_frame, self.end_frame)
        with io.export_fbx_set_pointcache("FBXCacheSET"):
            io.export_fbx(cache_path)

        io.wrap_fbx(entry_path, [(cache_file, "ROOT")])

        self.add_data({"entryFileName": entry_file})

    def extract_GPUCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        io.export_gpu(cache_path, self.start_frame, self.end_frame)
        io.wrap_gpu(entry_path, [(cache_file, "ROOT")])

        self.add_data({"entryFileName": entry_file})
