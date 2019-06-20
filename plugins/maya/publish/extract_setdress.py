
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
    """Extract hierarchical subsets' matrix data
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Set Dress"
    hosts = ["maya"]
    families = ["reveries.setdress"]

    representations = [
        "setPackage",
    ]

    def _collect_components_matrix(self, data, container):

        id_path = container_to_id_path(container)

        data["subMatrix"][id_path] = dict()
        data["hidden"][id_path] = list()

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

            # Collect visbility with matrix
            visibility = cmds.getAttr(transform + ".visibility")
            if not visibility:
                # Only record hidden nodes
                data["hidden"][id_path].append(address)

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
            data["hidden"] = dict()

            self._collect_components_matrix(data, container)

            for sub_container in walk_containers(container):
                subset_group = sub_container.get("subsetGroup")
                if (not subset_group or
                        not cmds.getAttr(subset_group + ".visibility")):
                    # Skip hidden child subset
                    continue
                self._collect_components_matrix(data, sub_container)

    def extract_setPackage(self):
        entry_file = self.file_name("abc")
        instances_file = self.file_name("json")
        package_path = self.create_package()
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

        self.add_data({
            "entryFileName": entry_file,
        })

        self.log.debug("Exported: {}".format(entry_path))

        cmds.select(clear=True)
