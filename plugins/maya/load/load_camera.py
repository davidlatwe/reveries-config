
import avalon.api
import reveries.maya.lib
from reveries.maya.plugins import ReferenceLoader


class CameraLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for the reveries.camera family"""

    label = "Reference camera"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.camera"]

    representations = [
        "mayaAscii",
        "Alembic",
        "FBX",
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

        reveries.maya.lib.lock_transform(group)
        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
