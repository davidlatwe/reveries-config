
import avalon.api
from reveries.maya.plugins import ReferenceLoader
from avalon.vendor import qargparse


class PointCacheReferenceLoader(ReferenceLoader, avalon.api.Loader):

    label = "Reference PointCache"
    order = -10
    icon = "flash"
    color = "orange"

    hosts = ["maya"]

    families = [
        "reveries.pointcache",
        "reveries.setdress",
    ]

    representations = [
        "Alembic",
        "FBXCache",
        "GPUCache",
    ]

    options = [
        qargparse.Integer("count", default=1, min=1, help="Batch load count."),
        qargparse.Double3("offset", help="Offset loaded subsets."),
    ]

    def process_reference(self, context, name, namespace, group, options):
        import maya.cmds as cmds
        import reveries.maya.lib
        from reveries.maya import utils

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

        if representation["name"] == "Alembic":
            self.unit_conversion_patch(nodes)

        # (NOTE) Nodes loaded from Alembic did not have verifiers
        utils.update_id_verifiers(nodes)

        reveries.maya.lib.lock_transform(group)
        self[:] = nodes

    def update(self, container, representation):
        import maya.cmds as cmds

        uuid = cmds.ls(container["objectName"], uuid=True)

        super(PointCacheReferenceLoader,
              self).update(container, representation)

        if representation["name"] == "Alembic":
            nodes = cmds.sets(cmds.ls(uuid), query=True, nodesOnly=True)
            self.unit_conversion_patch(nodes)

    def switch(self, container, representation):
        self.update(container, representation)

    def unit_conversion_patch(self, nodes):
        """
        When referencing same Alembic file multiple times, the rotation
        misbehave except the first one, after scene saved and re-open.

        The observable cause was the unitConversion nodes which being
        connected in between alembic node's output and transform node's
        rotation, their `conversionFactor` did not properly configured
        after re-open. The value should be like `0.017453292519943295`
        but remain `1.0`.

        It's a known bug for about 4 years from now:
        https://gitter.im/getavalon/Lobby?at=5d36b894d61887416420bcda

        Current workaround that I can think of is to trigger reference
        edit on all newly created unitConversion nodes, let reference
        edit *pin* the factor value for us.

        """
        import maya.cmds as cmds

        for conversion in cmds.ls(nodes, type="unitConversion"):
            attr = conversion + ".conversionFactor"
            factor = cmds.getAttr(attr)
            cmds.setAttr(attr, 1)  # To trigger reference edit
            cmds.setAttr(attr, factor)
