
import avalon.maya
from maya import cmds

from reveries.maya.pipeline import put_instance_icon


class PointCacheCreator(avalon.maya.Creator):
    """Any cacheable object"""

    name = "pointcacheDefault"
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

        self.data["staticCache"] = False

        self.data["publishContractor"] = self.contractor
        self.data["useContractor"] = False

        instance = super(PointCacheCreator, self).process()
        cmds.setAttr(instance + ".publishContractor", lock=True)

        return put_instance_icon(instance)
