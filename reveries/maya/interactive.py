
from maya import cmds

from .vendor import capture


def active_view_snapshot(*args):
    capture.snap(
        clipboard=True,
        display_options={
            "displayGradient": cmds.displayPref(
                query=True, displayGradient=True),
            "background": cmds.displayRGBColor(
                "background", query=True),
            "backgroundTop": cmds.displayRGBColor(
                "backgroundTop", query=True),
            "backgroundBottom": cmds.displayRGBColor(
                "backgroundBottom", query=True),
        }
    )


def wipe_all_namespaces():
    all_NS = cmds.namespaceInfo(":",
                                listOnlyNamespaces=True,
                                recurse=True,
                                absoluteName=True)
    for NS in reversed(all_NS):
        if NS in (":UI", ":shared"):
            continue

        try:
            cmds.namespace(removeNamespace=NS,
                           force=True,
                           mergeNamespaceWithRoot=True)
        except RuntimeError:
            pass
