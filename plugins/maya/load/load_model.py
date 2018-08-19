
from reveries.plugins import repr_obj
from reveries.maya.plugins import ReferenceLoader


class ModelLoader(ReferenceLoader):
    """Load the model"""

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.model"]

    representations = [
        repr_obj("mayaBinary", "mb"),
    ]

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.entry_path,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))
        self[:] = nodes
