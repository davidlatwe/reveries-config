
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class LightSetCreator(avalon.maya.Creator):
    """A set of lights for base lighting"""

    label = "LightSet"
    family = "reveries.lightset"
    icon = "lightbulb-o"

    def process(self):
        return put_instance_icon(super(LightSetCreator, self).process())
