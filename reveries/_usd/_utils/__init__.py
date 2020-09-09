def load_maya_plugin():
    """
    Load usd plugin in current session
    """
    import maya.cmds as cmds

    PLUGIN_NAMES = ["pxrUsd", "pxrUsdPreviewSurface"]
    for plugin_name in PLUGIN_NAMES:
        cmds.loadPlugin(plugin_name, quiet=True)