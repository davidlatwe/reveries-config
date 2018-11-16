
import avalon.maya
from maya import cmds


class ModelCreator(avalon.maya.Creator):
    """Polygonal geometry"""

    name = "modelDefault"
    label = "Model"
    family = "reveries.model"
    icon = "cubes"

    def build_base(self):
        if cmds.objExists("|ROOT"):
            return

        make_empty = not ((self.options or {}).get("useSelection") and
                          bool(cmds.ls(sl=True)))
        cmds.group(name="ROOT", empty=make_empty, world=True)

    def process(self):

        self.build_base()

        return super(ModelCreator, self).process()
