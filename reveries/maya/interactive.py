
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
