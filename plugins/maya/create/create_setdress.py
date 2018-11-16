
import avalon.maya
from maya import cmds


class SetDressCreator(avalon.maya.Creator):
    """A grouped package of loaded content"""

    name = "setdressDefault"
    label = "Set Dress"
    family = "reveries.setdress"
    icon = "tree"

    def build_base(self):
        if cmds.objExists("|ROOT"):
            return

        make_empty = not ((self.options or {}).get("useSelection") and
                          bool(cmds.ls(sl=True)))
        cmds.group(name="ROOT", empty=make_empty, world=True)

    def process(self):

        self.build_base()

        return super(SetDressCreator, self).process()
