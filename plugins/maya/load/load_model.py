
import avalon.api
from reveries.maya.plugins import ReferenceLoader


class ModelLoader(ReferenceLoader, avalon.api.Loader):
    """Load the model"""

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.model"]

    representations = [
        "mayaBinary",
        "GPUCache",
    ]

    def process_reference(self, context, name, namespace, options):

        import maya.cmds as cmds
        from avalon import maya
        from reveries.maya.lib import get_highest_in_hierarchy

        representation = context["representation"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        group_name = "{}:{}".format(namespace, name)

        with maya.maintained_selection():
            nodes = cmds.file(entry_path,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=group_name)
        self[:] = nodes

        transforms = cmds.ls(nodes, type="transform", long=True)
        self.interface = get_highest_in_hierarchy(transforms)

        return group_name

    def switch(self, container, representation):
        self.update(container, representation)
