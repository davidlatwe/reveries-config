
import json
import pyblish.api


class ExtractSetDress(pyblish.api.InstancePlugin):
    """Extract hierarchical subsets' matrix data
    """

    order = pyblish.api.ExtractorOrder
    label = "Extract Set Dress"
    hosts = ["maya"]
    families = ["reveries.setdress"]

    def process(self, instance):
        from maya import cmds
        from reveries import utils
        from reveries.maya import io, lib

        staging_dir = utils.stage_dir()
        filename = "%s.abc" % instance.data["subset"]
        members = "%s.json" % instance.data["subset"]

        outpath = "%s/%s" % (staging_dir, filename)
        memberpath = "%s/%s" % (staging_dir, members)

        instance.data["repr.setPackage._stage"] = staging_dir
        instance.data["repr.setPackage._files"] = [filename, members]
        instance.data["repr.setPackage.entryFileName"] = filename

        self.parse_matrix(instance)

        self.log.info("Dumping setdress members data ..")
        with open(memberpath, "w") as fp:
            json.dump(instance.data["subsetData"], fp, ensure_ascii=False)
            self.log.debug("Dumped: {}".format(memberpath))

        self.log.info("Extracting hierarchy ..")
        cmds.select(instance.data["subsetSlots"])
        io.export_alembic(file=outpath,
                          startFrame=1.0,
                          endFrame=1.0,
                          selection=True,
                          uvWrite=True,
                          writeUVSets=True,
                          writeVisibility=True,
                          writeCreases=True,
                          attr=[lib.AVALON_ID_ATTR_LONG])

        self.log.debug("Exported: {}".format(outpath))

        cmds.select(clear=True)

    def _collect_components_matrix(self, data, container):
        from maya import cmds
        from reveries.lib import DEFAULT_MATRIX, matrix_equals
        from reveries.maya import utils as maya_utils
        from reveries.maya import hierarchy

        id_path = hierarchy.container_to_id_path(container)

        data["subMatrix"][id_path] = dict()
        data["inheritsTransform"][id_path] = dict()
        data["hidden"][id_path] = dict()

        nodes = cmds.sets(container["objectName"], query=True, nodesOnly=True)

        # Alembic, If any..
        # (NOTE) Shouldn't be extracted here with matrix, need decouple
        if container["loader"] == "PointCacheReferenceLoader":
            abc = cmds.ls(nodes, type="AlembicNode")
            if abc:
                abc = abc[0]  # Should have one and only one alembic node
                data["alembic"][id_path] = [
                    cmds.getAttr(abc + ".speed"),
                    cmds.getAttr(abc + ".offset"),
                    cmds.getAttr(abc + ".cycleType"),
                ]

        # Transform Matrix
        #
        transforms = cmds.ls(nodes, type="transform", referencedNodes=True)
        transforms = set(transforms) - set(cmds.ls(transforms, type=["joint"]))

        for transform in transforms:
            matrix = cmds.xform(transform,
                                query=True,
                                matrix=True,
                                objectSpace=True)

            if matrix_equals(matrix, DEFAULT_MATRIX):
                matrix = "<default>"

            address = maya_utils.get_id(transform)
            short = transform.split("|")[-1].split(":")[-1]
            # (NOTE) New data model for duplicated AvalonID..
            #   Use transform node's short name as a buffer for AvalonID
            #   duplication..
            if address not in data["subMatrix"][id_path]:
                data["subMatrix"][id_path][address] = dict()
            data["subMatrix"][id_path][address][short] = matrix

            # Collect `inheritsTransform`...
            inherits = cmds.getAttr(transform + ".inheritsTransform")
            if address not in data["inheritsTransform"][id_path]:
                # (NOTE) New data model for duplicated AvalonID..
                data["inheritsTransform"][id_path][address] = dict()
            data["inheritsTransform"][id_path][address][short] = inherits

            # Collect visbility with matrix
            visibility = cmds.getAttr(transform + ".visibility")
            if not visibility:
                # Only record hidden nodes
                if address not in data["hidden"][id_path]:
                    # (NOTE) New data model for duplicated AvalonID..
                    data["hidden"][id_path][address] = list()
                data["hidden"][id_path][address].append(short)

        # Collect subseet group node's matrix
        subset_group = container["subsetGroup"]

        matrix = cmds.xform(subset_group,
                            query=True,
                            matrix=True,
                            objectSpace=True)
        inherits = cmds.getAttr(subset_group + ".inheritsTransform")

        name = subset_group.rsplit(":", 1)[-1]
        data["subMatrix"][id_path]["GROUP"] = {name: matrix}
        data["inheritsTransform"][id_path]["GROUP"] = {name: inherits}

    def parse_matrix(self, instance):
        from maya import cmds
        from reveries.maya import hierarchy

        for data in instance.data["subsetData"]:
            container = data.pop("_container")
            subset_group = container["subsetGroup"]

            matrix = cmds.xform(subset_group,
                                query=True,
                                matrix=True,
                                objectSpace=True)
            data["matrix"] = matrix

            data["subMatrix"] = dict()
            data["inheritsTransform"] = dict()
            data["hidden"] = dict()
            data["alembic"] = dict()

            self._collect_components_matrix(data, container)

            for sub_container in hierarchy.walk_containers(container):
                subset_group = sub_container.get("subsetGroup")
                if (not subset_group or
                        not cmds.getAttr(subset_group + ".visibility")):
                    # Skip hidden child subset
                    continue
                self._collect_components_matrix(data, sub_container)
