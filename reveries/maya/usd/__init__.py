def load_maya_plugin():
    """
    Load usd plugin in current session
    """
    import maya.cmds as cmds

    PLUGIN_NAMES = ["pxrUsd", "pxrUsdPreviewSurface"]
    for plugin_name in PLUGIN_NAMES:
        cmds.loadPlugin(plugin_name, quiet=True)


def get_export_hierarchy(geom):
    """
    Get export node long path and usd root path.
    :param geom: (str) Geometry name
    :return: Export node name and usd root path.
        export_node = "|..|..|HanMaleA_rig_02:HanMaleA_model_01_:Geometry"
        root_usd_path = "/rigDefault/ROOT/Group/Geometry/modelDefault/ROOT"
    """
    import maya.cmds as cmds

    cmds.listRelatives(geom, allDescendents=True)
    geom_long = cmds.ls(geom, long=True)
    if not geom_long:
        return '', ''
    parents = geom_long[0].split("|")[1:-1]
    parents_long_named = ["|".join(parents[:i])
                          for i in range(1, 1 + len(parents))]
    export_node = [_p for _p in parents_long_named
                   if _p.endswith(':Geometry')]  # MOD

    # Get mod root path
    root_usd_path = ''
    parents_without_ns = [parents[i].split(':')[-1]
                          for i in range(0, len(parents))]
    for item in ["|".join(parents_without_ns[:i])
                 for i in range(1, 1 + len(parents_without_ns))]:
        if "|" in item:
            if item.endswith('ROOT') and len(item.split('|')) != 2:
                root_usd_path = '|{}'.format(item).\
                    replace('|MOD', '').replace('|', '/')

    return export_node[0] if export_node else '', root_usd_path
