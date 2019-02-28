
import avalon.api
from reveries.maya.plugins import ReferenceLoader
from reveries.maya.xgen.interactive import list_lead_descriptions


class XGenInteractiveLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for XGen Interactive"""

    label = "Reference XGen"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.xgen"]

    representations = [
        "XGenInteractive",
    ]

    def process_reference(self, context, name, namespace, group, options):

        import maya.cmds as cmds
        from avalon import maya
        from reveries.maya.lib import get_highest_in_hierarchy

        representation = context["representation"]

        entry_path = self.file_path(representation)

        with maya.maintained_selection():
            nodes = cmds.file(entry_path,
                              namespace=namespace,
                              ignoreVersion=True,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=group)
        self[:] = nodes

        transforms = cmds.ls(nodes, type="transform", long=True)
        root = get_highest_in_hierarchy(transforms)
        descriptions = cmds.listRelatives(list_lead_descriptions(nodes),
                                          parent=True) or []
        self.interface = root + descriptions

    def switch(self, container, representation):
        self.update(container, representation)
