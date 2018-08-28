
import reveries.maya.lib
from reveries.maya.plugins import ReferenceLoader


class CameraLoader(ReferenceLoader):
    """Specific loader for the reveries.camera family"""

    label = "Reference camera"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.camera"]

    representations = [
        "mayaAscii",
        "Alembic",
        "FBX",
    ]

    def process_reference(self, context, name, namespace, data):
        import maya.cmds as cmds

        entry_path = self.file_path(data["entry_fname"])

        group_name = "{}:{}".format(namespace, name)
        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName=group_name,
                          reference=True,
                          lockReference=True,
                          returnNewNodes=True)

        reveries.maya.lib.lock_transform(group_name)
        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
