
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class LookCreator(avalon.maya.Creator):
    """Shader connections defining shape look"""

    name = "lookDefault"
    label = "Look"
    family = "reveries.look"
    icon = "paint-brush"

    def process(self):
        return put_instance_icon(super(LookCreator, self).process())
