
import avalon.maya
from maya import cmds

from reveries.maya.pipeline import put_instance_icon


class PointCacheCreator(avalon.maya.Creator):
    """Any cacheable object"""

    name = "PointCacheDefault"
    label = "PointCache"
    family = "reveries.pointcache"
    icon = "diamond"

    contractor = "deadline.maya.script"

    def process(self):
        self.data["format"] = [
            "Alembic",
            "GPUCache",
            "FBXCache",
        ]

        self.data["static_cache"] = False

        self.data["publish_contractor"] = self.contractor
        self.data["use_contractor"] = False

        instance = super(PointCacheCreator, self).process()
        cmds.setAttr(instance + ".publish_contractor", lock=True)

        return put_instance_icon(instance)
