import reveries.maya.io
import reveries.maya.lib


class CameraLoader(reveries.maya.io.ReferenceLoader):
    """Specific loader for the reveries.camera family"""

    families = ["reveries.camera"]
    label = "Reference camera"
    representations = ["abc", "fbx", "ma"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        # Get family type from the context

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        group_name = "{}:{}".format(namespace, name)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName=group_name,
                          reference=True,
                          lockReference=True,
                          returnNewNodes=True)

        reveries.maya.lib.lock_transform(group_name)
        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
