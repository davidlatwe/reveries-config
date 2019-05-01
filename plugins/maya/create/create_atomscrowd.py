
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class AtomsCrowdCreator(avalon.maya.Creator):
    """Atoms Crowd"""

    label = "Atoms Crowd"
    family = "reveries.atomscrowd"
    icon = "building"

    def process(self):
        return put_instance_icon(super(AtomsCrowdCreator, self).process())
