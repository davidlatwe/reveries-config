
import avalon.api

import reveries.maya.lib
from reveries.maya.plugins import ReferenceLoader


class ArnoldStandInLoader(ReferenceLoader, avalon.api.Loader):

    label = "Reference Arnold Stand-In"
    order = -10
    icon = "coffee"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.standin",
    ]

    representations = [
        "Ass",
    ]

    def process_reference(self, context, name, namespace, group, options):
        import maya.cmds as cmds
        from reveries.maya.lib import get_highest_in_hierarchy

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

        transforms = cmds.ls(nodes, type="transform", long=True)
        self.interface = get_highest_in_hierarchy(transforms)

    def switch(self, container, representation):
        self.update(container, representation)
