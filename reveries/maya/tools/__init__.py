
import importlib
from maya import cmds


def show(tool_name):
    path = "reveries.maya.tools."
    try:
        tool = importlib.import_module(path + tool_name)
    except Exception as e:
        cmds.warning("Cannot open {tool!r} because: {error}"
                     "".format(tool=tool_name, error=e))
    else:
        reload(tool)
        tool.show()


__all__ = (
    "show",
)
