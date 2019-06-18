
import os
import getpass
import contextlib
from distutils.dir_util import copy_tree

import avalon.api
from maya import cmds
from reveries.maya import utils
from reveries.maya.plugins import MayaBaseLoader, unique_root_namespace
from reveries.maya.xgen import legacy as xgen
from reveries.maya.pipeline import (
    subset_containerising,
    apply_namespace_wrapper,
)


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

        # (NOTE) AnimWire modifier has a bug that not able to find wires if
        #        namespace is applied.
        #        The hairSystem is okay to work with, but not able to update
        #        XGen preview. So you either simulate without the update, or
        #        build the simulation without namespace and save with .xgen
        #        file exported, then reference it with namespace.
        #
        #        https://forums.autodesk.com/t5/maya-dynamics/anim-wire-
        #        errors-when-using-namespaces/m-p/7329883#M5642
        #

        if not cmds.pluginInfo("xgenToolkit", query=True, loaded=True):
            cmds.loadPlugin("xgenToolkit", quiet=True)

        representation = context["representation"]

        asset = context["asset"]
        asset_name = asset["data"].get("shortName", asset["name"])
        family_name = context["version"]["data"]["families"][0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

        descriptions_data = representation["data"]["descriptionsData"]
        baked = representation["data"]["step"] != xgen.SHAPING
        bound_meshes = list()

        # Varify selection
        selected = cmds.ls(sl=True, long=True)

        all_bound_geos = set()
        for data in descriptions_data.values():
            for geo in data["bound"]:
                all_bound_geos.add("|" + geo)

        msg = ("Require bound geos: {0}\n"
               "Selected: {1}".format(all_bound_geos, selected))
        assert set(selected) == all_bound_geos, msg

        # Rename bound geos to namespace
        for node in selected:
            bound_meshes.append(node)

        # Copy maps
        local_map_dir = os.path.join(avalon.api.Session["AVALON_WORKDIR"],
                                     "xgen",
                                     "published",
                                     # Add username to ease out file lock issue
                                     getpass.getuser())
        map_dir = os.path.join(self.package_path, "maps")
        for palette in os.listdir(map_dir):
            palette_dir = os.path.join(map_dir, palette)
            local_palette_dir = os.path.join(local_map_dir, palette)

            # Copy
            copy_tree(palette_dir, local_palette_dir)

        # Import palette
        palette_nodes = list()
        xgen.preview_clear()

        for file in representation["data"]["palettes"]:

            xgen_path = os.path.join(self.package_path, file)
            xgen_path = xgen_path.replace("\\", "/")
            palette_node = xgen.import_palette(xgen_path,
                                               wrapPatches=True)
            palette_nodes.append(palette_node)

            # Set xgDataPath
            palette = os.path.splitext(file)[0]
            data_path = os.path.join(local_map_dir, palette).replace("\\", "/")
            xgen.set_data_path(palette_node, data_path)

            if not baked:
                # Bind grooming descriptions to geometry
                for desc in xgen.list_descriptions(palette_node):
                    groom = xgen.get_groom(desc)
                    if groom:
                        groom_dir = os.path.join(self.package_path,
                                                 "groom",
                                                 palette_node,
                                                 desc)
                        xgen.import_grooming(desc, groom, groom_dir)

            # Apply ID
            asset_id = str(asset["_id"])
            with utils.id_namespace(asset_id):
                for desc in xgen.list_descriptions(palette_node):
                    _desc = desc.rsplit(":", 1)[-1]
                    id = descriptions_data[_desc]["id"]
                    utils.upsert_id(desc, id)

            # Ensure tube shade disabled
            xgen.disable_tube_shade(palette_node)

        group_name = self.group_name(namespace, name)
        # Cannot be grouped
        # cmds.group(palette_nodes, name=group_name, world=True)
        # palette_nodes = cmds.ls(palette_nodes, long=True)

        # Containerising..
        nodes = palette_nodes[:]
        nodes += bound_meshes
        nodes += cmds.listRelatives(palette_nodes,
                                    allDescendents=True,
                                    fullPath=True)
        nodes += apply_namespace_wrapper(namespace, nodes)

        container_id = options.get("containerId",
                                   utils.generate_container_id())
        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def update(self, container, representation):
        # (TODO) Update XPD file if current step is baked
        pass

    def remove(self, container):
        namespace = container["namespace"]
        container_name = container["objectName"]
        container_content = cmds.sets(container_name, query=True)
        nodes = cmds.ls(container_content, long=True)

        nodes.append(container_name)

        self.log.info("Removing '%s' from Maya.." % container["name"])

        palettes = cmds.ls(nodes, type="xgmPalette")
        with ensure_desc_editor():
            for palette in palettes:
                xgen.delete_palette(palette)

        for node in nodes:
            try:
                cmds.delete(node)
            except ValueError:
                pass

        cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)

        return True


class MockDescriptionEditor(object):

    class Previewer(object):
        tracking = True
        idle = True

    previewer = Previewer()
    refresh = (lambda self, *args: None)
    clearPreview = (lambda self, *args: None)


@contextlib.contextmanager
def ensure_desc_editor():
    # Avoid "AttributeError: 'NoneType' object has no attribute 'previewer'"
    # when there's no DescriptionEditor GUI exists.
    import xgenm.xgGlobal as xgg

    mocked = False
    if xgg.DescriptionEditor is None:
        mocked = True
        xgg.DescriptionEditor = MockDescriptionEditor()
    try:
        yield

    finally:
        if mocked:
            xgg.DescriptionEditor = None
