
import avalon.api
import reveries.maya.plugins as plugins


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

    sub_representations = [
        "setPackage",
        "mayaBinary",
    ]

    def apply_variation(self, instance, assembly):

        import maya.cmds as cmds

        # Apply matrix to root node (if any matrix edits)
        matrix = instance["matrix"]
        cmds.xform(assembly, objectSpace=True, matrix=matrix)

    def update_variation(self):
        pass
