
import avalon.maya

from reveries.maya.pipeline import put_instance_icon
from reveries.plugins import message_box_error
from maya import cmds


error__invalid_name = """
{!r} is not a valid XGen subset name, a XGen subset name
should starts with one of these variation name:
{}
"""


class XGenCreator(avalon.maya.Creator):
    """Maya XGen Legacy or Interactive Grooming"""

    label = "XGen"
    family = "reveries.xgen"
    icon = "paw"

    defaults = [
        "legacy",
        "interactive",
    ]

    def process(self):
        variant = None

        for var in self.defaults:
            prefix = "xgen" + var
            if self.data["subset"].lower().startswith(prefix):
                variant = var
                break

        if variant is None:
            msg = error__invalid_name.format(self.data["subset"],
                                             ", ".join(self.defaults))
            message_box_error("Invalid Subset Name", msg)
            raise RuntimeError(msg)

        self.data["XGenType"] = variant

        instance = super(XGenCreator, self).process()

        cmds.setAttr(instance + ".XGenType", lock=True)

        return put_instance_icon(instance)
