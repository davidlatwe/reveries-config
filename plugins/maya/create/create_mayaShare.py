
import avalon.maya

from reveries.maya.pipeline import put_instance_icon


class MayaShareCreator(avalon.maya.Creator):
    """低驗證的普通檔案輸出, 僅限救急用"""

    label = "Maya Share (.ma)"
    family = "reveries.mayashare"
    icon = "share-square-o"

    def process(self):
        return put_instance_icon(super(MayaShareCreator, self).process())
