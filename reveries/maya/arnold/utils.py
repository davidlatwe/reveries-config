
from collections import defaultdict
from maya import cmds
from .. import lib

from avalon.vendor import six


def create_options():
    import mtoa
    mtoa.core.createOptions()


def get_arnold_aov_nodes(layer=None):
    """
    """
    create_options()
    aov_mode = cmds.getAttr("defaultArnoldRenderOptions.aovMode")
    merge_aov = cmds.getAttr("defaultArnoldDriver.mergeAOVs")

    layer = layer or cmds.editRenderLayerGlobals(query=True,
                                                 currentRenderLayer=True)

    aov_nodes = []

    if aov_mode and not merge_aov:
        for aov in cmds.ls(type="aiAOV"):
            enabled = lib.query_by_renderlayer(aov, "enabled", layer)
            if enabled and cmds.listConnections(aov, type="aiOptions"):
                # AOV must connected with `defaultArnoldRenderOptions` node
                aov_nodes.append(aov)

    return aov_nodes


def get_arnold_aov_names(layer=None):
    """
    """
    create_options()
    merge_aov = cmds.getAttr("defaultArnoldDriver.mergeAOVs")

    aov_names = [cmds.getAttr(aov + ".name")
                 for aov in get_arnold_aov_nodes(layer)]

    if not merge_aov:
        # (NOTE) 'RGBA' is 'beauty'.
        #        'beauty' will always present even no AOV named 'RGBA'.
        if "RGBA" in aov_names:
            aov_names.remove("RGBA")
        aov_names += ["beauty"]

    return aov_names


def update_full_scene():
    cmds.arnoldRenderView(option=["Update Full Scene", "1"])


def apply_ai_attrs(relationships, namespace=None, target_namespaces=None):
    """Given a dictionary of `relationships`, apply ai attributes to nodes

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to surface nodes.
        namespace (str, optional): namespace that need to apply to
        target_namespaces (list, optional): model namespaces

    """
    namespace = namespace or ""

    ids = set()
    for id, attrs in relationships.items():
        if attrs:
            ids.add(id)

    surfaces = defaultdict(set)
    for target_namespace in target_namespaces:
        _map = lib.ls_nodes_by_id(ids, target_namespace)
        for id, nodes in _map.items():
            surfaces[id].update(nodes)

    for id, attrs in relationships.items():
        if id not in surfaces:
            continue

        for node in surfaces[id]:
            for attr, value in attrs.items():
                shape = cmds.listRelatives(node,
                                           shapes=True,
                                           noIntermediate=True,
                                           fullPath=True)[0]
                attr_path = shape + "." + attr
                try:
                    origin = cmds.getAttr(attr_path)
                except (RuntimeError, ValueError):
                    continue

                if origin == value:
                    continue

                if isinstance(value, six.string_types):
                    cmds.setAttr(attr_path, value, type="string")
                elif isinstance(value, list):
                    # Ignore for now
                    pass
                else:
                    cmds.setAttr(attr_path, value)


def create_standin(path):
    import mtoa
    return mtoa.core.createStandIn(path)
