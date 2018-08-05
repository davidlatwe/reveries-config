
import avalon.maya
from maya import cmds


class CreatePointCache(avalon.maya.Creator):
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
        self.data["use_contractor"] = True

        container = super(CreatePointCache, self).process()
        cmds.setAttr(container + ".publish_contractor", lock=True)
