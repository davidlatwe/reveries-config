import os

import avalon.api
from avalon.vendor import qargparse
from reveries.maya.plugins import USDLoader


class USDSetdressLoader(USDLoader, avalon.api.Loader):
    """Load the USD stage"""

    label = "Load USD Stage"
    order = -10.5
    icon = "cloud-download"
    color = "#b85c7c"

    hosts = ["maya"]

    families = [
        "reveries.setdress.usd"
    ]

    representations = ["USD"]

    options = [
        qargparse.Integer("count", default=1, min=1, help="Batch load count."),
        qargparse.Double3("offset", help="Offset loaded subsets."),
    ]

    def process_reference(self, context, name, namespace, group, options):
        import maya.cmds as cmds
        from avalon import maya

        representation = context["representation"]
        entry_path = self.file_path(representation).replace("\\", "/")
        entry_path = entry_path.replace(
            "$AVALON_PROJECTS",
            os.environ["AVALON_PROJECTS"])
        entry_path = entry_path.replace(
            "$AVALON_PROJECT",
            os.environ["AVALON_PROJECT"])

        with maya.maintained_selection():
            node = cmds.createNode("pxrUsdProxyShape",
                                   name="{}Shape".format(namespace))

            translate_grp = cmds.listRelatives(node, parent=True)[0]
            cmds.rename(translate_grp, namespace)

            cmds.setAttr("{}.filePath".format(node), entry_path, type="string")

            cmds.setAttr("{}.overrideEnabled".format(namespace), 1)
            cmds.setAttr("{}.overrideDisplayType".format(namespace), 2)

            cmds.select(cl=True)
            cmds.group(translate_grp, name=group)

        print("node:", node)
        self[:] = [node]
