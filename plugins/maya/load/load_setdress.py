
import contextlib
import avalon.api
from reveries.maya.plugins import HierarchicalLoader


class SetDressLoader(HierarchicalLoader, avalon.api.Loader):

    label = "Load SetDress"
    order = -9
    icon = "tree"
    color = "green"

    hosts = ["maya"]

    families = ["reveries.setdress"]

    representations = [
        "setPackage"
    ]

    def has_input_connections(self, node, attributes):
        import maya.cmds as cmds

        for attr in attributes:
            conns = cmds.listConnections(node + "." + attr,
                                         source=True,
                                         destination=False,
                                         plugs=False)
            if conns:
                return True
        return False

    @contextlib.contextmanager
    def keep_scale_pivot(self, node):
        import maya.cmds as cmds
        scale_pivot = cmds.xform(node, query=True, scalePivot=True)
        try:
            yield
        finally:
            cmds.xform(node, scalePivot=scale_pivot)

    def apply_variation(self, data, container):
        """
        """
        import maya.cmds as cmds
        from reveries.maya.lib import TRANSFORM_ATTRS

        assembly = container["subsetGroup"]

        # Apply matrix to root node (if any matrix edits)
        matrix = data["matrix"]
        with self.keep_scale_pivot(assembly):
            cmds.xform(assembly, objectSpace=True, matrix=matrix)

        # Apply matrix to components
        for transform, sub_matrix, is_hidden in self.parse_sub_matrix(data):
            if not transform:
                continue

            if transform == "<alembic>":
                abc = transform = is_hidden
                alembic = sub_matrix
                cmds.setAttr(abc + ".speed", alembic[0])
                cmds.setAttr(abc + ".offset", alembic[1])
                cmds.setAttr(abc + ".cycleType", alembic[2])
                continue

            if (is_hidden
                    and not self.has_input_connections(transform,
                                                       ["visibility"])):
                cmds.setAttr(transform + ".visibility", False)

            if self.has_input_connections(transform, TRANSFORM_ATTRS):
                # Possible an object that is part of pointcache
                continue

            with self.keep_scale_pivot(transform):
                cmds.xform(transform,
                           objectSpace=True,
                           matrix=sub_matrix)

    def update_variation(self, data_new, data_old, container, force=False):
        """
        """
        import maya.cmds as cmds
        from reveries.lib import matrix_equals
        from reveries.maya.lib import TRANSFORM_ATTRS

        assembly = container["subsetGroup"]

        current_matrix = cmds.xform(assembly,
                                    query=True,
                                    matrix=True,
                                    objectSpace=True)
        origin_matrix = data_old["matrix"]
        has_matrix_override = not matrix_equals(current_matrix,
                                                origin_matrix)

        if has_matrix_override and not force:
            self.log.warning("Matrix override preserved on %s",
                             assembly)
        elif self.has_input_connections(assembly, TRANSFORM_ATTRS):
            self.log.warning("Input connection preserved on %s",
                             assembly)
        else:
            new_matrix = data_new["matrix"]
            with self.keep_scale_pivot(assembly):
                cmds.xform(assembly, objectSpace=True, matrix=new_matrix)

        # Update matrix to components
        old_data_map = {t: (m, h) for t, m, h in
                        self.parse_sub_matrix(data_old)}

        for parsed in self.parse_sub_matrix(data_new):
            transform, sub_matrix, is_hidden = parsed

            if not transform:
                continue

            origin_sub_matrix, origin_hidden = old_data_map.get(transform,
                                                                (None, False))

            _tag = transform
            if _tag == "<alembic>":
                abc = transform = is_hidden
                alembic = sub_matrix

                current_sub_matrix = [
                    cmds.getAttr(abc + ".speed"),
                    cmds.getAttr(abc + ".offset"),
                    cmds.getAttr(abc + ".cycleType"),
                ]
                current_hidden = None
                attributes = ["speed", "offset", "cycleType"]

            else:
                current_sub_matrix = cmds.xform(transform,
                                                query=True,
                                                matrix=True,
                                                objectSpace=True)
                current_hidden = not cmds.getAttr(transform + ".visibility")
                attributes = TRANSFORM_ATTRS

            # Updating matrix
            if origin_sub_matrix:
                has_matrix_override = not matrix_equals(current_sub_matrix,
                                                        origin_sub_matrix)
            else:
                has_matrix_override = False

            if has_matrix_override and not force:
                self.log.warning("Sub-Matrix override preserved on %s",
                                 transform)
            elif self.has_input_connections(transform, attributes):
                self.log.warning("Input connection preserved on %s",
                                 transform)
            elif _tag == "<alembic>":
                cmds.setAttr(abc + ".speed", alembic[0])
                cmds.setAttr(abc + ".offset", alembic[1])
                cmds.setAttr(abc + ".cycleType", alembic[2])
            else:
                with self.keep_scale_pivot(transform):
                    cmds.xform(transform, objectSpace=True, matrix=sub_matrix)

            if _tag == "<alembic>":
                continue

            # Updating visibility
            if self.has_input_connections(transform, ["visibility"]):
                continue

            if origin_hidden:
                has_hidden_override = current_hidden != origin_hidden
            else:
                has_hidden_override = False

            if has_hidden_override and not force:
                self.log.warning("Visibility override preserved on %s",
                                 transform)
            elif force:
                if current_hidden and not is_hidden:
                    cmds.setAttr(transform + ".visibility", True)
                elif not current_hidden and is_hidden:
                    cmds.setAttr(transform + ".visibility", False)
            else:
                if origin_hidden and not is_hidden:
                    cmds.setAttr(transform + ".visibility", True)
                elif not origin_hidden and is_hidden:
                    cmds.setAttr(transform + ".visibility", False)

    def transform_by_id(self, nodes):
        """
        """
        import maya.cmds as cmds
        from reveries.maya.utils import get_id

        transform_id_map = dict()
        for transform in cmds.ls(nodes, type="transform"):
            id = get_id(transform)
            if id not in transform_id_map:
                # (NOTE) New data model for duplicated AvalonID..
                transform_id_map[id] = list()
            transform_id_map[id].append(transform)

        return transform_id_map

    def parse_sub_matrix(self, data):
        """
        """
        import maya.cmds as cmds
        from reveries.lib import DEFAULT_MATRIX
        from reveries.maya.hierarchy import container_from_id_path
        from reveries.maya.pipeline import get_group_from_container

        def d(mx):
            return DEFAULT_MATRIX if mx == "<default>" else mx

        current_NS = cmds.namespaceInfo(currentNamespace=True,
                                        absoluteName=True)
        for container_id, sub_matrix in data["subMatrix"].items():

            container = container_from_id_path(self, container_id, current_NS)
            if not container:
                # Possibly been removed in parent asset
                continue

            full_NS = cmds.getAttr(container + ".namespace")
            nodes = cmds.namespaceInfo(full_NS, listOnlyDependencyNodes=True)
            # Collect hidden nodes' address
            hidden = data.get("hidden", {}).get(container_id, {})

            transform_id_map = self.transform_by_id(nodes)

            for address in sub_matrix:
                is_hidden = False

                if address == "GROUP":
                    _, matrix = sub_matrix[address].popitem()
                    transform = get_group_from_container(container)

                    yield transform, d(matrix), is_hidden

                else:
                    transforms = transform_id_map.get(address)
                    matrix = sub_matrix[address]

                    if address in hidden and transforms is not None:
                        is_hidden = True

                    if isinstance(matrix, dict):
                        # (NOTE) New data model for duplicated AvalonID..
                        for transform in transforms or []:
                            short = transform.split("|")[-1].split(":")[-1]
                            _matrix = matrix.get(short)

                            if _matrix is None:
                                continue

                            _hidden = is_hidden and short in hidden[address]

                            yield transform, d(_matrix), _hidden

                    else:
                        transform = transforms[-1] if transforms else None

                        yield transform, d(matrix), is_hidden

            # Alembic, If any..
            # (NOTE) Shouldn't be loaded here with matrix, need decouple
            alembic = data.get("alembic", {}).get(container_id)
            if alembic:
                abc = cmds.ls(nodes, type="AlembicNode")
                if abc:
                    abc = abc[0]  # Should have one and only one alembic node
                    yield "<alembic>", alembic, abc
