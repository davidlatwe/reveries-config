
import avalon.api
from avalon.vendor import qargparse
from reveries.maya.plugins import ReferenceLoader


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

    options = [
        qargparse.Integer("count", default=1, min=1, help="Batch load count."),
        qargparse.Double3("offset", help="Offset loaded subsets."),
    ]

    def process_reference(self, context, name, namespace, group, options):

        import maya.cmds as cmds
        from avalon import maya

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

    def switch(self, container, representation):
        self.update(container, representation)
