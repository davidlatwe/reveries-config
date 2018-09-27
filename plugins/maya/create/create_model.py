
import avalon.maya
from maya import cmds


class ModelCreator(avalon.maya.Creator):
    """Polygonal geometry"""

    name = "modelDefault"
    label = "Model"
    family = "reveries.model"
    icon = "cubes"

    def process(self):
        if not cmds.objExists("|MODEL"):
            make_empty = not ((self.options or {}).get("useSelection") and
                              bool(cmds.ls(sl=True)))
            cmds.group(name="MODEL", empty=make_empty, world=True)

        return super(ModelCreator, self).process()
