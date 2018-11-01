
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
        entry_file = self.file_name("abc")
        instances_file = self.file_name("json")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        instances_path = os.path.join(package_path, instances_file)

        self.log.info("Dumping instnaces data ..")
        with open(instances_path, "w") as fp:
            json.dump(self.data["instancesData"], fp, ensure_ascii=False)
            self.log.debug("Dumped: {}".format(instances_path))

        self.log.info("Extracting hierarchy ..")
        cmds.select(self.data["setdressRoots"])
        io.export_alembic(file=entry_path,
                          startFrame=1.0,
                          endFrame=1.0,
                          selection=True,
                          uvWrite=True,
                          writeVisibility=True,
                          writeCreases=True,
                          attr=[lib.AVALON_ID_ATTR_LONG])
        self.log.debug("Exported: {}".format(entry_path))

        cmds.select(clear=True)

    def extract_GPUCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        cmds.select(self.data["setdressRoots"])

        self.log.info("Extracting setDress GPUCache ..")

        frame = cmds.currentTime(query=True)
        io.export_gpu(cache_path, frame, frame)
        io.wrap_gpu(entry_path, cache_file, self.data["subset"])

        self.log.debug("Exported: {}".format(entry_path))
