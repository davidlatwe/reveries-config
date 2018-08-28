
from reveries.maya.plugins import ReferenceLoader


class ModelLoader(ReferenceLoader):
    """Load the model"""

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.model"]

    representations = [
        "mayaBinary",
    ]

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        entry_path = self.file_path(data["entry_fname"])

        with maya.maintained_selection():
            nodes = cmds.file(entry_path,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))
        self[:] = nodes
