
import reveries.base as base
import reveries.base.maya_plugins as maya_plugins


class MayaShareLoader(maya_plugins.ReferenceLoader):
    """Specific loader for the reveries.mayaShare family"""

    label = "Reference MayaShare"
    order = -10
    icon = "code-fork"
    color = "orange"

    families = ["reveries.mayaShare"]

    representations = base.repr_obj_list([
        ("mayaAscii", "ma"),
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
                          lockReference=False,
                          returnNewNodes=True)

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
