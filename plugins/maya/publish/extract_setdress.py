
import os
import json
import pyblish.api
from maya import cmds
from reveries.plugins import PackageExtractor
from reveries.maya import io, lib


class ExtractSetDress(PackageExtractor):
    """Produce an alembic of just point positions and normals.

    Positions and normals are preserved, but nothing more,
    for plain and predictable point caches.

    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Set Dress"
    hosts = ["maya"]
    families = ["reveries.setdress"]

    representations = [
        "setPackage",
        "GPUCache",
    ]

    def extract_setPackage(self):
        entry_file = self.file_name("json")
        hierarchy_file = self.file_name("abc")

        self.log.info("Dumping package data ..")
        with open(entry_file, "w") as filepath:
            json.dump(self.data["packageData"], filepath, ensure_ascii=False)

        self.log.info("Extracting hierarchy ..")
        cmds.select(self.data["setdressRoots"])
        io.export_alembic(file=hierarchy_file,
                          startFrame=1.0,
                          endFrame=1.0,
                          selection=True,
                          uvWrite=True,
                          writeVisibility=True,
                          writeCreases=True,
                          attr=[lib.AVALON_ID_ATTR_LONG])

        # Remove data
        self.data.pop("packageData", None)

        cmds.select(clear=True)

    def extract_GPUCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        cmds.select(self.data["setdressRoots"])

        frame = cmds.currentTime(query=True)
        io.export_gpu(cache_path, frame, frame)
        io.wrap_gpu(entry_path, cache_file, self.data["subset"])
