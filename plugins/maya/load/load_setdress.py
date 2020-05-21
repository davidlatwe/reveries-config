
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

    def has_input_connections(self, node):
        import maya.cmds as cmds
        from reveries.maya.lib import TRANSFORM_ATTRS

        for attr in TRANSFORM_ATTRS:
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

        assembly = container["subsetGroup"]

        # Apply matrix to root node (if any matrix edits)
        matrix = data["matrix"]
        with self.keep_scale_pivot(assembly):
            cmds.xform(assembly, objectSpace=True, matrix=matrix)

        # Apply matrix to components
        for transform, sub_matrix, is_hidden in self.parse_sub_matrix(data):
            if not transform:
                continue

            with self.keep_scale_pivot(transform):
                cmds.xform(transform,
                           objectSpace=True,
                           matrix=sub_matrix)
            if is_hidden:
                cmds.setAttr(transform + ".visibility", False)

    def update_variation(self, data_new, data_old, container, force=False):
        """
        """
        import maya.cmds as cmds
        from reveries.lib import matrix_equals

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
        elif self.has_input_connections(assembly):
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

            current_sub_matrix = cmds.xform(transform,
                                            query=True,
                                            matrix=True,
                                            objectSpace=True)
            current_hidden = not cmds.getAttr(transform + ".visibility")

            origin_sub_matrix, origin_hidden = old_data_map.get(transform,
                                                                (None, False))

            # Updating matrix
            if origin_sub_matrix:
                has_matrix_override = not matrix_equals(current_sub_matrix,
                                                        origin_sub_matrix)
            else:
                has_matrix_override = False

            if has_matrix_override and not force:
                self.log.warning("Sub-Matrix override preserved on %s",
                                 transform)
            elif self.has_input_connections(transform):
                self.log.warning("Input connection preserved on %s",
                                 transform)
            else:
                with self.keep_scale_pivot(transform):
                    cmds.xform(transform, objectSpace=True, matrix=sub_matrix)

            # Updating visibility
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
            transform_id_map[get_id(transform)] = transform

        return transform_id_map

    def parse_sub_matrix(self, data):
        """
        """
        import maya.cmds as cmds
        from reveries.lib import DEFAULT_MATRIX
        from reveries.maya.hierarchy import container_from_id_path
        from reveries.maya.pipeline import get_group_from_container

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
            hidden = data.get("hidden", {}).get(container_id, [])

            transform_id_map = self.transform_by_id(nodes)

            for address in sub_matrix:
                is_hidden = False

                if address == "GROUP":
                    _, matrix = sub_matrix[address].popitem()
                    transform = get_group_from_container(container)

                else:
                    transform = transform_id_map.get(address)
                    matrix = sub_matrix[address]

                    if address in hidden and transform is not None:
                        is_hidden = True

                if matrix == "<default>":
                    matrix = DEFAULT_MATRIX

                yield transform, matrix, is_hidden
