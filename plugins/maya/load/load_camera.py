
import reveries.maya.lib
from reveries.plugins import repr_obj
from reveries.maya.plugins import ReferenceLoader


class CameraLoader(ReferenceLoader):
    """Specific loader for the reveries.camera family"""

    label = "Reference camera"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.camera"]

    representations = [
        repr_obj("mayaAscii", "ma"),
        repr_obj("Alembic", "abc"),
        repr_obj("FBX", "fbx"),
    ]

    def process_reference(self, context, name, namespace, data):
        import maya.cmds as cmds

        group_name = "{}:{}".format(namespace, name)
        nodes = cmds.file(self.entry_path,
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
