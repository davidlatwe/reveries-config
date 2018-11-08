
import avalon.api
import reveries.maya.plugins as plugins

reload(plugins)


class SetDressLoader(plugins.HierarchicalLoader, avalon.api.Loader):

    label = "Load Set Dress"
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
