
import avalon.maya
from reveries.maya.pipeline import put_instance_icon


class AnimationCreator(avalon.maya.Creator):
    """發佈動畫曲線 (Animation Curves)"""

    label = "Animation"
    family = "reveries.animation"
    icon = "male"

    def process(self):
        return put_instance_icon(super(AnimationCreator, self).process())
