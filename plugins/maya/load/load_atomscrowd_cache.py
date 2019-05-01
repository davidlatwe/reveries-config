
import os
import avalon.api
from reveries.maya import lib, capsule
from reveries.maya.plugins import ImportLoader


class AtomsCrowdCacheLoader(ImportLoader, avalon.api.Loader):

    label = "Atoms Cache"
    order = -10
    icon = "building"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.atomscrowd"]

    representations = [
        "atoms",
    ]

    def process_import(self, context, name, namespace, group, options):
        import maya.cmds as cmds

        cmds.loadPlugin("AtomsProxyMaya", quiet=True)
        if not cmds.pluginInfo("AtomsProxyMaya", query=True, loaded=True):
            self.log.warning("Could not load AtomsProxyMaya plugin")
            return

        representation = context["representation"]

        entry_path = self.file_path(representation)
        entry_path = os.path.expandvars(entry_path)

        variation_file = representation["data"]["variationFile"]
        variation_path = os.path.dirname(entry_path) + "/" + variation_file

        with capsule.namespaced(namespace):
            node_name = "tcAtomsProxy"
            node = cmds.createNode("tcAtomsProxy", name=node_name + "Shape")
            cmds.rename(cmds.listRelatives(node, parent=True), node_name)

        cmds.setAttr(node + ".cachePath", entry_path, type="string")
        cmds.setAttr(node + ".variationsPath", variation_path, type="string")
        cmds.connectAttr("time1.outTime", node + ".time", f=True)

        group = cmds.group(node, name=group, world=True)

        nodes = [node, group]

        lib.lock_transform(group)
        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
