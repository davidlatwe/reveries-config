
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
            if enabled and cmds.listConnections(aov, type="renderLayer"):
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


def get_smooth_sets():
    subdiv_iter = set(cmds.ls("*.aiSubdivIterations",
                              objectsOnly=True,
                              type="objectSet"))

    subdiv_type = set(cmds.ls("*.aiSubdivType",
                              objectsOnly=True,
                              type="objectSet"))

    return list(subdiv_iter.intersection(subdiv_type))


def apply_smooth_sets(relationships, namespace=None, target_namespaces=None):
    """Given a dictionary of `relationships`, apply smooth value to edges

    Arguments:
        relationships (avalon-core:shaders-1.0): A dictionary of
            shaders and how they relate to surface nodes.
        namespace (str, optional): namespace that need to apply to smoothSet
        target_namespaces (list, optional): model namespaces

    Returns:
        list: A list of created or used smooth sets

    """
    namespace = namespace or ""
    al_smooth_sets = list()

    for (level, subtp), members in relationships.items():
        level = int(level)
        subtp = int(subtp)

        node = lib.lsAttrs({"aiSubdivIterations": level,
                            "aiSubdivType": subtp},
                           namespace=namespace)
        if not node:
            smooth_name = namespace + ":alSmoothSet1"
            smooth_set = cmds.createNode("objectSet", name=smooth_name)
            cmds.setAttr(smooth_set + ".aiSubdivIterations", level)
            cmds.setAttr(smooth_set + ".aiSubdivType", subtp)
        else:
            smooth_set = node[0]

        al_smooth_sets.append(smooth_set)

        for id in members:
            for target_namespace in target_namespaces:
                nodes = lib.lsAttr(lib.AVALON_ID_ATTR_LONG,
                                   value=id,
                                   namespace=target_namespace)
                if not nodes:
                    continue

                cmds.sets(nodes, forceElement=smooth_set)

    return al_smooth_sets
