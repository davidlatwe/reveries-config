
import avalon.api
import avalon.maya

from reveries.maya.plugins import ReferenceLoader


class RigLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """
    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def process_reference(self, context, name, namespace, options):

        import maya.cmds as cmds
        from reveries.maya.lib import get_highest_in_hierarchy

        representation = context["representation"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        group_name = "{}:{}".format(namespace, name)

        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName=group_name)

        self[:] = nodes

        transforms = cmds.ls(nodes, type="transform", long=True)
        root = get_highest_in_hierarchy(transforms)
        sets = cmds.ls(nodes, type="objectSet")
        self.interface = root + sets

        return group_name

    def switch(self, container, representation):
        self.update(container, representation)
