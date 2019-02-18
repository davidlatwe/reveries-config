
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
            if enabled:
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
        aov_names += ["beauty"]

    return aov_names
