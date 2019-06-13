
import avalon.api
from avalon.pipeline import AVALON_CONTAINER_ID
from reveries.maya.plugins import ReferenceLoader
from reveries.maya.vendor import sticker


class MayaShareLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for the reveries.mayaShare family"""

    label = "Reference MayaShare"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.mayashare"]

    representations = [
        "mayaAscii",
    ]

    def process_reference(self, context, name, namespace, group, options):
        import maya.cmds as cmds

        representation = context["representation"]

        entry_path = self.file_path(representation)

        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          ignoreVersion=True,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName=group,
                          reference=True,
                          lockReference=False,
                          returnNewNodes=True)

        # Process container nodes from the sharing scene
        for node in cmds.ls(nodes, type="objectSet"):
            if (cmds.objExists(node + ".id") and
                    cmds.getAttr(node + ".id") == AVALON_CONTAINER_ID):
                # Update namespace
                new_ns = namespace + cmds.getAttr(node + ".namespace")
                cmds.setAttr(node + ".namespace", new_ns, type="string")

        sticker.reveal()

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
