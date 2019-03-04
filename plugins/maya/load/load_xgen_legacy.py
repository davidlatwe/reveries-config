
import os
from distutils.dir_util import copy_tree

import avalon.api
from maya import cmds
from reveries.maya import utils
from reveries.maya.plugins import MayaBaseLoader, unique_root_namespace
from reveries.maya.xgen import legacy as xgen
from reveries.maya.pipeline import subset_containerising


class XGenLegacyLoader(MayaBaseLoader, avalon.api.Loader):
    """Specific loader for XGen Legacy"""

    label = "Import XGen Legacy"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.xgen"]

    representations = [
        "XGenLegacy",
    ]

    def load(self, context, name=None, namespace=None, options=None):

        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        family_name = context["version"]["data"]["families"][0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

        # Copy maps
        local_map_dir = os.path.join(avalon.api.Session["AVALON_WORKDIR"],
                                     "xgen",
                                     "published")
        map_dir = os.path.join(self.package_path, "maps")
        for palette in os.listdir(map_dir):
            palette_dir = os.path.join(map_dir, palette)
            local_palette_dir = os.path.join(local_map_dir, palette)

            # Copy
            copy_tree(palette_dir, local_palette_dir)

        # Import palette (No bind)
        palette_nodes = list()
        palettes = context["representation"]["data"]["palettes"]
        desc_ids = context["representation"]["data"]["descriptionIds"]
        for file in palettes:
            xgen_path = os.path.join(self.package_path, file)
            xgen_path = xgen_path.replace("\\", "/")
            palette_node = xgen.import_palette(xgen_path,
                                               namespace=namespace,
                                               wrapPatches=False)
            palette_nodes.append(palette_node)

            # Set xgDataPath
            palette = os.path.splitext(file)[0]
            data_path = os.path.join(local_map_dir, palette).replace("\\", "/")
            xgen.set_data_path(palette_node, data_path)

            # Apply ID
            for desc in xgen.list_descriptions(palette_node):
                _desc = desc.rsplit(":", 1)[-1]
                id = desc_ids[_desc]
                utils.set_id(desc, id)

        group_name = self.group_name(namespace, name)
        # Cannot be grouped
        # cmds.group(palette_nodes, name=group_name, world=True)
        # palette_nodes = cmds.ls(palette_nodes, long=True)

        # (NOTE) Guides will be import after description
        #        being binded.

        # Containerising..
        self.interface = palette_nodes[:]
        nodes = palette_nodes[:]
        nodes += cmds.listRelatives(palette_nodes,
                                    allDescendents=True,
                                    fullPath=True)

        container_id = options.get("containerId",
                                   utils.generate_container_id())
        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          ports=self.interface,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def update(self, container, representation):
        pass

    def remove(self, container):
        namespace = container["namespace"]
        container_name = container["objectName"]
        container_content = cmds.sets(container_name, query=True)
        nodes = cmds.ls(container_content, long=True)

        nodes.append(container_name)

        self.log.info("Removing '%s' from Maya.." % container["name"])

        palettes = cmds.ls(nodes, type="xgmPalette")
        for palette in palettes:
            xgen.delete_palette(palette)

        try:
            cmds.delete(nodes)
        except ValueError:
            pass

        cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)

        return True
