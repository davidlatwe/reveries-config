
import avalon.api
from reveries.maya.plugins import NestedLoader


class SetDressLoader(NestedLoader, avalon.api.Loader):

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

    def process_subset(self, instance, assembly):

        import maya.cmds as cmds

        # Apply matrix to root node (if any matrix edits)
        matrix = instance["matrix"]
        cmds.xform(assembly, objectSpace=True, matrix=matrix)
