
import os
import avalon.api
import avalon.io
from reveries.utils import get_representation_path_
from reveries.maya import lib, capsule, pipeline
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

        nodes = list()

        with capsule.namespaced(namespace):
            node = "tcAtomsProxy"
            shape = cmds.createNode("tcAtomsProxy", name=node + "Shape")
            parent = cmds.listRelatives(shape, parent=True)
            node = cmds.rename(parent, node)

            nodes = [shape, node]

        cmds.setAttr(shape + ".cachePath", entry_path, type="string")
        cmds.setAttr(shape + ".variationsPath", variation_path, type="string")
        cmds.connectAttr("time1.outTime", shape + ".time", f=True)

        group = cmds.group(node, name=group, world=True)
        nodes.append(group)

        lib.lock_transform(group)
        self[:] = nodes

    def update(self, container, representation):
        import maya.cmds as cmds

        members = cmds.sets(container["objectName"], query=True)
        proxy_node = cmds.ls(members, type="tcAtomsProxy")

        if not proxy_node:
            raise Exception("No Atoms Proxy node, this is a bug.")

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation)
        entry_path = os.path.expandvars(entry_path)

        variation_file = representation["data"]["variationFile"]
        variation_path = os.path.dirname(entry_path) + "/" + variation_file

        shape = proxy_node[0]
        self.log.info(entry_path)
        cmds.setAttr(shape + ".cachePath", entry_path, type="string")
        cmds.setAttr(shape + ".variationsPath", variation_path, type="string")

        # Update container
        version, subset, asset, _ = parents
        pipeline.update_container(container,
                                  asset,
                                  subset,
                                  version,
                                  representation)

    def switch(self, container, representation):
        self.update(container, representation)
