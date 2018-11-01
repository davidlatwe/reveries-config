
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

    def process_subset(self, instance, vessel, namespace, group, options):

        import maya.cmds as cmds
        from reveries.maya.lib import to_namespace

        # Apply matrix to root node (if any matrix edits)
        matrix = instance["matrix"]
        cmds.xform(vessel, objectSpace=True, matrix=matrix)

        # Parent into the setdress hierarchy
        # Namespace is missing from parent node(s), add namespace
        # manually
        parent = group + to_namespace(instance["root"], namespace)
        cmds.parent(vessel, parent, relative=True)

    def update(self, container, representation):
        pass

    def remove(self, container):
        pass
