
import os
import json
import pyblish.api
from maya import cmds
from reveries.plugins import PackageExtractor
from reveries.maya import io, lib, utils
from reveries.maya.hierarchy import (
    walk_containers,
    container_to_id_path,
)
from reveries.lib import DEFAULT_MATRIX, matrix_equals


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

    def _collect_components_matrix(self, data, container):

        id_path = container_to_id_path(container)

        data["subMatrix"][id_path] = dict()

        members = cmds.sets(container["objectName"], query=True)
        transforms = cmds.ls(members,
                             type="transform",
                             referencedNodes=True)

        for transform in transforms:
            matrix = cmds.xform(transform,
                                query=True,
                                matrix=True,
                                objectSpace=True)

            if matrix_equals(matrix, DEFAULT_MATRIX):
                matrix = "<default>"

            address = utils.get_id(transform)
            data["subMatrix"][id_path][address] = matrix

        # Collect subseet group node's matrix
        subset_group = container["subsetGroup"]

        matrix = cmds.xform(subset_group,
                            query=True,
                            matrix=True,
                            objectSpace=True)

        if matrix_equals(matrix, DEFAULT_MATRIX):
            return

        name = subset_group.rsplit(":", 1)[-1]
        data["subMatrix"][id_path]["GROUP"] = {name: matrix}

    def parse_matrix(self):
        for data in self.data["subsetData"]:
            container = data.pop("_container")
            subset_group = container["subsetGroup"]

            matrix = cmds.xform(subset_group,
                                query=True,
                                matrix=True,
                                objectSpace=True)
            data["matrix"] = matrix

            data["subMatrix"] = dict()

            self._collect_components_matrix(data, container)

            for sub_container in walk_containers(container):
                self._collect_components_matrix(data, sub_container)

    def extract_setPackage(self):
        entry_file = self.file_name("abc")
        instances_file = self.file_name("json")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        instances_path = os.path.join(package_path, instances_file)

        self.parse_matrix()

        self.log.info("Dumping setdress members data ..")
        with open(instances_path, "w") as fp:
            json.dump(self.data["subsetData"], fp, ensure_ascii=False)
            self.log.debug("Dumped: {}".format(instances_path))

        self.log.info("Extracting hierarchy ..")
        cmds.select(self.data["subsetSlots"])
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

        cmds.select(self.data["subsetSlots"])

        self.log.info("Extracting setDress GPUCache ..")

        frame = cmds.currentTime(query=True)
        io.export_gpu(cache_path, frame, frame)
        io.wrap_gpu(entry_path, cache_file, self.data["subset"])

        self.log.debug("Exported: {}".format(entry_path))
