
from maya import cmds
from .. import lib


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


def apply_smooth_sets(relationships, namespace=None, target_namespaces=None):
    """Given a dictionary of `relationships`, apply smooth value to edges

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to surface nodes.
        namespace (str, optional): namespace that need to apply to smoothSet
        target_namespaces (list, optional): model namespaces

    """
    namespace = namespace or ""

    for id, attrs in relationships.items():
        for target_namespace in target_namespaces:
            nodes = lib.lsAttr(lib.AVALON_ID_ATTR_LONG,
                               value=id,
                               namespace=target_namespace)
            if not nodes:
                continue

            for node in nodes:
                for attr, value in attrs.items():
                    cmds.setAttr(node + "." + attr, value)
