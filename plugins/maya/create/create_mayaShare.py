
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class MayaShareCreator(avalon.maya.Creator):
    """Share work as MayaAscii with minimum validation"""

    name = "mayashareDefault"
    label = "Maya Share (.ma)"
    family = "reveries.mayashare"
    icon = "share-square-o"

    def process(self):
        return put_instance_icon(super(MayaShareCreator, self).process())
