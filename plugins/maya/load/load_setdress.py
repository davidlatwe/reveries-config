
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

    def apply_variation(self, data, assembly):
        import maya.cmds as cmds

        # Apply matrix to root node (if any matrix edits)
        matrix = data["matrix"]
        cmds.xform(assembly, objectSpace=True, matrix=matrix)

        # Apply matrix to components
        for transform, sub_matrix in self.parse_sub_matrix(data):
            if not transform:
                continue

            cmds.xform(transform,
                       objectSpace=True,
                       matrix=sub_matrix)

    def update_variation(self, data_new, data_old, assembly):
        import maya.cmds as cmds
        from reveries.lib import matrix_equals

        current_matrix = cmds.xform(assembly,
                                    query=True,
                                    matrix=True,
                                    objectSpace=True)
        original_matrix = data_old["matrix"]
        has_matrix_override = not matrix_equals(current_matrix,
                                                original_matrix)

        if has_matrix_override:
            self.log.warning("Matrix override preserved on %s",
                             data_new["namespace"])
        else:
            new_matrix = data_new["matrix"]
            cmds.xform(assembly, objectSpace=True, matrix=new_matrix)

        # Update matrix to components
        old_data_map = {t: m for t, m in self.parse_sub_matrix(data_old)}

        for transform, sub_matrix in self.parse_sub_matrix(data_new):
            if not transform:
                continue

            current_sub_matrix = cmds.xform(transform,
                                            query=True,
                                            matrix=True,
                                            objectSpace=True)

            original_sub_matrix = old_data_map.get(transform)

            if original_sub_matrix:
                has_matrix_override = not matrix_equals(current_sub_matrix,
                                                        original_sub_matrix)
            else:
                has_matrix_override = False

            if has_matrix_override:
                pass
            else:
                cmds.xform(transform, objectSpace=True, matrix=sub_matrix)

    def transform_by_id(self, nodes):
        import maya.cmds as cmds
        from reveries.maya.utils import get_id

        transform_id_map = dict()
        for transform in cmds.ls(nodes, type="transform", long=True):
            transform_id_map[get_id(transform)] = transform

        return transform_id_map

    def parse_sub_matrix(self, data):
        import maya.cmds as cmds

        current_NS = cmds.namespaceInfo(currentNamespace=True)
        for namespace, sub_matrix in data["subMatrix"].items():
            full_NS = current_NS + ":" + namespace
            nodes = cmds.namespaceInfo(full_NS, listOnlyDependencyNodes=True)

            transform_id_map = self.transform_by_id(nodes)

            for address in sub_matrix:
                if address == "GROUP":
                    name, matrix = sub_matrix[address].popitem()
                    transform = full_NS + ":" + name
                else:
                    transform = transform_id_map.get(address)
                    matrix = sub_matrix[address]

                yield transform, matrix
