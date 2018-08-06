
import reveries.maya.lib
import reveries.base as base
import reveries.base.maya_plugins as maya_plugins


class CameraLoader(maya_plugins.ReferenceLoader):
    """Specific loader for the reveries.camera family"""

    label = "Reference camera"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.camera"]

    representations = base.repr_obj_list([
        ("mayaAscii", "ma"),
        ("Alembic", "abc"),
        ("FBX", "fbx"),
    ])

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
