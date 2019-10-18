
import avalon.maya
from maya import cmds

from reveries.maya.pipeline import put_instance_icon


class ModelCreator(avalon.maya.Creator):
    """發佈模型, 請選取模型物件或群組"""

    label = "Model"
    family = "reveries.model"
    icon = "cubes"

    defaults = [
        "default",
        "polyHigh",
        "polyLow",
    ]

    def build_base(self):
        if cmds.objExists("|ROOT"):
            return

        make_empty = not ((self.options or {}).get("useSelection") and
                          bool(cmds.ls(sl=True)))
        cmds.group(name="ROOT", empty=make_empty, world=True)

    def process(self):

        self.build_base()

        return put_instance_icon(super(ModelCreator, self).process())
