
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class SetDressCreator(avalon.maya.Creator):
    """A grouped package of loaded content"""

    label = "Set Dress"
    family = "reveries.setdress"
    icon = "tree"

    def process(self):
        return put_instance_icon(super(SetDressCreator, self).process())
